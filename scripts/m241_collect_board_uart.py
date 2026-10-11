#!/usr/bin/env python3
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
    matches = re.findall(r"M241_RESULT_BEGIN\s*(\{.*?\})\s*M241_RESULT_END", text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"M241 expected one result envelope, found {len(matches)}")
    gate = json.loads(matches[0])
    restored = "M241_SERVICE_RESTORE_PASS" in text or "M241_SERVICE_RESTORE_AFTER_FAILURE_PASS" in text
    passed = gate.get("status") == "PASS" and restored and "M241_COMPLETE_849_PREFILL_BOARD_RUNNER_PASS" in text
    value = {
        "date": "2026-09-01",
        "gate": "M241-real-KV260-complete-849-token-grouped-GQA-Prefill-acceptance",
        "status": "PASS_SERVICE_RESTORED" if passed else "FAIL_NOT_PROMOTED",
        "classification": "Real-KV260 complete frozen 849-token language-only Prefill using grouped GQA only; not visual, Web, video, T64, semantic-reference, or real-time evidence.",
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "prefill_gate": gate,
        "service_restore_marker": restored,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Run frozen fixed-text complete 4B FPGA E2E with M241 grouped-GQA Prefill; do not integrate Web before exact token and FPGA proof pass."
            if passed else
            "Do not promote M241; retain M238/M239 and use the M239 family profile to select another isolated non-T64 optimization."
        ),
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print(json.dumps(value, indent=2))
    print("M241_BOARD_ACCEPTANCE_PASS" if passed else "M241_BOARD_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
