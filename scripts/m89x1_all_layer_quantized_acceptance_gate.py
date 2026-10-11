#!/usr/bin/env python3
"""Check one fixed-text M89-X1 run against the frozen quantized-CPU contract.

This implementation-conformance subgate deliberately covers every layer and
every shared Linear-family boundary.  It does *not* establish model fidelity:
the current quantized policy must pass the separate BF16 quality gate before
this result can contribute to an L5 promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


LAYERS = 36
FAMILIES = ("qkv", "attention_out", "gate_up", "mlp_down")
EXPECTED_BUILD_ID = "0x4d395831"
EXPECTED_LOGICAL_CALLS = 152
EXPECTED_SAMPLE_COUNT = 512
EXPECTED_SHAPES = {
    "qkv": [30, 2560],
    "attention_out": [30, 4096],
    "gate_up": [30, 2560],
    "mlp_down": [30, 9728],
}

# Frozen after reviewing the complete 144-boundary M89-X1 measurement.  These
# are family-wide limits, not per-layer exceptions.  Relative error and cosine
# constrain sampled direction; RMS drift independently constrains full-tensor
# energy so a sparse sample alone cannot pass the gate.
FAMILY_THRESHOLDS = {
    "qkv": {"max_relative_l2": 0.15, "min_cosine": 0.985, "max_rms_drift": 0.01},
    "attention_out": {"max_relative_l2": 0.25, "min_cosine": 0.95, "max_rms_drift": 0.05},
    "gate_up": {"max_relative_l2": 0.16, "min_cosine": 0.985, "max_rms_drift": 0.01},
    "mlp_down": {"max_relative_l2": 0.30, "min_cosine": 0.95, "max_rms_drift": 0.06},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-measurement-sha256", required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    args = parser.parse_args()

    measured_sha = sha256(args.measurement)
    measured = json.loads(args.measurement.read_text(encoding="utf-8"))
    evidence = measured.get("evidence", {})
    metrics = measured.get("family_input_metrics", {})
    required_names = {
        f"layer{layer:02d}_{family}"
        for layer in range(LAYERS)
        for family in FAMILIES
    }

    structural_checks = {
        "measurement_identity": measured_sha == args.expected_measurement_sha256,
        "measurement_status": measured.get("status") == "MEASURED",
        "gate_identity": measured.get("gate")
        == "M89-X1-fixed-text-all-layer-quantized-CPU-differential",
        "family_name_closure": set(metrics) == required_names,
        "family_count": measured.get("family_count") == len(required_names),
        "expected_family_count": measured.get("expected_family_count") == len(required_names),
        "all_family_inputs_finite": measured.get("all_family_inputs_finite") is True,
        "quantized_token_match": measured.get("quantized_token_match") is True,
        "generated_token_identity": measured.get("generated_token_id")
        == measured.get("quantized_cpu_expected_token_id"),
        "hardware_identity": measured.get("hardware_identity_pass") is True,
        "build_id": evidence.get("build_id") == EXPECTED_BUILD_ID,
        "logical_calls": evidence.get("logical_calls") == EXPECTED_LOGICAL_CALLS
        and measured.get("expected_calls") == EXPECTED_LOGICAL_CALLS,
        "physical_calls_cover_retries": isinstance(evidence.get("host_calls"), int)
        and evidence["host_calls"] >= EXPECTED_LOGICAL_CALLS,
        "logical_macro_identity": evidence.get("logical_expected_macros")
        == measured.get("expected_macros"),
        "physical_macros_cover_logical": isinstance(evidence.get("expected_macros"), int)
        and evidence["expected_macros"] >= measured.get("expected_macros", 0),
        "scale_policy": evidence.get("activation_scale_policy")
        == "adaptive-power-of-two-finite-retry-v1",
        "scale_bounds": evidence.get("minimum_activation_scale_shift") == 0
        and evidence.get("maximum_activation_scale_shift") == 6,
        "scale_attempt_closure": len(evidence.get("scale_attempts", []))
        == EXPECTED_LOGICAL_CALLS,
        "scale_count_closure": sum(
            int(value) for value in evidence.get("scale_shift_counts", {}).values()
        )
        == EXPECTED_LOGICAL_CALLS,
    }

    boundary_checks: dict[str, dict[str, object]] = {}
    aggregates = {
        family: {
            "count": 0,
            "max_relative_l2": 0.0,
            "min_cosine": 1.0,
            "max_rms_drift": 0.0,
        }
        for family in FAMILIES
    }
    for layer in range(LAYERS):
        for family in FAMILIES:
            name = f"layer{layer:02d}_{family}"
            metric = metrics.get(name, {})
            golden_rms = float(metric.get("golden_rms", 0.0))
            observed_rms = float(metric.get("observed_rms", float("inf")))
            relative_l2 = float(metric.get("sample_relative_l2", float("inf")))
            cosine = float(metric.get("sample_cosine", float("-inf")))
            rms_drift = (
                abs(observed_rms / golden_rms - 1.0)
                if golden_rms > 0.0
                else float("inf")
            )
            threshold = FAMILY_THRESHOLDS[family]
            checks = {
                "present": name in metrics,
                "shape": metric.get("shape") == EXPECTED_SHAPES[family],
                "finite": metric.get("finite") is True,
                "sample_count": metric.get("sample_count") == EXPECTED_SAMPLE_COUNT,
                "relative_l2": relative_l2 <= threshold["max_relative_l2"],
                "cosine": cosine >= threshold["min_cosine"],
                "rms_drift": rms_drift <= threshold["max_rms_drift"],
            }
            boundary_checks[name] = {
                "pass": all(checks.values()),
                "checks": checks,
                "observed": {
                    "relative_l2": relative_l2,
                    "cosine": cosine,
                    "rms_drift": rms_drift,
                },
            }
            aggregate = aggregates[family]
            aggregate["count"] += 1
            aggregate["max_relative_l2"] = max(aggregate["max_relative_l2"], relative_l2)
            aggregate["min_cosine"] = min(aggregate["min_cosine"], cosine)
            aggregate["max_rms_drift"] = max(aggregate["max_rms_drift"], rms_drift)

    failed_boundaries = [
        name for name, check in boundary_checks.items() if not check["pass"]
    ]
    passed = all(structural_checks.values()) and not failed_boundaries
    result = {
        "date": "2026-08-31",
        "gate": "M89-X1-fixed-text-all-36-layer-quantized-CPU-conformance",
        "status": "PASS" if passed else "FAIL",
        "candidate_package_manifest_sha256": args.expected_package_manifest_sha256,
        "measurement_path": args.measurement.as_posix(),
        "measurement_sha256": measured_sha,
        "threshold_policy": "frozen-global-family-thresholds-v1",
        "family_thresholds": FAMILY_THRESHOLDS,
        "structural_checks": structural_checks,
        "family_aggregates": aggregates,
        "failed_boundary_count": len(failed_boundaries),
        "failed_boundaries": failed_boundaries,
        "boundary_checks": boundary_checks,
        "generated_token_id": measured.get("generated_token_id"),
        "quantized_cpu_expected_token_id": measured.get("quantized_cpu_expected_token_id"),
        "official_bf16_token_id": measured.get("official_bf16_token_id"),
        "hardware_evidence": evidence,
        "timing": measured.get("timing"),
        "classification": (
            "fixed-text FPGA-vs-same-quantized-software implementation-conformance subgate only: "
            "one frozen 30-token prompt, all 36 language layers, all 144 shared family boundaries, "
            "and LM head on FPGA. It is not an L5 model-fidelity PASS and cannot unlock arbitrary "
            "prompt, video, Web, stability, or performance promotion while M102 remains FAIL."
        ),
        "model_fidelity_prerequisite": {
            "evidence": "deployment/mage_vl4b/M102_QUANTIZATION_ACCURACY_AUDIT.json",
            "required_status_before_l5": "PASS",
            "current_status": "FAIL_NOT_WITHIN_REASONABLE_MODEL_FIDELITY",
        },
        "next_gate": (
            "run sensitivity-guided W2-to-W4 software quality scans against BF16, select a bounded "
            "Pareto policy, then regenerate the same-quantized reference before any board rerun"
            if passed
            else "debug the first failed shared-family boundary and rerun this same conformance subgate"
        ),
    }
    atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    print(
        "M89X1_ALL_LAYER_QUANTIZED_ACCEPTANCE_PASS"
        if passed
        else "M89X1_ALL_LAYER_QUANTIZED_ACCEPTANCE_FAIL",
        flush=True,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
