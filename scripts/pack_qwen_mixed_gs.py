#!/usr/bin/env python3
"""Stream a Hugging Face Qwen2 checkpoint into TeLLMe Mixed-GS files.

Transformer Linear weights are stored as asymmetric W4-GS64 packets in
group-major, eight-output-block-major order.  The embedding, normalization
weights, and Q/K/V biases are stored as contiguous little-endian FP16 tensors.
The converter reads one input group or auxiliary row chunk at a time so that a
larger checkpoint never has to be materialized as FP32 in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288
AUX_ROW_CHUNK = 4096


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_map(model_dir: Path) -> dict[str, str]:
    index_path = model_dir / "model.safetensors.index.json"
    if index_path.exists():
        return {
            str(name): str(shard)
            for name, shard in json.loads(index_path.read_text())["weight_map"].items()
        }
    shards = sorted(model_dir.glob("*.safetensors"))
    if len(shards) != 1:
        raise RuntimeError("expected one safetensors file or a shard index")
    with safe_open(shards[0], framework="pt", device="cpu") as source:
        return {str(name): shards[0].name for name in source.keys()}


def tensor_shape(model_dir: Path, mapping: dict[str, str], name: str) -> tuple[int, ...]:
    if name not in mapping:
        raise KeyError(f"checkpoint tensor not found: {name}")
    with safe_open(model_dir / mapping[name], framework="pt", device="cpu") as source:
        return tuple(int(value) for value in source.get_slice(name).get_shape())


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


def quantize_group(weights: np.ndarray) -> bytes:
    minimum = weights.min(axis=1)
    maximum = weights.max(axis=1)
    scale = (maximum - minimum) / np.float32(15.0)
    scale = np.where(scale > 0.0, scale, np.float32(1.0))
    # Transformer packets use an integer affine zero point.  This differs from
    # the later LM-head packer, whose shortlist approximation retained a
    # fractional zero point.
    zero = np.clip(np.rint(-minimum / scale), 0.0, 15.0)

    # Scale and zero are serialized as FP16 metadata.  Codes are derived from
    # the FP32 extrema so that the quantizer matches the original Transformer
    # packer rather than the LM-head-specific rounded-metadata path.
    scale_half = scale.astype("<f2")
    zero_half = zero.astype("<f2")
    codes = np.clip(
        np.rint(weights / scale[:, None] + zero[:, None]), 0, 15
    ).astype(np.uint8)
    packed = codes[:, 0::2] | (codes[:, 1::2] << 4)

    outputs = int(weights.shape[0])
    blocks = outputs // OUTPUTS_PER_BLOCK
    packet = np.empty((blocks, PACKET_BYTES), dtype=np.uint8)
    packet[:, :256] = packed.reshape(blocks, 256)
    packet[:, 256:272] = (
        scale_half.reshape(blocks, OUTPUTS_PER_BLOCK)
        .view(np.uint8)
        .reshape(blocks, 16)
    )
    packet[:, 272:288] = (
        zero_half.reshape(blocks, OUTPUTS_PER_BLOCK)
        .view(np.uint8)
        .reshape(blocks, 16)
    )
    return packet.tobytes(order="C")


def pack_linears(
    model_dir: Path,
    mapping: dict[str, str],
    names: list[str],
    output_path: Path,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    offset = 0
    with output_path.open("wb") as destination:
        for ordinal, name in enumerate(names):
            rows, columns = tensor_shape(model_dir, mapping, name)
            if rows % OUTPUTS_PER_BLOCK or columns % GROUP_SIZE:
                raise ValueError(
                    f"{name} shape {(rows, columns)} violates GS64/8-output layout"
                )
            groups = columns // GROUP_SIZE
            blocks = rows // OUTPUTS_PER_BLOCK
            tensor_digest = hashlib.sha256()
            with safe_open(
                model_dir / mapping[name], framework="pt", device="cpu"
            ) as source:
                view = source.get_slice(name)
                for group in range(groups):
                    start = group * GROUP_SIZE
                    values = (
                        view[:, start : start + GROUP_SIZE]
                        .to(dtype=torch.float32)
                        .contiguous()
                        .numpy()
                    )
                    encoded = quantize_group(values)
                    destination.write(encoded)
                    tensor_digest.update(encoded)
            byte_count = groups * blocks * PACKET_BYTES
            entries.append(
                {
                    "ordinal": ordinal,
                    "name": name,
                    "shape": [rows, columns],
                    "input_groups": groups,
                    "output_blocks": blocks,
                    "offset": offset,
                    "bytes": byte_count,
                    "sha256": tensor_digest.hexdigest(),
                }
            )
            offset += byte_count
            print(
                json.dumps(
                    {
                        "kind": "linear",
                        "ordinal": ordinal + 1,
                        "total": len(names),
                        "name": name,
                        "bytes": byte_count,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    return entries


def pack_auxiliary(
    model_dir: Path,
    mapping: dict[str, str],
    names: list[str],
    output_path: Path,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    offset = 0
    with output_path.open("wb") as destination:
        for ordinal, name in enumerate(names):
            shape = tensor_shape(model_dir, mapping, name)
            tensor_digest = hashlib.sha256()
            with safe_open(
                model_dir / mapping[name], framework="pt", device="cpu"
            ) as source:
                view = source.get_slice(name)
                rows = shape[0] if shape else 1
                for start in range(0, rows, AUX_ROW_CHUNK):
                    tensor = view[start : start + AUX_ROW_CHUNK]
                    array = tensor.to(dtype=torch.float16).contiguous().numpy()
                    encoded = array.astype("<f2", copy=False).tobytes(order="C")
                    destination.write(encoded)
                    tensor_digest.update(encoded)
            byte_count = int(np.prod(shape, dtype=np.int64)) * 2
            entries.append(
                {
                    "name": name,
                    "shape": list(shape),
                    "dtype": "float16",
                    "offset": offset,
                    "bytes": byte_count,
                    "sha256": tensor_digest.hexdigest(),
                }
            )
            offset += byte_count
            print(
                json.dumps(
                    {
                        "kind": "aux",
                        "ordinal": ordinal + 1,
                        "total": len(names),
                        "name": name,
                        "bytes": byte_count,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    return entries


def copy_runtime_metadata(model_dir: Path, output_dir: Path) -> None:
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        source = model_dir / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, output_dir / name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--linear-limit", type=int)
    parser.add_argument("--skip-aux", action="store_true")
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads((model_dir / "config.json").read_text())
    layers = int(config["num_hidden_layers"])
    mapping = tensor_map(model_dir)

    names = linear_names(layers)
    if args.linear_limit is not None:
        names = names[: int(args.linear_limit)]
    linear_path = output_dir / f"{args.tag}_linears_w4g64.mgs"
    aux_path = output_dir / f"{args.tag}_aux_fp16.bin"
    index_path = output_dir / f"{args.tag}_mixed_gs_index.json"

    linears = pack_linears(model_dir, mapping, names, linear_path)
    auxiliary = (
        []
        if args.skip_aux
        else pack_auxiliary(
            model_dir, mapping, auxiliary_names(layers), aux_path
        )
    )
    copy_runtime_metadata(model_dir, output_dir)

    index = {
        "linear_file": {
            "path": str(linear_path),
            "bytes": linear_path.stat().st_size,
            "sha256": file_sha256(linear_path),
        },
        "aux_file": None
        if args.skip_aux
        else {
            "path": str(aux_path),
            "bytes": aux_path.stat().st_size,
            "sha256": file_sha256(aux_path),
        },
        "linears": linears,
        "aux_tensors": auxiliary,
        "source": {
            "model_dir": str(model_dir),
            "architecture": config.get("architectures"),
            "hidden_size": int(config["hidden_size"]),
            "intermediate_size": int(config["intermediate_size"]),
            "num_hidden_layers": layers,
            "vocab_size": int(config["vocab_size"]),
            "linear_quantization": "asymmetric-w4-gs64-fp16-metadata",
        },
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "index": str(index_path),
                "linears": len(linears),
                "aux_tensors": len(auxiliary),
                "linear_bytes": linear_path.stat().st_size,
                "aux_bytes": 0 if args.skip_aux else aux_path.stat().st_size,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
