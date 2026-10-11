#!/usr/bin/env python3
"""Collect the single M246 formal result from COM3 output."""

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
items = re.findall(
    r"__M246_BOARD_RESULT_BEGIN__\s*(\{.*?\})\s*__M246_BOARD_RESULT_END__",
    text,
    re.S,
)
if len(items) != 1:
    raise RuntimeError(f"M246 formal result count mismatch: {len(items)}")
value = json.loads(items[0])
if value.get("gate") != "M246-real-KV260-constrained-knife-runtime-ready-no-frame":
    raise RuntimeError("M246 result identity mismatch")
args.result.parent.mkdir(parents=True, exist_ok=True)
partial = args.result.with_name(args.result.name + ".partial")
partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(partial, args.result)
print("M246_BOARD_RESULT_COLLECT_PASS" if value.get("status") == "PASS" else "M246_BOARD_RESULT_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)

