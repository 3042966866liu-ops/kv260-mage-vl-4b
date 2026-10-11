#!/usr/bin/env python3
"""Fail-closed acceptance wrapper for the M89-X1 HS64 fixed-text E2E result."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


EXPECTED_BUILD_ID = "0x4d395831"
EXPECTED_CALLS = 152
EXPECTED_SCALE_POLICY = "adaptive-power-of-two-finite-retry-v1"


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    args = parser.parse_args()
    environment = json.loads(args.environment.read_text(encoding="utf-8"))
    measured = json.loads(args.measurement.read_text(encoding="utf-8"))
    evidence = measured.get("evidence", {})
    checks = {
        "environment_pass": environment.get("status") == "PASS",
        "environment_manifest_identity": (
            environment.get("package_manifest_sha256")
            == args.expected_package_manifest_sha256
        ),
        "measurement_pass": measured.get("status") == "PASS",
        "gate_identity": measured.get("gate") == "M89-X-fixed-text-E2E",
        "reference_match": measured.get("reference_match") is True,
        "generated_token_match": (
            measured.get("generated_token_id") == measured.get("expected_token_id")
        ),
        "fpga_execution_proved": measured.get("fpga_execution_proved") is True,
        "cpu_linear_fallback_disabled": measured.get("cpu_linear_fallback") is False,
        "build_id": evidence.get("build_id") == EXPECTED_BUILD_ID,
        "logical_calls": (
            evidence.get("logical_calls") == EXPECTED_CALLS
            and measured.get("expected_calls") == EXPECTED_CALLS
        ),
        "physical_calls_cover_logical_calls": (
            isinstance(evidence.get("host_calls"), int)
            and evidence.get("host_calls") >= EXPECTED_CALLS
        ),
        "logical_macro_count": (
            isinstance(evidence.get("logical_expected_macros"), int)
            and evidence.get("logical_expected_macros") == measured.get("expected_macros")
        ),
        "physical_macros_cover_logical_macros": (
            isinstance(evidence.get("expected_macros"), int)
            and evidence.get("expected_macros") >= measured.get("expected_macros", 0)
        ),
        "activation_scale_policy": evidence.get("activation_scale_policy") == EXPECTED_SCALE_POLICY,
        "activation_scale_bounds": (
            evidence.get("minimum_activation_scale_shift") == 0
            and evidence.get("maximum_activation_scale_shift") == 6
        ),
        "scale_accounting": (
            sum(int(value) for value in evidence.get("scale_shift_counts", {}).values())
            == EXPECTED_CALLS
            and len(evidence.get("scale_attempts", [])) == EXPECTED_CALLS
        ),
    }
    passed = all(checks.values())
    result = {
        "date": "2026-08-31",
        "gate": "M89-X1-HS64-fixed-text-E2E-acceptance",
        "status": "PASS" if passed else "FAIL",
        "base_package_manifest_sha256": args.expected_package_manifest_sha256,
        "checks": checks,
        "measurement": measured,
        "classification": (
            "One frozen 30-token prompt and one generated token through all 36 language layers "
            "and LM head on FPGA; not arbitrary-prompt, video, Web, stability, or performance evidence."
        ),
        "next_gate": (
            "arbitrary-prompt/text service preparation, then clean M90 video rebase"
            if passed else "debug and rerun fixed-text E2E only"
        ),
    }
    atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M89X1_HS64_FIXED_TEXT_E2E_ACCEPTANCE_PASS" if passed
          else "M89X1_HS64_FIXED_TEXT_E2E_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
