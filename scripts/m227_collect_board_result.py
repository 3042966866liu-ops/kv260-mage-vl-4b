#!/usr/bin/env python3
"""Collect one M227 board result from its COM3 transcript."""

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
matches = re.findall(r"__M227_BOARD_RESULT_BEGIN__\s*(\{.*?\})\s*__M227_BOARD_RESULT_END__", text, re.S)
if len(matches) != 1:
    raise RuntimeError(f"M227 formal result count mismatch: {len(matches)}")
value = json.loads(matches[0])
if value.get("gate") != "M227-real-KV260-visual-runtime-base-compatibility-control-plane":
    raise RuntimeError("M227 result identity mismatch")
args.result.parent.mkdir(parents=True, exist_ok=True)
partial = args.result.with_name(args.result.name + ".partial")
partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(partial, args.result)
print("M227_BOARD_RESULT_COLLECT_PASS" if value.get("status") == "PASS" else "M227_BOARD_RESULT_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)

