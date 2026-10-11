#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path


def find(text: str) -> dict:
    end = max(text.rfind("M120_FIXED_TEXT_E2E_PASS"), text.rfind("M120_FIXED_TEXT_E2E_FAIL"))
    if end < 0:
        raise RuntimeError("M179 fixed-text marker missing")
    decoder = json.JSONDecoder()
    values = []
    for index, character in enumerate(text[:end]):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:end])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("gate") == "M120-fixed-text-E2E":
            values.append(value)
    if len(values) != 1:
        raise RuntimeError(f"M179 expected one result, observed={len(values)}")
    return values[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--layer0", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    value = find(args.log.read_text(encoding="utf-8", errors="replace"))
    evidence = value.get("evidence", {})
    if value.get("status") not in {"PASS", "FAIL"} or value.get("cpu_linear_fallback") is not False:
        raise RuntimeError("M179 result identity mismatch")
    if value.get("status") == "PASS":
        accepted = (
            value.get("reference_match") is True
            and value.get("fpga_execution_proved") is True
            and value.get("expected_calls") == 162
            and evidence.get("logical_calls") == 162
            and str(evidence.get("build_id", "")).lower() == "0x4d395832"
        )
        if not accepted:
            raise RuntimeError("M179 PASS lacks fixed-text FPGA proof")
    value.update({
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
        "m167_formal_result": args.layer0.as_posix(),
        "m167_formal_result_sha256": hashlib.sha256(args.layer0.read_bytes()).hexdigest(),
        "m176_stage_result": args.stage.as_posix(),
        "m176_stage_result_sha256": hashlib.sha256(args.stage.read_bytes()).hexdigest(),
        "uart_log": args.log.as_posix(),
        "uart_log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest(),
        "evidence_level": "L5 fixed-reference M120 text E2E; not arbitrary prompt/Web",
    })
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(value, indent=2))
    print("M179_M120_FIXED_TEXT_COLLECT_PASS" if value["status"] == "PASS" else "M179_M120_FIXED_TEXT_COLLECT_FAIL")
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
