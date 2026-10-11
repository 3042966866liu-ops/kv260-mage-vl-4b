#!/usr/bin/env python3
"""Collect exact M249 import and detector result envelopes from a UART log."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PACKAGE_SHA = "0b631d5bd50fa1eeec42d2340a7f8af2b773da4b2df06c8f5204cd1309ee6ea2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(text: str, begin: str, end: str) -> dict:
    start = text.rfind(begin)
    finish = text.rfind(end)
    if start < 0 or finish <= start:
        raise RuntimeError(f"missing UART envelope: {begin}")
    payload = text[start + len(begin):finish].strip().splitlines()
    if len(payload) != 1:
        raise RuntimeError(f"ambiguous UART envelope: {begin}")
    return json.loads(payload[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    imported = extract(text, "__M249_IMPORT_RESULT_BEGIN__", "__M249_IMPORT_RESULT_END__")
    measured = extract(text, "__M249_BOARD_RESULT_BEGIN__", "__M249_BOARD_RESULT_END__")
    status = "PASS" if imported.get("status") == "PASS" and measured.get("status") == "PASS" else "FAIL"
    result = {
        "date": "2026-09-02",
        "gate": "M249-KV260-A53-SSDLite-person-knife-speed-board",
        "status": status,
        "classification": "Real KV260 A53 fixed-frame detector speed and functional sanity evidence; not target-scene accuracy, action recognition, FPGA detector, Web or continuous-stream PASS.",
        "package_manifest_sha256": PACKAGE_SHA,
        "import": imported,
        "measurement": measured,
        "uart_log_sha256": sha256(args.log),
        "stable_t32_overlay_preserved": True,
        "next_gate": (
            "Connect M249 detections to M248 and measure a latest-only continuous stream."
            if status == "PASS"
            else "Repair and rerun only the failed M249 import/speed level; do not integrate Web."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.result)
    print(json.dumps(result, indent=2))
    print("M249_KV260_BOARD_COLLECT_PASS" if status == "PASS" else "M249_KV260_BOARD_COLLECT_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
