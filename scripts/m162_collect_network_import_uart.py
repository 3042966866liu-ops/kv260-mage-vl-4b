#!/usr/bin/env python3
"""Collect the final bounded M162 import result from one COM3 log."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


BEGIN = "__M162_NETWORK_IMPORT_RESULT_BEGIN__"
END = "__M162_NETWORK_IMPORT_RESULT_END__"


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
        raise RuntimeError(f"expected one M162 result envelope, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("gate") != "M162-M120-direct-Ethernet-board-import":
        raise RuntimeError("M162 result gate mismatch")
    if result.get("status") != "PASS" or int(result.get("payload_bytes", -1)) != 2_035_472_384:
        raise RuntimeError(f"M162 import is not PASS: {result.get('error')}")
    if result.get("boot_dtb_cma_partitions_services_changed") is not False or result.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M162 stable-state evidence mismatch")
    result["uart_log"] = str(args.log).replace("\\", "/")
    result["uart_log_sha256"] = sha256(args.log)
    result["evidence_level"] = "hash-verified complete M120 weight transfer; not Layer-0 or E2E"
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M162_NETWORK_IMPORT_COLLECT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
