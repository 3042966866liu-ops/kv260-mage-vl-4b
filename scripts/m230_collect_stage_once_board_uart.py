#!/usr/bin/env python3
"""Collect the compact M230 acceptance result from one COM3 transcript."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--result", type=Path, required=True)
parser.add_argument("--expected-delta-manifest-sha256", required=True)
args = parser.parse_args()
text = args.log.read_text(encoding="utf-8", errors="replace")
matches = re.findall(
    r"M230_BOARD_ACCEPTANCE_RESULT_BEGIN\s*(\{.*?\})\s*M230_BOARD_ACCEPTANCE_RESULT_END",
    text,
    re.S,
)
if len(matches) != 1:
    raise RuntimeError(f"M230 formal result count mismatch: {len(matches)}")
value = json.loads(matches[0])
if value.get("gate") != "M230-real-KV260-stage-once-acceptance":
    raise RuntimeError("M230 board result identity mismatch")
if value.get("delta_manifest_sha256") != args.expected_delta_manifest_sha256:
    raise RuntimeError("M230 board delta identity mismatch")
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("M230_BOARD_RESULT_COLLECT_PASS" if value.get("status") == "PASS" else "M230_BOARD_RESULT_COLLECT_FAIL")
raise SystemExit(0 if value.get("status") == "PASS" else 1)
