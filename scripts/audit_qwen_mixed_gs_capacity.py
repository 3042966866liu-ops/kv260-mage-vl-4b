#!/usr/bin/env python3
"""Read-only capacity and interface audit for a Qwen2 Mixed-GS deployment."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from safetensors import safe_open


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288
ACTIVATION_RECORD_BYTES = 80
PREFILL_MAX_OUTPUT_BLOCKS = 560
HARDWARE_MAX_INPUT_GROUPS = 512
HARDWARE_MAX_DMA_BYTES = (1 << 26) - 1
KV260_DDR_BYTES = 4 * (1 << 30)


def tensor_map(model_dir: Path) -> dict[str, str]:
    index = json.loads((model_dir / "model.safetensors.index.json").read_text())
    return {str(name): str(shard) for name, shard in index["weight_map"].items()}


def tensor_shape(
    model_dir: Path, mapping: dict[str, str], name: str
) -> tuple[int, ...]:
    with safe_open(model_dir / mapping[name], framework="pt", device="cpu") as src:
        return tuple(int(value) for value in src.get_slice(name).get_shape())


def linear_names(layers: int) -> list[str]:
    suffixes = (
        "self_attn.q_proj.weight",
        "self_attn.k_proj.weight",
        "self_attn.v_proj.weight",
        "self_attn.o_proj.weight",
        "mlp.gate_proj.weight",
        "mlp.up_proj.weight",
        "mlp.down_proj.weight",
    )
    return [
        f"model.layers.{layer}.{suffix}"
        for layer in range(layers)
        for suffix in suffixes
    ]


def auxiliary_names(layers: int) -> list[str]:
    names = ["model.embed_tokens.weight"]
    for layer in range(layers):
        prefix = f"model.layers.{layer}"
        names.extend(
            (
                f"{prefix}.input_layernorm.weight",
                f"{prefix}.post_attention_layernorm.weight",
                f"{prefix}.self_attn.q_proj.bias",
                f"{prefix}.self_attn.k_proj.bias",
                f"{prefix}.self_attn.v_proj.bias",
            )
        )
    names.append("model.norm.weight")
    return names


def product(shape: tuple[int, ...]) -> int:
    result = 1
    for value in shape:
        result *= value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prompt-tokens", type=int, default=40)
    args = parser.parse_args()

    model_dir = args.model_dir
    config = json.loads((model_dir / "config.json").read_text())
    layers = int(config["num_hidden_layers"])
    mapping = tensor_map(model_dir)

    linears = []
    total_linear_bytes = 0
    max_groups = 0
    max_blocks = 0
    max_cma_bytes = 0
    dma_failures = []
    for name in linear_names(layers):
        rows, columns = tensor_shape(model_dir, mapping, name)
        if rows % OUTPUTS_PER_BLOCK or columns % GROUP_SIZE:
            raise ValueError(f"unsupported Linear shape {name}: {(rows, columns)}")
        groups = columns // GROUP_SIZE
        blocks = rows // OUTPUTS_PER_BLOCK
        packed_bytes = groups * blocks * PACKET_BYTES
        tile_blocks = min(PREFILL_MAX_OUTPUT_BLOCKS, blocks)
        tile_bytes = groups * (
            args.prompt_tokens * ACTIVATION_RECORD_BYTES
            + tile_blocks * PACKET_BYTES
        )
        if tile_bytes > HARDWARE_MAX_DMA_BYTES:
            dma_failures.append({"name": name, "bytes": tile_bytes})
        max_groups = max(max_groups, groups)
        max_blocks = max(max_blocks, blocks)
        max_cma_bytes = max(max_cma_bytes, tile_bytes)
        total_linear_bytes += packed_bytes
        linears.append(
            {
                "name": name,
                "shape": [rows, columns],
                "input_groups": groups,
                "output_blocks": blocks,
                "packed_bytes": packed_bytes,
            }
        )

    aux_bytes = 0
    aux_entries = []
    for name in auxiliary_names(layers):
        shape = tensor_shape(model_dir, mapping, name)
        byte_count = product(shape) * 2
        aux_bytes += byte_count
        aux_entries.append({"name": name, "shape": list(shape), "bytes": byte_count})

    lm_source_name = "lm_head.weight"
    if lm_source_name not in mapping:
        if not bool(config.get("tie_word_embeddings", False)):
            raise KeyError("lm_head.weight is absent but tie_word_embeddings is false")
        lm_source_name = "model.embed_tokens.weight"
    lm_shape = tensor_shape(model_dir, mapping, lm_source_name)
    vocab, hidden = lm_shape
    if hidden % GROUP_SIZE or vocab % OUTPUTS_PER_BLOCK:
        raise ValueError(f"unsupported LM Head shape: {lm_shape}")
    lm_groups = hidden // GROUP_SIZE
    lm_blocks = vocab // OUTPUTS_PER_BLOCK
    lm_head_bytes = lm_groups * lm_blocks * PACKET_BYTES
    lm_tile_bytes = lm_groups * (
        ACTIVATION_RECORD_BYTES
        + min(PREFILL_MAX_OUTPUT_BLOCKS, lm_blocks) * PACKET_BYTES
    )
    max_cma_bytes = max(max_cma_bytes, lm_tile_bytes)

    packed_total = total_linear_bytes + aux_bytes + lm_head_bytes
    # Tied models can reuse the FP16 embedding already present in the auxiliary
    # blob for exact shortlist rescoring. Untied models need a separate FP16
    # LM-head matrix in addition to the W4 approximation.
    lm_head_fp16_rescore_bytes = (
        0 if bool(config["tie_word_embeddings"]) else product(lm_shape) * 2
    )
    runtime_artifact_total = packed_total + lm_head_fp16_rescore_bytes
    result = {
        "model_dir": str(model_dir),
        "geometry": {
            "hidden_size": int(config["hidden_size"]),
            "intermediate_size": int(config["intermediate_size"]),
            "layers": layers,
            "attention_heads": int(config["num_attention_heads"]),
            "kv_heads": int(config["num_key_value_heads"]),
            "vocab_size": int(config["vocab_size"]),
            "tie_word_embeddings": bool(config["tie_word_embeddings"]),
        },
        "transformer": {
            "linear_count": len(linears),
            "packed_bytes": total_linear_bytes,
            "max_input_groups": max_groups,
            "max_output_blocks": max_blocks,
        },
        "auxiliary_fp16": {
            "tensor_count": len(aux_entries),
            "bytes": aux_bytes,
            "embedding_bytes": next(
                item["bytes"]
                for item in aux_entries
                if item["name"] == "model.embed_tokens.weight"
            ),
        },
        "lm_head_w4g64": {
            "source_tensor": lm_source_name,
            "shape": list(lm_shape),
            "input_groups": lm_groups,
            "output_blocks": lm_blocks,
            "bytes": lm_head_bytes,
        },
        "lm_head_fp16_rescore": {
            "required_separate_file": not bool(config["tie_word_embeddings"]),
            "bytes": lm_head_fp16_rescore_bytes,
        },
        "deployment": {
            "packed_total_bytes": packed_total,
            "packed_total_gib": packed_total / (1 << 30),
            "kv260_ddr_bytes": KV260_DDR_BYTES,
            "packed_total_over_ddr_bytes": packed_total - KV260_DDR_BYTES,
            "packed_total_fits_ddr_without_runtime": packed_total <= KV260_DDR_BYTES,
            "runtime_artifact_total_bytes": runtime_artifact_total,
            "runtime_artifact_total_gib": runtime_artifact_total / (1 << 30),
            "runtime_artifact_over_ddr_bytes": runtime_artifact_total
            - KV260_DDR_BYTES,
            "hardware_input_group_limit": HARDWARE_MAX_INPUT_GROUPS,
            "input_groups_fit": max_groups <= HARDWARE_MAX_INPUT_GROUPS,
            "prompt_tokens": args.prompt_tokens,
            "max_single_cma_tile_bytes": max_cma_bytes,
            "double_cma_bytes": 2 * max_cma_bytes,
            "dma_limit_bytes": HARDWARE_MAX_DMA_BYTES,
            "dma_failures": dma_failures,
        },
    }
    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
