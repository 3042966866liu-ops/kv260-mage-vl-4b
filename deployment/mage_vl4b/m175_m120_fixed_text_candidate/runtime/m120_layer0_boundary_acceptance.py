#!/usr/bin/env python3
"""Apply predeclared M120 Layer-0 boundary thresholds without changing them post-measurement."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


THRESHOLDS = {
    "relative_l2": 0.05,
    "cosine": 0.998,
}
REQUIRED = {
    "layer00_q_input",
    "layer00_kv_input",
    "layer00_attention_out_input",
    "layer00_gate_up_input",
    "layer00_mlp_down_input",
    "layer01_q_input",
    "layer01_kv_input",
}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    measurement = json.loads(args.measurement.read_text(encoding="utf-8"))
    metrics = measurement.get("metrics", {})
    checks = {
        "measurement_status": measurement.get("status") == "MEASURED",
        "build_id": measurement.get("build_id") == "0x4d395832",
        "fpga_execution_proved": measurement.get("fpga_execution_proved") is True,
        "five_logical_calls": measurement.get("expected_logical_calls") == 5,
        "required_boundaries": set(metrics) == REQUIRED,
        "all_boundaries_finite": measurement.get("all_boundaries_finite") is True,
    }
    boundary_checks = {
        name: {
            "finite": metric.get("finite") is True,
            "relative_l2": float(metric.get("relative_l2", float("inf"))) <= THRESHOLDS["relative_l2"],
            "cosine": float(metric.get("cosine", float("-inf"))) >= THRESHOLDS["cosine"],
        }
        for name, metric in metrics.items()
    }
    passed = all(checks.values()) and all(all(item.values()) for item in boundary_checks.values())
    result = {
        "date": "2026-09-01",
        "gate": "M144-M120-complete-layer0-boundary-acceptance",
        "status": "PASS" if passed else "FAIL",
        "classification": "real-board complete Layer-0 numerical gate; fixed-text remains a separate next level",
        "thresholds_frozen_before_board_measurement": True,
        "thresholds": THRESHOLDS,
        "checks": checks,
        "boundary_checks": boundary_checks,
        "measurement": measurement,
        "next_gate": "fixed 30-token/one-token M120 E2E" if passed else "debug and rerun complete Layer-0 only",
    }
    atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M144_M120_LAYER0_ACCEPTANCE_PASS" if passed else "M144_M120_LAYER0_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
