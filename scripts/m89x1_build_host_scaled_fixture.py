#!/usr/bin/env python3
"""Power-of-two scale the activation-scale fields in the retained QKV fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


MAGIC = b"M89X1NQ"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shift", type=int, default=6)
    args = parser.parse_args()
    raw = bytearray(args.input.read_bytes())
    if raw[:7] != MAGIC:
        raise RuntimeError("M89X1_HOST_SCALE_FIXTURE_MAGIC_FAIL")
    _, max_chain, tokens, valid_tokens = struct.unpack_from("<IIII", raw, 7)
    _, _, _, descriptors, groups, _ = struct.unpack_from("<IIIIII", raw, 23)
    if max_chain != 10 or tokens != 32 or valid_tokens != 32 or descriptors != 4 or groups != 40:
        raise RuntimeError("M89X1_HOST_SCALE_FIXTURE_HEADER_FAIL")
    cursor = 47
    for _ in range(descriptors):
        bits, words, descriptor_groups, _, _ = struct.unpack_from("<BBBBI", raw, cursor)
        cursor += 8
        if bits != 2 or words != 9 or descriptor_groups != groups:
            raise RuntimeError("M89X1_HOST_SCALE_FIXTURE_DESCRIPTOR_FAIL")
        cursor += 4 * groups * 17 * 16
    records = np.frombuffer(raw, dtype=np.uint8, count=groups * tokens * 80, offset=cursor).reshape(groups, tokens, 80)
    original_bits = records[:, :, 64:66].copy().reshape(-1, 2).view("<u2").reshape(groups, tokens)
    original = original_bits.view("<f2")
    scaled = np.ldexp(original.astype(np.float32), args.shift).astype("<f2")
    if not np.all(np.isfinite(scaled)) or np.any((original != 0) & (scaled == 0)):
        raise RuntimeError("M89X1_HOST_SCALE_FIXTURE_RANGE_FAIL")
    records[:, :, 64:66] = scaled.view("<u2").reshape(groups, tokens, 1).view(np.uint8).reshape(groups, tokens, 2)
    output = bytes(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    result = {
        "gate": "M89-X1-host-power2-scale-fixture",
        "status": "PASS",
        "shift": args.shift,
        "factor": 1 << args.shift,
        "input_sha256": sha256(args.input.read_bytes()),
        "output_sha256": sha256(output),
        "activation_scale_min_before": float(np.min(original)),
        "activation_scale_min_after": float(np.min(scaled)),
        "activation_scale_max_before": float(np.max(original)),
        "activation_scale_max_after": float(np.max(scaled)),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
