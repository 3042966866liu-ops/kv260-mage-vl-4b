#!/usr/bin/env python3
"""Positive and fault-injection tests for the fixed M90 upload envelope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from video_request import HEADER, decode, encode


def must_fail(payload: bytes) -> bool:
    try:
        decode(payload)
    except ValueError:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.fixture, allow_pickle=False) as fixture:
        frames = fixture["frames_rgb_u8"]
    payload = encode("Describe this video.", 64, frames)
    request = decode(payload)
    checks = {
        "roundtrip_prompt": request.prompt == "Describe this video.",
        "roundtrip_max_tokens": request.max_new_tokens == 64,
        "roundtrip_frames": bool(np.array_equal(request.frames_rgb_u8, frames)),
        "reject_truncated": must_fail(payload[:-1]),
        "reject_trailing": must_fail(payload + b"x"),
        "reject_magic": must_fail(b"BAD!" + payload[4:]),
        "reject_geometry": must_fail(payload[:8] + b"\x03\x00" + payload[10:]),
        "reject_empty": must_fail(b""),
    }
    passed = all(checks.values())
    result = {
        "gate": "M90-fixed-frame-request-envelope",
        "status": "PASS" if passed else "FAIL",
        "header_bytes": HEADER.size,
        "request_bytes": len(payload),
        "checks": checks,
        "boundary": "Browser-to-board decoded RGB transport only; not inference evidence.",
    }
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M90_VIDEO_REQUEST_CONTRACT_PASS" if passed else "M90_VIDEO_REQUEST_CONTRACT_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
