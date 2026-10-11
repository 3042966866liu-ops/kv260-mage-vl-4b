#!/usr/bin/env python3
"""Rebuild the exact atomic KV260 M334 JSON from the captured COM3 line."""

import argparse
import hashlib
import json
from pathlib import Path


MARKER = "M334_IMPORT_RESULT "


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uart-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--board-sha256", required=True)
    args = parser.parse_args()
    matches = [line.split(MARKER, 1)[1] for line in args.uart_log.read_text(encoding="utf-8").splitlines()
               if line.startswith(MARKER)]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one M334 result, got {len(matches)}")
    value = json.loads(matches[0])
    if value.get("gate") != "M334-KV260-real-M333-import-closure":
        raise RuntimeError("wrong board gate identity")
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != args.board_sha256:
        raise RuntimeError(f"reconstructed result differs from board: {actual}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(f"M334_BOARD_RESULT_COLLECT_PASS sha256={actual} status={value['status']}")


if __name__ == "__main__":
    main()
