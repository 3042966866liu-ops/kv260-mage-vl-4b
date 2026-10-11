#!/usr/bin/env python3
"""Collect the read-only M188 board ML-runtime inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


BEGIN = "__M188_ML_RUNTIME_INVENTORY_BEGIN__"
END = "__M188_ML_RUNTIME_INVENTORY_END__"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(re.escape(BEGIN) + r"\s*(\{.*?\})\s*" + re.escape(END), text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"expected one M188 envelope, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("gate") != "M188-KV260-ARM64-ML-runtime-inventory" or result.get("status") != "PASS_INVENTORY":
        raise RuntimeError("M188 inventory gate/status mismatch")
    if result.get("package_manifest_sha256") != PACKAGE_SHA or result.get("board_state_changed") is not False:
        raise RuntimeError("M188 identity/state mismatch")
    result["uart_log"] = args.log.as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M188_BOARD_ML_INVENTORY_COLLECT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
