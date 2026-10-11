#!/usr/bin/env python3
"""Collect the authoritative M231 family JSON from retained UART output."""

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
        r"M231_BOARD_FAMILY_RESULT_BEGIN\s*(\{.*?\})\s*M231_BOARD_FAMILY_RESULT_END",
        text,
        flags=re.S,
    )
    if len(matches) != 1:
        raise RuntimeError(f"expected one M231 result envelope, found {len(matches)}")
    family = json.loads(matches[0])
    passed = (
        family.get("status") == "PASS"
        and family.get("build_id", "").lower() == "0x4d395832"
        and family.get("tokens") == 849
        and family.get("output_bit_exact") is True
        and family.get("maximum_abs_error") == 0.0
        and family.get("host_calls") == family.get("expected_host_calls") == 54
        and family.get("cpu_linear_fallback") is False
        and "M231_PARSE_REUSE_FAMILY_BOARD_PASS" in text
        and "M231_SERVICE_RESTORE_PASS" in text
        and "M231_PARSE_REUSE_BOARD_RUNNER_PASS" in text
        and "__M231_RUNNER_RC_0__" in text
    )
    result = {
        "date": "2026-09-01",
        "gate": "M231-real-KV260-parse-reuse-acceptance",
        "status": "PASS" if passed else "FAIL",
        "classification": "Real-KV260 M230-versus-M231 849-token single-family bit-exact performance and service restoration; not fixed-text E2E, full video, Web integration, or real-time evidence.",
        "candidate_build_id": family.get("build_id"),
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "family": family,
        "service_restore_marker": "M231_SERVICE_RESTORE_PASS" in text,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "If PASS, integrate the parser-only runtime into fixed-text E2E; only then make a hash-locked Web runtime delta.",
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M231_BOARD_ACCEPTANCE_PASS" if passed else "M231_BOARD_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
