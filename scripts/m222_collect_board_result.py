#!/usr/bin/env python3
"""Collect the M222 ARM64 decoder UART result envelope."""

import argparse
import json
import os
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
text = args.log.read_text(encoding="utf-8", errors="replace")
begin = "__M222_BOARD_RESULT_BEGIN__"
end = "__M222_BOARD_RESULT_END__"
if text.count(begin) != 1 or text.count(end) != 1:
    raise RuntimeError("M222 UART result envelope mismatch")
value = json.loads(text.split(begin, 1)[1].split(end, 1)[0].strip())
if value.get("gate") != "M222-ARM64-vectorized-visual-W4-decoder":
    raise RuntimeError("M222 board result identity mismatch")
if value.get("status") == "PASS" and (
    "M222_ARM64_DECODER_RUNNER_PASS" not in text
    or "__M222_RUNNER_RC_0__" not in text
):
    raise RuntimeError("M222 runner PASS proof missing")
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("M222_BOARD_UART_COLLECT_PASS" if value.get("status") == "PASS" else "M222_BOARD_UART_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)

