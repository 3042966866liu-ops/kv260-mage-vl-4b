#!/usr/bin/env python3
"""Collect M294's final envelope and independent M254 restoration proof."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


EXPECTED_PLAN_SHA256 = "424dd30c09e57ce6982a3e2bb08835641dabc38e63bc66d33284a57f6eb07162"


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def incomplete_result(text: str, package_hash: str, error: str) -> dict:
    markers = re.findall(
        r"M294_MEASUREMENT_(\d+)_([A-Z]+) tokens=(\d+) calls=(\d+)/(\d+) prefill_ms=([0-9.]+)",
        text,
    )
    return {
        "date": "2026-09-02",
        "gate": "M294-real-KV260-counterbalanced-T32-boundary-pilot",
        "status": "FAIL_INCOMPLETE_UART_EVIDENCE",
        "classification": (
            "Host-side fail-closed collection result only. It cannot prove a complete board pilot, "
            "semantic accuracy, speedup, power, Web promotion or real-time behavior."
        ),
        "package_manifest_sha256": package_hash,
        "plan_sha256": EXPECTED_PLAN_SHA256,
        "completed_measurement_markers": len(markers),
        "measurement_markers": [
            {
                "measurement_index": int(index),
                "marker_status": status,
                "prompt_tokens": int(tokens),
                "observed_logical_fpga_calls": int(observed),
                "expected_logical_fpga_calls": int(expected),
                "prefill_ms": float(elapsed),
            }
            for index, status, tokens, observed, expected, elapsed in markers
        ],
        "host_collection_error": error,
        "board_result_envelope_present": False,
        "active_service_restoration_proved": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    envelopes = re.findall(
        r"__M294_BOARD_RESULT_BEGIN__\s*(.*?)\s*__M294_BOARD_RESULT_END__",
        text,
        flags=re.DOTALL,
    )
    if len(envelopes) != 1:
        result = incomplete_result(
            text,
            args.package_manifest_sha256,
            f"M294 result envelope count {len(envelopes)}",
        )
        atomic_json(args.result, result)
        print(
            f"M294_FORMAL_RESULT_FAIL incomplete_markers={result['completed_measurement_markers']} "
            "restore_proved=false"
        )
        return 1

    result = json.loads(envelopes[0])
    errors = []
    if result.get("gate") != "M294-real-KV260-counterbalanced-T32-boundary-pilot":
        errors.append("gate identity mismatch")
    if result.get("package_manifest_sha256") != args.package_manifest_sha256:
        errors.append("package hash mismatch")
    if result.get("plan_sha256") != EXPECTED_PLAN_SHA256:
        errors.append("plan hash mismatch")
    restore_codes = [int(value) for value in re.findall(r"__M294_RESTORE_RC_(\d+)__", text)]
    gate_codes = [int(value) for value in re.findall(r"__M294_GATE_RC_(\d+)__", text)]
    if not restore_codes or restore_codes[-1] != 0:
        errors.append(f"stable restoration not proved {restore_codes}")
    if not gate_codes or gate_codes[-1] != 0:
        errors.append(f"gate return code not zero {gate_codes}")
    if result.get("status") != "PASS_COUNTERBALANCED_PILOT":
        errors.append(f"board status not PASS {result.get('status')}")
    if result.get("completed_measurements") != 27 or len(result.get("records", [])) != 27:
        errors.append("measurement closure mismatch")
    result["host_collection"] = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "last_gate_rc": gate_codes[-1] if gate_codes else None,
        "last_restore_rc": restore_codes[-1] if restore_codes else None,
        "active_service_restoration_proved": bool(restore_codes and restore_codes[-1] == 0),
    }
    atomic_json(args.result, result)
    passed = not errors
    print(
        f"M294_FORMAL_RESULT_{'PASS' if passed else 'FAIL'} "
        f"measurements={result.get('completed_measurements')} restore_rc="
        f"{restore_codes[-1] if restore_codes else 'missing'}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
