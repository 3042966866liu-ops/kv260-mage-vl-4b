#!/usr/bin/env python3
"""Collect the real M120 Layer-0 acceptance object from one COM3 log."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


PASS_MARKER = "M144_M120_LAYER0_ACCEPTANCE_PASS"
FAIL_MARKER = "M144_M120_LAYER0_ACCEPTANCE_FAIL"


def find_acceptance(text: str) -> dict:
    limit = max(text.rfind(PASS_MARKER), text.rfind(FAIL_MARKER))
    if limit < 0:
        raise RuntimeError("M164 Layer-0 acceptance marker missing")
    decoder = json.JSONDecoder()
    accepted = []
    for index, character in enumerate(text[:limit]):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:limit])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("gate") == "M144-M120-complete-layer0-boundary-acceptance":
            accepted.append(value)
    if len(accepted) != 1:
        raise RuntimeError(f"M164 expected one Layer-0 acceptance, observed={len(accepted)}")
    return accepted[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = find_acceptance(text)
    measurement = result.get("measurement", {})
    if result.get("status") not in {"PASS", "FAIL"} or measurement.get("build_id") != "0x4d395832":
        raise RuntimeError("M164 Layer-0 acceptance identity/status mismatch")
    if measurement.get("fpga_execution_proved") is not True or int(measurement.get("expected_logical_calls", -1)) != 5:
        raise RuntimeError("M164 Layer-0 FPGA proof mismatch")
    if result.get("thresholds_frozen_before_board_measurement") is not True:
        raise RuntimeError("M164 Layer-0 threshold provenance mismatch")
    result["uart_log"] = args.log.as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    result["evidence_level"] = "L4.3 real complete Layer-0 numerical gate; not fixed-text E2E"
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M164_M120_LAYER0_COLLECT_PASS" if result.get("status") == "PASS" else "M164_M120_LAYER0_COLLECT_FAIL")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
