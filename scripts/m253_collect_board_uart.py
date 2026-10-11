#!/usr/bin/env python3
"""Collect the exact M253 board result envelope from UART."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    begin, end = "__M253_BOARD_RESULT_BEGIN__", "__M253_BOARD_RESULT_END__"
    start, finish = text.rfind(begin), text.rfind(end)
    if start < 0 or finish <= start:
        raise RuntimeError("missing M253 UART result envelope")
    lines = text[start + len(begin):finish].strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError("ambiguous M253 UART result envelope")
    measurement = json.loads(lines[0])
    status = "PASS" if measurement.get("status") == "PASS" else "FAIL"
    result = {
        "date": "2026-09-02",
        "gate": "M253-KV260-latest-only-fast-safety-stream-board",
        "status": status,
        "classification": (
            "Real KV260 A53 continuous-source pressure, latest-only scheduling and structured safety-event latency; "
            "not camera/Web or target-scene knife/action accuracy."
        ),
        "package_manifest_sha256": args.package_manifest_sha256,
        "measurement": measurement,
        "uart_log_sha256": sha256(args.log),
        "stable_t32_overlay_preserved": True,
        "next_gate": (
            "Integrate the exact M253 runtime into Web/SSE and run labelled target-camera evaluation."
            if status == "PASS" else
            "Repair and rerun only M253; do not publish the fast Web path."
        ),
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M253_BOARD_COLLECT_PASS" if status == "PASS" else "M253_BOARD_COLLECT_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

