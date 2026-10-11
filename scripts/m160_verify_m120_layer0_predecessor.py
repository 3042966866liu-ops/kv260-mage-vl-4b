#!/usr/bin/env python3
"""Require the exact real-board M144/M145 Layer-0 acceptance before fixed text."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer0-acceptance", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    path = args.layer0_acceptance.resolve()
    if not path.is_file() or sha256(path) != args.expected_sha256:
        raise RuntimeError("M160_LOCKED_UNTIL_EXACT_M145_LAYER0_BOARD_PASS")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("gate") != "M144-M120-complete-layer0-boundary-acceptance":
        raise RuntimeError("M160 Layer-0 gate identity mismatch")
    if value.get("status") != "PASS" or value.get("classification") != "real-board complete Layer-0 numerical gate; fixed-text remains a separate next level":
        raise RuntimeError("M160_LOCKED_UNTIL_EXACT_M145_LAYER0_BOARD_PASS")
    measurement = value.get("measurement", {})
    if measurement.get("build_id") != "0x4d395832" or measurement.get("fpga_execution_proved") is not True:
        raise RuntimeError("M160 Layer-0 hardware evidence mismatch")
    if value.get("thresholds_frozen_before_board_measurement") is not True:
        raise RuntimeError("M160 Layer-0 threshold policy mismatch")
    print(json.dumps({"status": "PASS", "layer0_acceptance_sha256": args.expected_sha256, "build_id": "0x4D395832"}))
    print("M160_M120_LAYER0_PREDECESSOR_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
