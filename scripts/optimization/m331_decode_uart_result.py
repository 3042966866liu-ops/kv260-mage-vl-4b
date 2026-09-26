#!/usr/bin/env python3
"""Extract one hash-locked JSON payload from a COM3 base64 capture."""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite prior result")
    captured = args.capture.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"\n([A-Za-z0-9+/=]{100,})__M75C_UART_RC_0__", captured)
    if len(matches) != 1:
        raise RuntimeError(f"expected one completed base64 result, got {len(matches)}")
    payload = base64.b64decode(matches[0], validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != args.sha256.lower():
        raise RuntimeError(f"board result SHA-256 mismatch: {digest}")
    value = json.loads(payload)
    if value.get("status") != "PASS_PAIRED_FIXTURE_AB":
        raise RuntimeError(f"board result is not PASS: {value.get('status')}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + f".partial-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, args.output)
    print(f"M331_BOARD_RESULT_PULL_PASS sha256={digest} bytes={len(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
