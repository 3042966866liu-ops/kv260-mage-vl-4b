#!/usr/bin/env python3
"""Isolated M332 parser-scale microgate; no FPGA, model, or file mutation.

This reproduces the accepted M236 output parser's FP16 strided extraction,
interleave, power-of-two rescale, finiteness check, and target assignment.
Only the rescale implementation differs. Microgate results do not establish
video-level acceleration and must not be used to promote a deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np


SHAPES = (("q_proj", 4096), ("gate_proj", 9728), ("down_proj", 2560))


def make_payload(width: int, seed: int) -> bytearray:
    if width % 32:
        raise ValueError("width must be divisible by 32")
    words = 32 * width // 2
    payload = bytearray(words * 8)
    rng = np.random.default_rng(seed)
    lanes = np.ndarray((words, 2), dtype="<u2", buffer=payload, strides=(8, 4))
    # Positive/negative finite normal and subnormal FP16; avoid an input
    # distribution that makes non-finite retry dominate this parser test.
    bits = rng.integers(0, 0x7C00, size=(words, 2), dtype=np.uint16)
    bits[:, 0] |= rng.integers(0, 2, size=words, dtype=np.uint16) << 15
    bits[:, 1] |= rng.integers(0, 2, size=words, dtype=np.uint16) << 15
    lanes[:] = bits
    return payload


def parse(payload: bytearray, width: int, shift: int, optimized: bool) -> np.ndarray:
    raw = memoryview(payload)
    if len(raw) != 32 * width * 4:
        raise RuntimeError("payload size mismatch")
    octets = np.frombuffer(raw, dtype=np.uint8)
    lanes = np.ndarray(
        (len(raw) // 8, 2), dtype="<f2", buffer=octets, strides=(8, 4)
    )
    values = lanes.astype(np.float32)
    rows_per_shard = width // 4
    assembled = values.reshape(rows_per_shard // 8, 32, 4, 4, 2)
    assembled = assembled.transpose(1, 2, 0, 3, 4).reshape(32, width)
    if shift:
        if optimized:
            # assembled is a newly materialized writable FP32 array here.
            # Multiplication by 2**-shift is exact for all finite FP16 inputs.
            np.multiply(assembled, np.float32(2.0**-shift), out=assembled)
        else:
            assembled = np.ldexp(assembled, -shift).astype(np.float32)
    if not np.isfinite(assembled).all():
        raise RuntimeError("unexpected nonfinite synthetic output")
    target = np.empty((32, width), dtype=np.float32)
    target[:] = assembled
    return target


def exhaustive_scale_proof() -> None:
    bits = np.arange(1 << 16, dtype=np.uint16)
    half = bits.view("<f2").astype(np.float32)
    finite = half[np.isfinite(half)]
    for shift in range(11):
        reference = np.ldexp(finite, -shift).astype(np.float32)
        candidate = finite.copy()
        np.multiply(candidate, np.float32(2.0**-shift), out=candidate)
        if not np.array_equal(reference.view("<u4"), candidate.view("<u4")):
            raise RuntimeError(f"FP16 exhaustive scale bits differ at shift={shift}")


def measure(payload: bytearray, width: int, shift: int, optimized: bool) -> float:
    started = time.perf_counter_ns()
    parse(payload, width, shift, optimized)
    return (time.perf_counter_ns() - started) / 1e6


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=15)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--shift", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeat < 10 or args.warmup < 1 or not 0 <= args.shift <= 6:
        raise ValueError("invalid measurement parameters")
    exhaustive_scale_proof()
    cases = []
    for ordinal, (name, width) in enumerate(SHAPES):
        payload = make_payload(width, 332 + ordinal)
        original = parse(payload, width, args.shift, False)
        candidate = parse(payload, width, args.shift, True)
        if original.tobytes() != candidate.tobytes():
            raise RuntimeError(f"complete output differs: {name}")
        for _ in range(args.warmup):
            measure(payload, width, args.shift, False)
            measure(payload, width, args.shift, True)
        baseline_ms: list[float] = []
        candidate_ms: list[float] = []
        order: list[str] = []
        for i in range(args.repeat):
            pair = (False, True) if i % 2 == 0 else (True, False)
            for optimized in pair:
                elapsed = measure(payload, width, args.shift, optimized)
                (candidate_ms if optimized else baseline_ms).append(elapsed)
                order.append("candidate" if optimized else "baseline")
        cases.append({
            "name": name,
            "width": width,
            "payload_bytes": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "output_sha256_fp32": hashlib.sha256(original.tobytes()).hexdigest(),
            "complete_output_bit_exact": True,
            "baseline_ms": baseline_ms,
            "candidate_ms": candidate_ms,
            "baseline_median_ms": statistics.median(baseline_ms),
            "candidate_median_ms": statistics.median(candidate_ms),
            "paired_order": order,
        })
    result = {
        "gate": "M332-isolated-FP16-output-parser-scale-microgate",
        "status": "PASS_MICROGATE_NOT_VIDEO" if all(c["complete_output_bit_exact"] for c in cases) else "FAIL",
        "host": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "dtype": "FP16 packet -> FP32 parser output",
        "scale_shift": args.shift,
        "exhaustive_finite_fp16_scale_bits": 11,
        "repeat_per_case": args.repeat,
        "cases": cases,
        "not_proved": "KV260 stage speedup, complete video TTFT, DMA correctness, deployment promotion",
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
