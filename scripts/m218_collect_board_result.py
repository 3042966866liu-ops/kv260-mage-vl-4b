#!/usr/bin/env python3
"""Collect the exact M218 UART result envelope atomically."""

import argparse
import json
import os
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
text = args.log.read_text(encoding="utf-8", errors="replace")
begin = "__M218_BOARD_RESULT_BEGIN__"
end = "__M218_BOARD_RESULT_END__"
if text.count(begin) != 1 or text.count(end) != 1:
    raise RuntimeError("M218 UART result envelope mismatch")
value = json.loads(text.split(begin, 1)[1].split(end, 1)[0].strip())
if value.get("gate") != "M218-real-KV260-dual-source-service-control-plane":
    raise RuntimeError("M218 board result identity mismatch")
if value.get("status") == "PASS" and (
    "M218_DUAL_SOURCE_SERVICE_BOARD_START_PASS" not in text
    or "__M218_LIVE_RUNNER_RC_0__" not in text
):
    raise RuntimeError("M218 runner PASS proof missing")
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("M218_BOARD_UART_COLLECT_PASS" if value.get("status") == "PASS" else "M218_BOARD_UART_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)
