#!/usr/bin/env python3
"""Collect one corrected M120 Layer-0 acceptance object from COM3."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def find_acceptance(text: str) -> dict:
    limit = max(text.rfind("M144_M120_LAYER0_ACCEPTANCE_PASS"), text.rfind("M144_M120_LAYER0_ACCEPTANCE_FAIL"))
    if limit < 0:
        raise RuntimeError("M167 Layer-0 acceptance marker missing")
    decoder = json.JSONDecoder()
    values = []
    for index, character in enumerate(text[:limit]):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:limit])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("gate") == "M144-M120-complete-layer0-boundary-acceptance":
            values.append(value)
    if len(values) != 1:
        raise RuntimeError(f"M167 expected one Layer-0 acceptance, observed={len(values)}")
    return values[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--stage-result", type=Path, required=True)
    args = parser.parse_args()
    stage = json.loads(args.stage_result.read_text(encoding="utf-8"))
    if stage.get("status") != "PASS" or stage.get("package_manifest_sha256") != "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97":
        raise RuntimeError("M167 corrected stage predecessor mismatch")
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = find_acceptance(text)
    measurement = result.get("measurement", {})
    if result.get("status") not in {"PASS", "FAIL"} or measurement.get("build_id") != "0x4d395832":
        raise RuntimeError("M167 Layer-0 identity/status mismatch")
    if measurement.get("fpga_execution_proved") is not True or int(measurement.get("expected_logical_calls", -1)) != 5:
        raise RuntimeError("M167 Layer-0 FPGA proof mismatch")
    if result.get("thresholds_frozen_before_board_measurement") is not True:
        raise RuntimeError("M167 threshold provenance mismatch")
    board_acceptance_bytes = (json.dumps(result, indent=2) + "\n").encode("utf-8")
    board_acceptance_sha256 = hashlib.sha256(board_acceptance_bytes).hexdigest()
    result.update({
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": stage["package_manifest_sha256"],
        "m166_stage_result": args.stage_result.as_posix(),
        "m166_stage_result_sha256": hashlib.sha256(args.stage_result.read_bytes()).hexdigest(),
        "board_acceptance_sha256": board_acceptance_sha256,
        "uart_log": args.log.as_posix(),
        "uart_log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest(),
        "evidence_level": "L4.3 real corrected complete Layer-0 numerical gate; not fixed-text E2E",
    })
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M167_M120_CORRECTED_LAYER0_COLLECT_PASS" if result["status"] == "PASS" else "M167_M120_CORRECTED_LAYER0_COLLECT_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
