#!/usr/bin/env python3
"""Trace the first non-finite stage in the fixed-text M89-X1 HS64 path."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np


LAYERS, HEADS, KV_HEADS, HEAD_DIM = 36, 32, 8, 128
SCALE_SHIFT = 6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stats(values: np.ndarray) -> dict[str, object]:
    array = np.asarray(values, dtype=np.float32)
    finite = np.isfinite(array)
    valid = array[finite]
    return {
        "shape": list(array.shape),
        "finite": bool(finite.all()),
        "nan_count": int(np.count_nonzero(np.isnan(array))),
        "posinf_count": int(np.count_nonzero(np.isposinf(array))),
        "neginf_count": int(np.count_nonzero(np.isneginf(array))),
        "finite_min": float(np.min(valid)) if valid.size else None,
        "finite_max": float(np.max(valid)) if valid.size else None,
        "finite_max_abs": float(np.max(np.abs(valid))) if valid.size else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate
    runtime_root = candidate / "runtime"
    sys.path.insert(0, str(runtime_root))
    from board_runtime import M89XBoardRuntime
    from contract_runtime import quantize_t32
    from text_e2e_gate import FixedTextModel, apply_rope, attention, rms_norm, silu

    result: dict[str, object] = {
        "gate": "M89-X1-HS64-fixed-text-first-nonfinite-trace",
        "status": "FAIL",
        "base_package_manifest_sha256": args.expected_package_manifest_sha256,
        "activation_scale_shift": SCALE_SHIFT,
        "activation_scale_factor": 1 << SCALE_SHIFT,
    }
    runtime = None
    payload = None
    started = time.monotonic()
    trace: list[dict[str, object]] = []
    first_nonfinite = None

    def record(stage: str, layer: int, values: np.ndarray) -> bool:
        nonlocal first_nonfinite
        item = {"layer": layer, "stage": stage, "output": stats(values)}
        trace.append(item)
        if not item["output"]["finite"] and first_nonfinite is None:
            first_nonfinite = item
            return False
        return True

    def run_family(layer: int, family_name: str, values: np.ndarray) -> dict[str, np.ndarray] | None:
        nonlocal first_nonfinite
        chain = next(item for item in runtime.language_contract.chains
                     if int(item["layer"]) == layer and item["family"] == family_name)
        item: dict[str, object] = {
            "layer": layer,
            "stage": family_name,
            "input": stats(values),
            "groups": int(chain["groups"]),
        }
        if item["input"]["finite"]:
            _, _, transmitted = quantize_t32(values, int(chain["groups"]),
                                              activation_scale_shift=SCALE_SHIFT)
            item["transmitted_scale"] = stats(transmitted)
        outputs = runtime.language_family(layer, family_name, values)
        item["outputs"] = {name: stats(value) for name, value in outputs.items()}
        trace.append(item)
        bad = {name: metric for name, metric in item["outputs"].items()
               if not metric["finite"]}
        if bad:
            first_nonfinite = {"layer": layer, "stage": family_name, "outputs": bad}
            return None
        return outputs

    try:
        manifest_path = candidate / "PACKAGE_MANIFEST.json"
        if sha256(manifest_path) != args.expected_package_manifest_sha256:
            raise RuntimeError("candidate package manifest hash mismatch")
        reference = json.loads((candidate / "auxiliary/official_cpu_text_1token.json").read_text(encoding="utf-8"))
        token_ids = [int(value) for value in reference["prompt_token_ids"]]
        aux_manifest_path = candidate / "auxiliary/M77_TEXT_AUX_MANIFEST.json"
        aux_path = candidate / "auxiliary/m77_text_aux_fp16.npz"
        aux_manifest = json.loads(aux_manifest_path.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS" or aux_manifest.get("payload_sha256") != sha256(aux_path):
            raise RuntimeError("auxiliary identity failed")
        payload = np.load(aux_path, allow_pickle=False)
        auxiliary = {name: payload[name] for name in payload.files}
        runtime = M89XBoardRuntime(
            candidate / "overlay/m89x_t32.bit",
            Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport"),
            Path("/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport"),
            candidate / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
            candidate / "contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "staged-low-cma",
        )
        model = FixedTextModel(runtime, auxiliary,
                               [int(value) for value in aux_manifest["selected_embedding_ids"]])
        hidden = np.stack([model.embedding[token] for token in token_ids]).astype(np.float32)
        record("embedding", -1, hidden)
        for layer in range(LAYERS):
            prefix = f"model.language_model.layers.{layer}"
            residual = hidden
            normed = rms_norm(hidden, model.weight(f"{prefix}.input_layernorm.weight"))
            if not record("input_rmsnorm", layer, normed):
                break
            qkv = run_family(layer, "qkv", normed)
            if qkv is None:
                break
            query = qkv[f"{prefix}.self_attn.q_proj"][:len(token_ids)].reshape(-1, HEADS, HEAD_DIM)
            key = qkv[f"{prefix}.self_attn.k_proj"][:len(token_ids)].reshape(-1, KV_HEADS, HEAD_DIM)
            value = qkv[f"{prefix}.self_attn.v_proj"][:len(token_ids)].reshape(-1, KV_HEADS, HEAD_DIM)
            query = rms_norm(query, model.weight(f"{prefix}.self_attn.q_norm.weight"))
            key = rms_norm(key, model.weight(f"{prefix}.self_attn.k_norm.weight"))
            query, key = apply_rope(query, key)
            attention_value = attention(query, key, value)
            if not record("attention_ps", layer, attention_value):
                break
            projected = run_family(layer, "attention_out", attention_value)
            if projected is None:
                break
            hidden = residual + projected[f"{prefix}.self_attn.o_proj"][:len(token_ids)]
            if not record("post_attention_residual", layer, hidden):
                break
            residual = hidden
            normed = rms_norm(hidden, model.weight(f"{prefix}.post_attention_layernorm.weight"))
            if not record("post_attention_rmsnorm", layer, normed):
                break
            gate_up = run_family(layer, "gate_up", normed)
            if gate_up is None:
                break
            gate = gate_up[f"{prefix}.mlp.gate_proj"][:len(token_ids)]
            up = gate_up[f"{prefix}.mlp.up_proj"][:len(token_ids)]
            down_input = silu(gate) * up
            if not record("mlp_product_ps", layer, down_input):
                break
            down = run_family(layer, "mlp_down", down_input)
            if down is None:
                break
            hidden = residual + down[f"{prefix}.mlp.down_proj"][:len(token_ids)]
            if not record("layer_output", layer, hidden):
                break
        result.update(
            status="MEASURED",
            first_nonfinite=first_nonfinite,
            trace=trace,
            evidence=runtime.evidence(),
            conclusion=("first non-finite stage captured" if first_nonfinite
                        else "no non-finite stage observed"),
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["trace"] = trace
        if runtime is not None:
            result["evidence"] = runtime.evidence()
    finally:
        if runtime is not None:
            runtime.close()
        if payload is not None:
            payload.close()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    measured = result.get("status") == "MEASURED" and result.get("first_nonfinite") is not None
    print("M89X1_HS64_FIXED_TEXT_TRACE_MEASURED" if measured
          else "M89X1_HS64_FIXED_TEXT_TRACE_FAIL")
    return 0 if measured else 1


if __name__ == "__main__":
    raise SystemExit(main())
