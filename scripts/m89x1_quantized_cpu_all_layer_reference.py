#!/usr/bin/env python3
"""Independent all-layer CPU reference for the M89-X1 text path.

This is intentionally an offline diagnostic.  It reloads the exact M56 mixed-
bit checkpoint, applies the same A8-G64 input QDQ to every language Linear and
the LM head, restores the prompt embedding rows used by the board candidate,
and captures the four shared Linear-family inputs in all 36 decoder layers.

The result distinguishes a model-level quantization divergence from an FPGA
operator defect.  It is never board or deployment evidence by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


LAYERS = 36
FAMILIES = {
    "qkv": "self_attn.q_proj",
    "attention_out": "self_attn.o_proj",
    "gate_up": "mlp.gate_proj",
    "mlp_down": "mlp.down_proj",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tensor_metrics(torch, observed, reference) -> dict[str, object]:
    observed = observed.to(dtype=torch.float64, device="cpu")
    reference = reference.to(dtype=torch.float64, device="cpu")
    if tuple(observed.shape) != tuple(reference.shape):
        raise RuntimeError(
            f"metric shape mismatch: {tuple(observed.shape)} != {tuple(reference.shape)}"
        )
    delta = observed - reference
    ref_norm = max(float(torch.linalg.vector_norm(reference)), 1.0e-12)
    obs_norm = max(float(torch.linalg.vector_norm(observed)), 1.0e-12)
    return {
        "shape": list(observed.shape),
        "finite": bool(torch.isfinite(observed).all()),
        "bf16_exact_count": int(
            torch.count_nonzero(observed.to(torch.bfloat16) == reference.to(torch.bfloat16))
        ),
        "element_count": int(observed.numel()),
        "max_abs": float(delta.abs().max()),
        "mean_abs": float(delta.abs().mean()),
        "rmse": float(torch.sqrt(torch.mean(delta * delta))),
        "relative_l2": float(torch.linalg.vector_norm(delta) / ref_norm),
        "cosine": float(torch.vdot(observed.reshape(-1), reference.reshape(-1)) / (obs_norm * ref_norm)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--official-hidden", type=Path, required=True)
    parser.add_argument("--auxiliary", type=Path, required=True)
    parser.add_argument("--auxiliary-manifest", type=Path, required=True)
    parser.add_argument("--capture-output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--row-chunk", type=int, default=32)
    args = parser.parse_args()

    sys.path.insert(0, str(args.deps.resolve()))
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM

    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    started = time.perf_counter()
    result: dict[str, object] = {
        "gate": "M89-X1-independent-quantized-CPU-all-layer-reference",
        "status": "FAIL",
        "classification": (
            "offline same-quantized-model CPU reference; not FPGA execution or deployment evidence"
        ),
    }
    auxiliary_npz = None
    official_npz = None
    capture_handles = []
    a8_handles = []
    try:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        prompt_ids = [int(value) for value in reference["prompt_token_ids"]]
        official_token = int(reference["generated_token_ids"][0])
        if len(prompt_ids) != 30:
            raise RuntimeError("fixed reference must contain exactly 30 prompt tokens")

        aux_manifest = json.loads(args.auxiliary_manifest.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS":
            raise RuntimeError("auxiliary manifest is not PASS")
        if sha256(args.auxiliary) != aux_manifest.get("payload_sha256"):
            raise RuntimeError("auxiliary payload hash mismatch")

        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        reload_info = load_packed_checkpoint(
            torch, model, args.checkpoint, verify_blob=True, row_chunk=args.row_chunk
        )

        auxiliary_npz = np.load(args.auxiliary, allow_pickle=False)
        embedding_rows = torch.from_numpy(
            np.asarray(auxiliary_npz["model.language_model.embed_tokens.weight"], dtype=np.float32)
        ).to(torch.bfloat16)
        embedding_ids = [int(value) for value in aux_manifest["selected_embedding_ids"]]
        if embedding_rows.shape != (len(embedding_ids), 2560):
            raise RuntimeError(f"unexpected selected embedding shape: {embedding_rows.shape}")
        embedding = model.get_input_embeddings().weight
        with torch.no_grad():
            embedding[torch.tensor(embedding_ids, dtype=torch.long)] = embedding_rows

        modules = dict(model.named_modules())
        requested: dict[str, str] = {}
        for layer in range(LAYERS):
            for family, suffix in FAMILIES.items():
                logical = f"layer{layer:02d}_{family}"
                exact = f"model.language_model.layers.{layer}.{suffix}"
                if exact in modules:
                    requested[logical] = exact
                    continue
                matches = [
                    name for name in modules
                    if name.endswith(f"language_model.layers.{layer}.{suffix}")
                ]
                if len(matches) != 1:
                    raise RuntimeError(
                        f"target discovery failed logical={logical} matches={matches}"
                    )
                requested[logical] = matches[0]

        captured: dict[str, object] = {}

        def make_hook(logical: str):
            def hook(_module, positional):
                if logical in captured:
                    raise RuntimeError(f"duplicate captured family input: {logical}")
                if not positional or not torch.is_tensor(positional[0]):
                    raise RuntimeError(f"invalid family input: {logical}")
                value = positional[0].detach().to(dtype=torch.float32, device="cpu")
                if value.ndim != 3 or value.shape[0] != 1:
                    raise RuntimeError(f"invalid family shape: {logical} {tuple(value.shape)}")
                captured[logical] = value[0].contiguous()
            return hook

        # Capture the logical family input before the A8 pre-hook modifies it.
        for logical, actual in requested.items():
            capture_handles.append(
                modules[actual].register_forward_pre_hook(make_hook(logical))
            )
        a8_handles, a8_modules = install_packed_linear_a8_hooks(
            torch,
            model,
            args.checkpoint,
            r"^(model\.language_model\.layers\.|lm_head$)",
        )

        input_ids = torch.tensor([prompt_ids], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)
        with torch.inference_mode():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=False,
                return_dict=True,
            )
        logits = outputs.logits[0, -1].to(dtype=torch.float32, device="cpu")
        generated_token = int(torch.argmax(logits))

        if len(captured) != LAYERS * len(FAMILIES):
            missing = sorted(set(requested) - set(captured))
            raise RuntimeError(f"all-layer capture incomplete count={len(captured)} missing={missing}")
        official_npz = np.load(args.official_hidden, allow_pickle=False)
        if set(official_npz.files) != set(requested):
            raise RuntimeError("official hidden-state key set mismatch")

        metrics = {}
        first_non_exact = None
        first_relative_l2_over_1e3 = None
        for layer in range(LAYERS):
            for family in FAMILIES:
                logical = f"layer{layer:02d}_{family}"
                expected = torch.from_numpy(
                    np.asarray(official_npz[logical], dtype=np.float32)
                )
                item = tensor_metrics(torch, captured[logical], expected)
                metrics[logical] = item
                if first_non_exact is None and item["bf16_exact_count"] != item["element_count"]:
                    first_non_exact = logical
                if first_relative_l2_over_1e3 is None and item["relative_l2"] > 1.0e-3:
                    first_relative_l2_over_1e3 = logical

        args.capture_output.parent.mkdir(parents=True, exist_ok=True)
        capture_temporary = args.capture_output.with_suffix(args.capture_output.suffix + ".tmp")
        with capture_temporary.open("wb") as handle:
            np.savez(
                handle,
                **{
                    logical: captured[logical].numpy().astype(np.float32, copy=False)
                    for logical in sorted(captured)
                },
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(capture_temporary, args.capture_output)

        result.update(
            status="MEASURED",
            source_checkpoint={
                **reload_info,
                "path": str(args.checkpoint.resolve()),
            },
            prompt_token_count=len(prompt_ids),
            official_bf16_token_id=official_token,
            quantized_cpu_token_id=generated_token,
            token_matches_official_bf16=generated_token == official_token,
            board_observed_token_id=18,
            token_matches_board_observation=generated_token == 18,
            selected_embedding_rows_restored=len(embedding_ids),
            a8_hook_count=len(a8_modules),
            expected_language_plus_head_a8_hooks=253,
            capture_count=len(captured),
            expected_capture_count=LAYERS * len(FAMILIES),
            capture_output=str(args.capture_output.resolve()),
            capture_output_bytes=args.capture_output.stat().st_size,
            capture_output_sha256=sha256(args.capture_output),
            all_captured_finite=all(item["finite"] for item in metrics.values()),
            first_bf16_non_exact_family_input=first_non_exact,
            first_family_input_relative_l2_over_1e3=first_relative_l2_over_1e3,
            family_input_metrics=metrics,
            interpretation=(
                "If token 18 is reproduced, the official BF16 token 17 is not a valid sole acceptance "
                "oracle for the W2/W4+A8 candidate; FPGA-vs-independent-quantized trace remains required. "
                "If token 17 remains, the FPGA/PS path still contains a model-semantic divergence."
            ),
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for handle in reversed(a8_handles):
            handle.remove()
        for handle in reversed(capture_handles):
            handle.remove()
        if official_npz is not None:
            official_npz.close()
        if auxiliary_npz is not None:
            auxiliary_npz.close()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_suffix(args.result.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, args.result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    marker = (
        "M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_MEASURED"
        if result["status"] == "MEASURED"
        else "M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_FAIL"
    )
    print(marker, flush=True)
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
