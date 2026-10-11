#!/usr/bin/env python3
"""Collect the atomic M223 board result from a COM3 transcript."""

import argparse
import json
import os
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
text = args.log.read_text(encoding="utf-8", errors="replace")
matches = re.findall(r"__M223_BOARD_RESULT_BEGIN__\s*(\{.*?\})\s*__M223_BOARD_RESULT_END__", text, re.S)
if len(matches) != 1:
    raise RuntimeError(f"M223 formal result count mismatch: {len(matches)}")
value = json.loads(matches[0])
if value.get("gate") != "M223-real-KV260-corrected-realtime-control-plane":
    raise RuntimeError("M223 board result identity mismatch")
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("M223_BOARD_RESULT_COLLECT_PASS" if value.get("status") == "PASS" else "M223_BOARD_RESULT_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)

