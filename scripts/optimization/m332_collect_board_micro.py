#!/usr/bin/env python3
"""Recover a bounded COM3 result, validate its identity and microgate trigger."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uart-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    transcript = args.uart_log.read_text(encoding="utf-8")
    match = re.search(r"(?m)^([A-Za-z0-9+/]{100,}={0,2})__M75C_UART_RC_0__", transcript)
    if not match:
        raise RuntimeError("missing complete base64 result and successful UART marker")
    payload = base64.b64decode(match.group(1), validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != args.sha256.lower():
        raise RuntimeError(f"board SHA-256 mismatch: {digest}")
    result = json.loads(payload)
    if result["gate"] != "M332-isolated-FP16-output-parser-scale-microgate":
        raise RuntimeError("wrong gate")
    cases = result["cases"]
    if len(cases) != 3 or result["repeat_per_case"] != 15:
        raise RuntimeError("unexpected case count or repetitions")
    speeds = [c["baseline_median_ms"] / c["candidate_median_ms"] for c in cases]
    exact = result["status"] == "PASS_MICROGATE_NOT_VIDEO" and all(c["complete_output_bit_exact"] for c in cases)
    trigger = exact and sum(speed >= 1.2 for speed in speeds) >= 2 and all(
        c["candidate_median_ms"] <= 1.05 * c["baseline_median_ms"] for c in cases
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(json.dumps({
        "sha256": digest,
        "numerical_pass": exact,
        "speedups": {c["name"]: round(speed, 4) for c, speed in zip(cases, speeds)},
        "video_trigger_pass": trigger,
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
