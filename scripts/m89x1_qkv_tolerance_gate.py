#!/usr/bin/env python3
"""Fail-closed numerical acceptance gate for the M89-X1 Layer-0 QKV chain.

The retained full-FP16 reference is independent of the board kernel.  The
hardware output is permitted only the measured one-FP16-LSB accumulation
difference; a global weight-layout or descriptor error is expected to violate
several limits by orders of magnitude.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


LIMITS = {
    "max_abs": 1.0 / 1000.0,
    "mean_abs": 1.0e-5,
    "rmse": 4.0e-5,
    "relative_l2": 2.0e-4,
    "cosine": 0.9999999,
    "minimum_fp16_exact_fraction": 0.94,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.candidate
    sys.path.insert(0, str(root / "runtime"))
    from m89x1_qkv_tolerance_diagnostic import main as diagnostic_main

    diagnostic_path = args.result.with_name("M89X1_QKV_TOLERANCE_MEASUREMENT.json")
    original_argv = sys.argv
    try:
        sys.argv = ["m89x1_qkv_tolerance_diagnostic.py", "--candidate", str(root), "--result", str(diagnostic_path)]
        if diagnostic_main() != 0:
            raise RuntimeError("measurement did not complete")
    except Exception as exc:
        output = {
            "gate": "M89-X1-layer0-qkv-full-output-fp16-tolerance",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "limits": LIMITS,
        }
    finally:
        sys.argv = original_argv

    if diagnostic_path.exists() and "output" not in locals():
        measurement = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        failures: dict[str, list[str]] = {}
        if measurement.get("status") != "MEASURED":
            failures["measurement"] = [str(measurement.get("error", "not measured"))]
        else:
            for name, metric in measurement["metrics"].items():
                exact_fraction = float(metric["fp16_exact_count"]) / float(metric["element_count"])
                rejected = []
                if float(metric["max_abs"]) > LIMITS["max_abs"]:
                    rejected.append("max_abs")
                if float(metric["mean_abs"]) > LIMITS["mean_abs"]:
                    rejected.append("mean_abs")
                if float(metric["rmse"]) > LIMITS["rmse"]:
                    rejected.append("rmse")
                if float(metric["relative_l2"]) > LIMITS["relative_l2"]:
                    rejected.append("relative_l2")
                if float(metric["cosine"]) < LIMITS["cosine"]:
                    rejected.append("cosine")
                if exact_fraction < LIMITS["minimum_fp16_exact_fraction"]:
                    rejected.append("minimum_fp16_exact_fraction")
                if rejected:
                    failures[name] = rejected
        output = {
            "gate": "M89-X1-layer0-qkv-full-output-fp16-tolerance",
            "status": "PASS" if not failures else "FAIL",
            "limits": LIMITS,
            "measurement": measurement,
            "failures": failures,
            "acceptance_basis": "All three full Q/K/V outputs must remain within the measured one-LSB FP16 accumulation envelope; identity hash differences are retained as diagnostics, not accepted as equality.",
        }

    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2), flush=True)
    print("M89X1_QKV_TOLERANCE_GATE_PASS" if output["status"] == "PASS" else "M89X1_QKV_TOLERANCE_GATE_FAIL")
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
