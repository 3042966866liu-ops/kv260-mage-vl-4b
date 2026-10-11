#!/usr/bin/env python3
"""Collect the exact M254 readiness envelope from COM3."""

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
    begin, end = "__M254_BOARD_RESULT_BEGIN__", "__M254_BOARD_RESULT_END__"
    start, finish = text.rfind(begin), text.rfind(end)
    if start < 0 or finish <= start:
        raise RuntimeError("missing M254 UART result envelope")
    lines = text[start + len(begin):finish].strip().splitlines()
    if len(lines) != 1:
        raise RuntimeError("ambiguous M254 UART result envelope")
    measurement = json.loads(lines[0])
    passed = (
        measurement.get("status") == "PASS"
        and measurement.get("package_manifest_sha256") == args.package_manifest_sha256
        and "M254_DUAL_PATH_WEB_BOARD_RUNNER_PASS" in text
        and "__M254_RUNNER_RC_0__" in text
    )
    result = {
        "date": "2026-09-02",
        "gate": "M254-KV260-dual-path-Web-runtime-board",
        "status": "PASS_CANDIDATE_SERVICE_ACTIVE" if passed else "FAIL_NOT_PROMOTED",
        "classification": "Real KV260 no-frame M253-fast plus M243/M238/M241 semantic-runtime identity and service activation; not frame inference, target-scene accuracy, semantic output, alarm latency, or full Web acceptance.",
        "package_manifest_sha256": args.package_manifest_sha256,
        "measurement": measurement,
        "uart_log_sha256": sha256(args.log),
        "stable_t32_overlay_preserved": True,
        "next_gate": (
            "Run labelled knife/non-knife frames through the Web endpoint and require immediate M253 safety_result before optional M243/M241 review."
            if passed else
            "Retain or restore M243; debug only M254 readiness without frame inference."
        ),
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M254_BOARD_COLLECT_PASS" if passed else "M254_BOARD_COLLECT_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

