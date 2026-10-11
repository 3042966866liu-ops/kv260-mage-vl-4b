#!/usr/bin/env python3
"""Regress the HS64/HLS-half reference against retained legacy-X1 CSim output."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_descriptor(raw: bytes) -> np.ndarray:
    words = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8)
    packed = np.empty((words.shape[0], 2), dtype="<u2")
    packed[:, 0] = words[:, :2].copy().view("<u2").reshape(-1)
    packed[:, 1] = words[:, 4:6].copy().view("<u2").reshape(-1)
    values = packed.view("<f2").reshape(1, 32, 4, 4, 2)
    return values.transpose(1, 2, 0, 3, 4).reshape(32, 32).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    candidate = workspace / "deployment/mage_vl4b/m89x1_hostscale64_board_candidate_c464"
    runtime = candidate / "runtime"
    sys.path.insert(0, str(runtime))
    sys.path.insert(0, str(workspace / "scripts"))
    from contract_runtime import RuntimeContract, quantize_t32
    from m89x1_layer0_tolerance_diagnostic import deterministic_input
    from m89x1_qkv_reference_helper import reference_descriptor
    from text_e2e_gate import rms_norm

    contract = RuntimeContract.load(
        candidate / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
        "PASS_MERGED_648_TILE_RUNTIME_CONTRACT")
    chain = next(item for item in contract.chains if int(item["layer"]) == 0 and item["family"] == "qkv")
    auxiliary = np.load(candidate / "auxiliary/m77_text_aux_fp16.npz", allow_pickle=False)
    try:
        values = rms_norm(
            deterministic_input(),
            np.asarray(auxiliary["model.language_model.layers.0.input_layernorm.weight"], dtype=np.float32))
    finally:
        auxiliary.close()
    _, codes, scales = quantize_t32(values, int(chain["groups"]), activation_scale_shift=6)
    layout = workspace / "deployment/mage_vl4b/artifacts/m89y_language_fourport"
    shards = [layout / f"weights{index}.bin" for index in range(4)]
    output_path = workspace / "deployment/mage_vl4b/artifacts/m89x1_layer0_norm_qkv_host_scale64_legacy_output.bin"
    raw = output_path.read_bytes()
    bytes_per_descriptor = 32 * 4 * 4 * 8
    comparisons = {}
    cursor = 0
    all_observed, all_reference = [], []
    for descriptor in chain["descriptors"]:
        full = reference_descriptor(
            shards, descriptor, chain, codes, scales,
            activation_scale_shift=6, hls_flush_subnormals=True)
        rows = int(descriptor["rows_per_shard"])
        reference = np.concatenate([full[:, shard * rows:shard * rows + 8] for shard in range(4)], axis=1)
        observed = np.ldexp(
            parse_descriptor(raw[cursor:cursor + bytes_per_descriptor]), -6).astype(np.float32)
        cursor += bytes_per_descriptor
        delta = observed.astype(np.float64) - reference.astype(np.float64)
        norm = max(float(np.linalg.norm(reference.astype(np.float64))), 1e-12)
        comparisons[str(descriptor["module"])] = {
            "element_count": int(observed.size),
            "fp16_exact_count": int(np.count_nonzero(observed.astype("<f2") == reference.astype("<f2"))),
            "max_abs": float(np.max(np.abs(delta))),
            "relative_l2": float(np.linalg.norm(delta) / norm),
        }
        all_observed.append(observed)
        all_reference.append(reference)
    if cursor != len(raw):
        raise RuntimeError("legacy CSim output byte count mismatch")
    observed = np.concatenate(all_observed, axis=1)
    reference = np.concatenate(all_reference, axis=1)
    delta = observed.astype(np.float64) - reference.astype(np.float64)
    norm = max(float(np.linalg.norm(reference.astype(np.float64))), 1e-12)
    exact = int(np.count_nonzero(observed.astype("<f2") == reference.astype("<f2")))
    summary = {
        "element_count": int(observed.size),
        "fp16_exact_count": exact,
        "fp16_exact_fraction": exact / observed.size,
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
        "relative_l2": float(np.linalg.norm(delta) / norm),
    }
    passed = (summary["max_abs"] <= 0.001 and summary["mean_abs"] <= 1e-5 and
              summary["rmse"] <= 4e-5 and summary["relative_l2"] <= 2e-4 and
              summary["fp16_exact_fraction"] >= 0.94)
    result = {
        "date": "2026-08-31",
        "gate": "M89-X1-HS64-HLS-half-reference-regression",
        "status": "PASS" if passed else "FAIL",
        "legacy_csim_output_sha256": sha256(output_path),
        "activation_scale_shift": 6,
        "summary": summary,
        "descriptors": comparisons,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M89X1_HS64_HLS_HALF_REFERENCE_PASS" if passed else "M89X1_HS64_HLS_HALF_REFERENCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
