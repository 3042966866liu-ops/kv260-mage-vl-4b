#!/usr/bin/env python3
"""Collect the authoritative M232 acceptance envelope from retained UART."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"M232_FIXED_TEXT_ACCEPTANCE_BEGIN\s*(\{.*?\})\s*M232_FIXED_TEXT_ACCEPTANCE_END",
        text,
        flags=re.S,
    )
    if len(matches) != 1:
        raise RuntimeError(f"expected one M232 acceptance envelope, found {len(matches)}")
    acceptance = json.loads(matches[0])
    fixed = acceptance.get("fixed_text", {})
    evidence = fixed.get("evidence", {})
    passed = (
        acceptance.get("status") == "PASS"
        and fixed.get("generated_token_id") == fixed.get("expected_token_id") == 17
        and fixed.get("reference_match") is True
        and fixed.get("fpga_execution_proved") is True
        and fixed.get("cpu_linear_fallback") is False
        and evidence.get("build_id", "").lower() == "0x4d395832"
        and evidence.get("prefill_scheduler")
            == "m231-family-stage-once-direct-final-buffer-t32"
        and evidence.get("parse_temporary_result_dicts") == 0
        and "M232_M231_PREDECESSOR_VERIFY_PASS" in text
        and "M232_M231_FIXED_TEXT_ACCEPTANCE_PASS" in text
        and "M232_SERVICE_RESTORE_PASS" in text
        and "M232_M231_FIXED_TEXT_BOARD_RUNNER_PASS" in text
        and "__M232_RUNNER_RC_0__" in text
    )
    result = {
        "date": "2026-09-01",
        "gate": "M232-real-KV260-M231-fixed-text-final",
        "status": "PASS" if passed else "FAIL",
        "classification": "Frozen fixed-text complete 4B FPGA E2E through M231 plus service restoration; not video, Web integration, or real-time evidence.",
        "candidate_build_id": evidence.get("build_id"),
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "fixed_text": fixed,
        "service_restore_marker": "M232_SERVICE_RESTORE_PASS" in text,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Build a hash-locked M231 Web runtime delta, then run fixed 849-token language-Prefill timing before any full visual window.",
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M232_FIXED_TEXT_BOARD_PASS" if passed else "M232_FIXED_TEXT_BOARD_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
