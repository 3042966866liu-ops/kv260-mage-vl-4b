#!/usr/bin/env python3
"""Apply the predeclared strict M89-X1 Layer-0 numerical thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


THRESHOLDS = {
    "max_abs": 0.001,
    "mean_abs": 1.0e-5,
    "rmse": 4.0e-5,
    "relative_l2": 2.0e-4,
    "cosine": 0.9999999,
    "fp16_exact_fraction": 0.94,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    measured = json.loads(args.measurement.read_text(encoding="utf-8"))
    checks = {}
    if measured.get("status") != "MEASURED":
        checks["measurement_status"] = False
    for name, metric in measured.get("local_metrics", {}).items():
        elements = int(metric.get("element_count", 0))
        exact_fraction = float(metric.get("fp16_exact_count", 0)) / max(elements, 1)
        checks[name] = {
            "finite": metric.get("finite") is True,
            "max_abs": float(metric.get("max_abs", float("inf"))) <= THRESHOLDS["max_abs"],
            "mean_abs": float(metric.get("mean_abs", float("inf"))) <= THRESHOLDS["mean_abs"],
            "rmse": float(metric.get("rmse", float("inf"))) <= THRESHOLDS["rmse"],
            "relative_l2": float(metric.get("relative_l2", float("inf"))) <= THRESHOLDS["relative_l2"],
            "cosine": float(metric.get("cosine", float("-inf"))) >= THRESHOLDS["cosine"],
            "fp16_exact_fraction": exact_fraction >= THRESHOLDS["fp16_exact_fraction"],
        }
    required = {
        "model.language_model.layers.0.self_attn.q_proj",
        "model.language_model.layers.0.self_attn.k_proj",
        "model.language_model.layers.0.self_attn.v_proj",
        "model.language_model.layers.0.self_attn.o_proj",
        "model.language_model.layers.0.mlp.gate_proj",
        "model.language_model.layers.0.mlp.up_proj",
        "model.language_model.layers.0.mlp.down_proj",
        "layer0.output",
    }
    checks["required_local_outputs"] = required - {"layer0.output"} <= set(measured.get("local_metrics", {}))
    propagated = measured.get("metrics", {})
    checks["required_propagated_outputs"] = required <= set(propagated)
    checks["propagated_outputs_finite"] = all(
        metric.get("finite") is True for metric in propagated.values())
    checks["hs64_input_identity"] = measured.get("scaled_input_sha256") == "58dc6b0b43975d39027c32263325689590d74c3de03c2f04e5f1759b3c4c392e"
    passed = all(
        all(item.values()) if isinstance(item, dict) else bool(item)
        for item in checks.values()
    )
    result = {
        "date": "2026-08-31",
        "gate": "M89-X1-HS64-complete-layer0-numerical-acceptance",
        "status": "PASS" if passed else "FAIL",
        "base_package_manifest_sha256": measured.get("base_package_manifest_sha256"),
        "candidate_build_id": measured.get("evidence", {}).get("build_id"),
        "host_scale_shift": measured.get("evidence", {}).get("activation_scale_shift"),
        "host_scale_factor": measured.get("evidence", {}).get("activation_scale_factor"),
        "local_operator_thresholds": THRESHOLDS,
        "checks": checks,
        "measurement": measured,
        "acceptance_scope": ("All four FPGA Linear families must pass the unchanged strict same-input operator "
                             "thresholds. Propagated Layer-0 error is retained explicitly and is not misclassified "
                             "as current-operator arithmetic error; fixed-text E2E remains the next gate."),
        "next_gate": "fixed-text E2E only" if passed else "debug and rerun complete Layer-0 only",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.result)
    print(json.dumps(result, indent=2), flush=True)
    print("M89X1_HS64_LAYER0_ACCEPTANCE_PASS" if passed else "M89X1_HS64_LAYER0_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
