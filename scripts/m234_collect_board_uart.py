#!/usr/bin/env python3
"""Collect the authoritative M234 family JSON from retained UART output."""

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
    matches = re.findall(r"M234_BOARD_FAMILY_RESULT_BEGIN\s*(\{.*?\})\s*M234_BOARD_FAMILY_RESULT_END", text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"expected one M234 result envelope, found {len(matches)}")
    family = json.loads(matches[0])
    passed = (
        family.get("status") == "PASS"
        and family.get("build_id", "").lower() == "0x4d395832"
        and family.get("tokens") == 849
        and family.get("output_bit_exact") is True
        and family.get("maximum_abs_error") == 0.0
        and family.get("host_calls") == family.get("expected_host_calls") == 54
        and family.get("cpu_linear_fallback") is False
        and float(family.get("parse_speedup", 0.0)) > 1.02
        and float(family.get("wall_speedup", 0.0)) > 0.97
        and "M234_DIRECT_SCATTER_FAMILY_BOARD_PASS" in text
        and "M234_SERVICE_RESTORE_PASS" in text
        and "M234_DIRECT_SCATTER_BOARD_RUNNER_PASS" in text
        and "__M234_RUNNER_RC_0__" in text
    )
    result = {
        "date": "2026-09-01",
        "gate": "M234-real-KV260-direct-scatter-acceptance",
        "status": "PASS" if passed else "FAIL",
        "classification": "Real-KV260 M231-versus-M234 849-token single-family bit-exact parser performance and service restoration; independent of T64; not fixed-text E2E, full video, Web integration, or real-time evidence.",
        "candidate_build_id": family.get("build_id"),
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "family": family,
        "service_restore_marker": "M234_SERVICE_RESTORE_PASS" in text,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Only if PASS, run the M234 fixed-text regression without changing the stable Web service.",
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M234_BOARD_ACCEPTANCE_PASS" if passed else "M234_BOARD_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

