#!/usr/bin/env python3
"""Collect the bounded M161 network probe JSON from one COM3 log."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


BEGIN = "__M161_NETWORK_PROBE_RESULT_BEGIN__"
END = "__M161_NETWORK_PROBE_RESULT_END__"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(re.escape(BEGIN) + r"\s*(\{.*?\})\s*" + re.escape(END), text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one M161 JSON envelope, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("gate") != "M161-KV260-temporary-network-readonly-probe":
        raise RuntimeError("M161 gate identity mismatch")
    if result.get("status") != "PASS" or not result.get("linked_interfaces"):
        raise RuntimeError("M161 board Ethernet link is not PASS")
    if result.get("state_changed") is not False:
        raise RuntimeError("M161 probe claims a state change")
    result["uart_log"] = str(args.log).replace("\\", "/")
    result["uart_log_sha256"] = sha256(args.log)
    result["evidence_level"] = "read-only board network discovery; not weight transfer or FPGA execution"
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M161_KV260_NETWORK_PROBE_COLLECT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
