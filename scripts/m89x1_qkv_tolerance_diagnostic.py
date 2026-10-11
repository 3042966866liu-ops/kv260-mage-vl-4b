#!/usr/bin/env python3
"""Full-output numerical comparison for the single M89-X1 Layer-0 QKV chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


EXPECTED_INPUT = "04457eb7f805ddb89bff1543e307844e7c6ccaa8f3593bbd18dda68cd23fa22f"


def metric(observed: np.ndarray, reference: np.ndarray) -> dict:
    delta = observed.astype(np.float64) - reference.astype(np.float64)
    reference_norm = max(float(np.linalg.norm(reference.astype(np.float64))), 1e-12)
    observed_norm = max(float(np.linalg.norm(observed.astype(np.float64))), 1e-12)
    return {
        "shape": list(observed.shape),
        "fp16_exact_count": int(np.count_nonzero(np.asarray(observed, dtype="<f2") == np.asarray(reference, dtype="<f2"))),
        "element_count": int(observed.size),
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
        "relative_l2": float(np.linalg.norm(delta) / reference_norm),
        "cosine": float(np.vdot(observed.reshape(-1).astype(np.float64), reference.reshape(-1).astype(np.float64)) /
                        (observed_norm * reference_norm)),
        "observed_sha256_fp16": hashlib.sha256(np.ascontiguousarray(observed, dtype="<f2").tobytes()).hexdigest(),
        "reference_sha256_fp16": hashlib.sha256(np.ascontiguousarray(reference, dtype="<f2").tobytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.candidate
    sys.path.insert(0, str(root / "runtime"))
    from board_runtime import BUILD_ID, M89XBoardRuntime
    from contract_runtime import pack_chain_input, quantize_t32
    from m89x1_qkv_reference_helper import deterministic_input, reference_descriptor

    started = time.monotonic()
    runtime = None
    result: dict[str, object] = {
        "gate": "M89-X1-layer0-qkv-full-output-tolerance-diagnostic",
        "status": "FAIL",
        "base_package_manifest_sha256": "c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50",
    }
    try:
        values = deterministic_input()
        runtime = M89XBoardRuntime(
            root / "overlay/m89x_t32.bit",
            Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport"),
            Path("/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport"),
            root / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
            root / "contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "staged-low-cma",
        )
        chain = next(item for item in runtime.language_contract.chains
                     if int(item["layer"]) == 0 and item["family"] == "qkv")
        if hashlib.sha256(pack_chain_input(chain, values)).hexdigest() != EXPECTED_INPUT:
            raise RuntimeError("deterministic input hash mismatch")
        observed = runtime.language_family(0, "qkv", values)
        _, codes, activation_scales = quantize_t32(values, int(chain["groups"]))
        shards = [Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport") / f"weights{i}.bin" for i in range(4)]
        reference: dict[str, np.ndarray] = {}
        for descriptor in chain["descriptors"]:
            value = reference_descriptor(shards, descriptor, chain, codes, activation_scales)
            name = descriptor["module"]
            start = int(descriptor["row_start"])
            stop = start + int(descriptor["valid_rows"])
            prior = reference.get(name)
            if prior is None:
                prior = np.zeros((32, stop), dtype="<f2")
            elif prior.shape[1] < stop:
                grown = np.zeros((32, stop), dtype="<f2")
                grown[:, :prior.shape[1]] = prior
                prior = grown
            prior[:, start:stop] = value[:, :int(descriptor["valid_rows"])]
            reference[name] = prior
        evidence = runtime.evidence()
        if evidence["build_id"] != f"0x{BUILD_ID:08x}" or evidence["host_calls"] != 1:
            raise RuntimeError(f"runtime evidence mismatch: {evidence}")
        metrics = {name: metric(observed[name], reference[name]) for name in sorted(reference)}
        result.update(status="MEASURED", evidence=evidence, metrics=metrics,
                      acceptance_note="No pass threshold is inferred; select it only after reviewing these complete measurements.")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if runtime is not None:
            runtime.close()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    print("M89X1_QKV_TOLERANCE_DIAGNOSTIC_MEASURED" if result["status"] == "MEASURED" else "M89X1_QKV_TOLERANCE_DIAGNOSTIC_FAIL")
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
