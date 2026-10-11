#!/usr/bin/env python3
"""Collect the passing M166 board-stage result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"__M166_STAGE_RESULT_BEGIN__\s*(\{.*?\})\s*__M166_STAGE_RESULT_END__", text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"M166 expected one result, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("status") not in {"PASS", "FAIL"}:
        raise RuntimeError(f"M166 stage status is invalid: {result.get('status')}")
    if result.get("status") == "PASS" and result.get("package_manifest_sha256") != "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97":
        raise RuntimeError("M166 passing stage package identity mismatch")
    result["uart_log"] = args.log.as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M166_CORRECTED_STAGE_COLLECT_PASS" if result.get("status") == "PASS" else "M166_CORRECTED_STAGE_COLLECT_FAIL")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
