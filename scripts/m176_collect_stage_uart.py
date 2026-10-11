#!/usr/bin/env python3
"""Collect a marked M176 board-stage result from a retained UART log."""

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    begin, end = "__M176_STAGE_RESULT_BEGIN__", "__M176_STAGE_RESULT_END__"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError("M176 expected one marked result")
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    value = json.loads(payload)
    if value.get("gate") != "M176-M120-LMHead-optional-layer-board-stage" or value.get("status") not in {"PASS", "FAIL"}:
        raise RuntimeError("M176 result identity mismatch")
    value["uart_log"] = args.log.as_posix()
    value["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    args.result.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, indent=2))
    print("M176_STAGE_COLLECT_PASS" if value["status"] == "PASS" else "M176_STAGE_COLLECT_FAIL")
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
