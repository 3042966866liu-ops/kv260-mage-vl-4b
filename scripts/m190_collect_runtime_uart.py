#!/usr/bin/env python3
"""Collect the formal M190 result envelope from the UART log."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    begin = text.rfind("__M190_RUNTIME_INSTALL_RESULT_BEGIN__")
    end = text.rfind("__M190_RUNTIME_INSTALL_RESULT_END__")
    if begin < 0 or end <= begin:
        raise RuntimeError("M190 UART result envelope missing")
    payload = text[begin:].splitlines()[1]
    result = json.loads(payload)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M190_RUNTIME_UART_COLLECT_PASS" if result.get("status") == "PASS" else "M190_RUNTIME_UART_COLLECT_FAIL")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
