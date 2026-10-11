#!/usr/bin/env python3
"""Collect one authoritative M202 result from a COM3 UART log."""

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    begin = "__M202_FIXED_VIDEO_E2E_RESULT_BEGIN__"
    end = "__M202_FIXED_VIDEO_E2E_RESULT_END__"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError("M202 UART result envelope cardinality mismatch")
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    value = json.loads(payload)
    if value.get("gate") != "M202-M200-fixed-four-frame-video-language-E2E":
        raise RuntimeError("M202 UART result identity mismatch")
    if value.get("status") == "PASS":
        proof = value.get("fpga_proof", {})
        if (value.get("prompt_tokens") != 849 or value.get("generated_tokens") != 1 or
                str(proof.get("build_id", "")).lower() != "0x4d395832" or
                proof.get("pl_logical_chain_calls") != 4166 or
                proof.get("expected_pl_logical_chain_calls") != 4166 or
                proof.get("language_cpu_linear_fallback") is not False or
                "M202_FIXED_VIDEO_E2E_RUNNER_PASS" not in text or
                "__M202_FIXED_VIDEO_RUNNER_RC_0__" not in text):
            raise RuntimeError("M202 PASS lacks complete FPGA proof")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M202_FIXED_VIDEO_UART_COLLECT_PASS" if value.get("status") == "PASS" else "M202_FIXED_VIDEO_UART_COLLECT_FAIL")
    return 0 if value.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
