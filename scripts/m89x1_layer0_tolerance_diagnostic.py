#!/usr/bin/env python3
"""Measure one complete Layer-0 Mage-VL text block through the M89-X1 FPGA.

This is a diagnostic, not an acceptance gate: it preserves independent direct
packed-weight references for all four hardware families, while the non-linear
Transformer operations run on PS in the same FP32 order on both paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


INPUT_SHA256 = "04457eb7f805ddb89bff1543e307844e7c6ccaa8f3593bbd18dda68cd23fa22f"
HS64_INPUT_SHA256 = "58dc6b0b43975d39027c32263325689590d74c3de03c2f04e5f1759b3c4c392e"
ACTIVATION_SCALE_SHIFT = 6
LAYER, HEADS, KV_HEADS, HEAD_DIM = 0, 32, 8, 128


def deterministic_input() -> np.ndarray:
    index = np.arange(32 * 2560, dtype=np.float32).reshape(32, 2560)
    return (np.sin(index * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)


def metrics(observed: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    observed = np.asarray(observed, dtype=np.float32)
    reference = np.asarray(reference, dtype=np.float32)
    delta = observed.astype(np.float64) - reference.astype(np.float64)
    reference_norm = max(float(np.linalg.norm(reference.astype(np.float64))), 1e-12)
    observed_norm = max(float(np.linalg.norm(observed.astype(np.float64))), 1e-12)
    return {
        "shape": list(observed.shape),
        "finite": bool(np.isfinite(observed).all()),
        "fp16_exact_count": int(np.count_nonzero(np.asarray(observed, dtype="<f2") == np.asarray(reference, dtype="<f2"))),
        "element_count": int(observed.size),
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
        "relative_l2": float(np.linalg.norm(delta) / reference_norm),
        "cosine": float(np.vdot(observed.reshape(-1).astype(np.float64), reference.reshape(-1).astype(np.float64)) / (observed_norm * reference_norm)),
    }


def assemble_reference(chain: dict, values: np.ndarray, language_root: Path) -> dict[str, np.ndarray]:
    from contract_runtime import quantize_t32
    from m89x1_qkv_reference_helper import reference_descriptor

    _, codes, activation_scales = quantize_t32(
        values, int(chain["groups"]), activation_scale_shift=ACTIVATION_SCALE_SHIFT)
    shards = [language_root / f"weights{index}.bin" for index in range(4)]
    output: dict[str, np.ndarray] = {}
    for descriptor in chain["descriptors"]:
        tile = reference_descriptor(
            shards, descriptor, chain, codes, activation_scales,
            activation_scale_shift=ACTIVATION_SCALE_SHIFT,
            hls_flush_subnormals=True)
        name = str(descriptor["module"])
        start = int(descriptor["row_start"])
        stop = start + int(descriptor["valid_rows"])
        prior = output.get(name)
        if prior is None:
            prior = np.zeros((32, stop), dtype=np.float32)
        elif prior.shape[1] < stop:
            grown = np.zeros((32, stop), dtype=np.float32)
            grown[:, :prior.shape[1]] = prior
            prior = grown
        prior[:, start:stop] = tile[:, :int(descriptor["valid_rows"])]
        output[name] = prior
    return {name: np.asarray(value, dtype=np.float32) for name, value in output.items()}


def family(runtime, family_name: str, reference_values: np.ndarray, observed_values: np.ndarray,
           language_root: Path) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, np.ndarray], dict]:
    chain = next(item for item in runtime.language_contract.chains if int(item["layer"]) == LAYER and item["family"] == family_name)
    reference = assemble_reference(chain, reference_values, language_root)
    if np.array_equal(reference_values, observed_values):
        same_input_reference = reference
    else:
        same_input_reference = assemble_reference(chain, observed_values, language_root)
    observed = runtime.language_family(LAYER, family_name, observed_values)
    return ({name: np.asarray(value, dtype=np.float32) for name, value in observed.items()},
            reference, same_input_reference, chain)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.candidate
    sys.path.insert(0, str(root / "runtime"))
    from board_runtime import BUILD_ID, M89XBoardRuntime
    from contract_runtime import pack_chain_input
    from text_e2e_gate import apply_rope, attention, rms_norm, silu

    result: dict[str, object] = {
        "gate": "M89-X1-layer0-full-transformer-tolerance-diagnostic",
        "status": "FAIL",
        "base_package_manifest_sha256": args.expected_package_manifest_sha256,
    }
    runtime = None
    payload = None
    began = time.monotonic()
    try:
        package_manifest_path = root / "PACKAGE_MANIFEST.json"
        if hashlib.sha256(package_manifest_path.read_bytes()).hexdigest() != args.expected_package_manifest_sha256:
            raise RuntimeError("candidate package manifest hash mismatch")
        manifest_path = root / "auxiliary/M77_TEXT_AUX_MANIFEST.json"
        payload_path = root / "auxiliary/m77_text_aux_fp16.npz"
        aux_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS":
            raise RuntimeError("auxiliary manifest is not PASS")
        if hashlib.sha256(payload_path.read_bytes()).hexdigest() != aux_manifest.get("payload_sha256"):
            raise RuntimeError("auxiliary payload hash mismatch")
        payload = np.load(payload_path, allow_pickle=False)
        auxiliary = {name: np.asarray(payload[name], dtype=np.float32) for name in payload.files}
        language_root = Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport")
        head_root = Path("/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport")
        runtime = M89XBoardRuntime(root / "overlay/m89x_t32.bit", language_root, head_root,
                                  root / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
                                  root / "contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json", "staged-low-cma")
        hidden_reference = deterministic_input()
        hidden_observed = hidden_reference.copy()
        qkv_chain = next(item for item in runtime.language_contract.chains if int(item["layer"]) == LAYER and item["family"] == "qkv")
        if hashlib.sha256(pack_chain_input(qkv_chain, hidden_reference)).hexdigest() != INPUT_SHA256:
            raise RuntimeError("deterministic input packet hash mismatch")
        scaled_input_sha256 = hashlib.sha256(
            pack_chain_input(qkv_chain, hidden_reference,
                             activation_scale_shift=ACTIVATION_SCALE_SHIFT)).hexdigest()
        if scaled_input_sha256 != HS64_INPUT_SHA256:
            raise RuntimeError("HS64 deterministic input packet hash mismatch")
        prefix = f"model.language_model.layers.{LAYER}"
        metrics_out: dict[str, dict[str, object]] = {}
        local_metrics: dict[str, dict[str, object]] = {}
        propagation_metrics: dict[str, dict[str, object]] = {}
        family_input_metrics: dict[str, dict[str, object]] = {}

        residual_reference = hidden_reference
        residual_observed = hidden_observed
        norm_weight = auxiliary[f"{prefix}.input_layernorm.weight"]
        norm_reference = rms_norm(hidden_reference, norm_weight)
        norm_observed = rms_norm(hidden_observed, norm_weight)
        qkv_observed, qkv_reference, qkv_same_input, _ = family(
            runtime, "qkv", norm_reference, norm_observed, language_root)
        family_input_metrics["qkv"] = metrics(norm_observed, norm_reference)
        for name, value in qkv_observed.items():
            metrics_out[name] = metrics(value, qkv_reference[name])
            local_metrics[name] = metrics(value, qkv_same_input[name])
            propagation_metrics[name] = metrics(qkv_same_input[name], qkv_reference[name])
        q_ref = qkv_reference[f"{prefix}.self_attn.q_proj"].reshape(32, HEADS, HEAD_DIM)
        k_ref = qkv_reference[f"{prefix}.self_attn.k_proj"].reshape(32, KV_HEADS, HEAD_DIM)
        v_ref = qkv_reference[f"{prefix}.self_attn.v_proj"].reshape(32, KV_HEADS, HEAD_DIM)
        q_obs = qkv_observed[f"{prefix}.self_attn.q_proj"].reshape(32, HEADS, HEAD_DIM)
        k_obs = qkv_observed[f"{prefix}.self_attn.k_proj"].reshape(32, KV_HEADS, HEAD_DIM)
        v_obs = qkv_observed[f"{prefix}.self_attn.v_proj"].reshape(32, KV_HEADS, HEAD_DIM)
        q_ref = rms_norm(q_ref, auxiliary[f"{prefix}.self_attn.q_norm.weight"])
        k_ref = rms_norm(k_ref, auxiliary[f"{prefix}.self_attn.k_norm.weight"])
        q_obs = rms_norm(q_obs, auxiliary[f"{prefix}.self_attn.q_norm.weight"])
        k_obs = rms_norm(k_obs, auxiliary[f"{prefix}.self_attn.k_norm.weight"])
        q_ref, k_ref = apply_rope(q_ref, k_ref)
        q_obs, k_obs = apply_rope(q_obs, k_obs)
        attention_reference = attention(q_ref, k_ref, v_ref)
        attention_observed = attention(q_obs, k_obs, v_obs)
        family_input_metrics["attention_out"] = metrics(attention_observed, attention_reference)
        out_observed, out_reference, out_same_input, _ = family(
            runtime, "attention_out", attention_reference, attention_observed, language_root)
        out_name = f"{prefix}.self_attn.o_proj"
        metrics_out[out_name] = metrics(out_observed[out_name], out_reference[out_name])
        local_metrics[out_name] = metrics(out_observed[out_name], out_same_input[out_name])
        propagation_metrics[out_name] = metrics(out_same_input[out_name], out_reference[out_name])
        hidden_reference = residual_reference + out_reference[out_name]
        hidden_observed = residual_observed + out_observed[out_name]

        residual_reference = hidden_reference
        residual_observed = hidden_observed
        post_weight = auxiliary[f"{prefix}.post_attention_layernorm.weight"]
        post_reference = rms_norm(hidden_reference, post_weight)
        post_observed = rms_norm(hidden_observed, post_weight)
        family_input_metrics["gate_up"] = metrics(post_observed, post_reference)
        gu_observed, gu_reference, gu_same_input, _ = family(
            runtime, "gate_up", post_reference, post_observed, language_root)
        gate_name, up_name = f"{prefix}.mlp.gate_proj", f"{prefix}.mlp.up_proj"
        metrics_out[gate_name] = metrics(gu_observed[gate_name], gu_reference[gate_name])
        metrics_out[up_name] = metrics(gu_observed[up_name], gu_reference[up_name])
        local_metrics[gate_name] = metrics(gu_observed[gate_name], gu_same_input[gate_name])
        local_metrics[up_name] = metrics(gu_observed[up_name], gu_same_input[up_name])
        propagation_metrics[gate_name] = metrics(gu_same_input[gate_name], gu_reference[gate_name])
        propagation_metrics[up_name] = metrics(gu_same_input[up_name], gu_reference[up_name])
        down_input_reference = silu(gu_reference[gate_name]) * gu_reference[up_name]
        down_input_observed = silu(gu_observed[gate_name]) * gu_observed[up_name]
        family_input_metrics["mlp_down"] = metrics(down_input_observed, down_input_reference)
        down_observed, down_reference, down_same_input, _ = family(
            runtime, "mlp_down", down_input_reference, down_input_observed, language_root)
        down_name = f"{prefix}.mlp.down_proj"
        metrics_out[down_name] = metrics(down_observed[down_name], down_reference[down_name])
        local_metrics[down_name] = metrics(down_observed[down_name], down_same_input[down_name])
        propagation_metrics[down_name] = metrics(down_same_input[down_name], down_reference[down_name])
        hidden_reference = residual_reference + down_reference[down_name]
        hidden_observed = residual_observed + down_observed[down_name]
        metrics_out["layer0.output"] = metrics(hidden_observed, hidden_reference)

        evidence = runtime.evidence()
        expected_calls = 4
        expected_macros = sum(int(item["expected_macros"]) for item in runtime.language_contract.chains if int(item["layer"]) == LAYER)
        if evidence["build_id"] != f"0x{BUILD_ID:08x}" or evidence["host_calls"] != expected_calls or evidence["expected_macros"] != expected_macros:
            raise RuntimeError(f"hardware evidence mismatch: {evidence}")
        result.update(status="MEASURED", evidence=evidence, expected_calls=expected_calls,
                      expected_macros=expected_macros, scaled_input_sha256=scaled_input_sha256,
                      metrics=metrics_out, local_metrics=local_metrics,
                      propagation_metrics=propagation_metrics,
                      family_input_metrics=family_input_metrics,
                      acceptance_note=("Apply the retained strict single-operator thresholds only to local_metrics (C versus B). "
                                       "metrics and propagation_metrics remain explicit end-to-end propagation evidence."))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if runtime is not None:
            runtime.close()
        if payload is not None:
            payload.close()
        result["total_ms"] = (time.monotonic() - began) * 1000.0
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    print("M89X1_LAYER0_TOLERANCE_DIAGNOSTIC_MEASURED" if result["status"] == "MEASURED" else "M89X1_LAYER0_TOLERANCE_DIAGNOSTIC_FAIL")
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
