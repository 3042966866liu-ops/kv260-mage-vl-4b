#!/usr/bin/env python3
"""Decode a complete COM3 base64 result and compare with board SHA-256."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uart-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--board-sha256", required=True)
    parser.add_argument("--raw", action="store_true", help="collect a non-JSON service log")
    args = parser.parse_args()
    lines = args.uart_log.read_text(encoding="utf-8", errors="replace").splitlines()
    command = next(i for i, line in enumerate(lines) if "base64 /home/ubuntu/" in line)
    marker = next(i for i in range(command + 1, len(lines))
                  if re.search(r"__[A-Z0-9_]+_RC_0__", lines[i]))
    chunks = [line.strip() for line in lines[command + 1:marker]
              if re.fullmatch(r"[A-Za-z0-9+/=]{4,76}", line.strip())]
    if not chunks:
        raise RuntimeError("no base64 payload in COM3 log")
    raw = base64.b64decode("".join(chunks), validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.board_sha256.lower():
        raise RuntimeError(f"board result mismatch: {digest}")
    value = None
    if not args.raw:
        value = json.loads(raw)
        if value.get("gate") != "M335-real-Web-manual-4B-FPGA-SSE":
            raise RuntimeError("wrong gate identity")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_bytes() != raw:
        raise FileExistsError("refusing to replace different M335 result")
    args.output.write_bytes(raw)
    print(json.dumps({"sha256": digest, "bytes": len(raw),
                      "status": None if value is None else value.get("status"),
                      "first_error": None if value is None else value.get("first_error"),
                      "checks": None if value is None else value.get("checks")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
