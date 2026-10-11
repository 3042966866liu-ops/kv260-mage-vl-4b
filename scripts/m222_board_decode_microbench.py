#!/usr/bin/env python3
"""ARM64 bit-exact/timing gate for the M222 visual W4 decoder."""

from __future__ import annotations

import argparse
import gc
import json
import os
import resource
import time
from pathlib import Path

import numpy as np

import ps_vision_runtime as base
from m222_vectorized_w4_runtime import M222VectorizedFourPortW4Store


def timed_decode(store, name: str):
    started = time.perf_counter()
    value = store.decode(name)
    return value, (time.perf_counter() - started) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    legacy = base.FourPortW4Store(args.layout)
    optimized = M222VectorizedFourPortW4Store(args.layout)
    legacy_ms = 0.0
    optimized_ms = 0.0
    mismatch = None
    count = 0
    elements = 0
    started = time.monotonic()
    try:
        names = sorted(legacy.entries)
        if len(names) != 98 or names != sorted(optimized.entries):
            raise RuntimeError("M222 ARM64 module closure mismatch")
        for index, name in enumerate(names):
            # Alternate order so the page-cache advantage is not always given
            # to the candidate decoder.
            if index % 2 == 0:
                expected, old_ms = timed_decode(legacy, name)
                observed, new_ms = timed_decode(optimized, name)
            else:
                observed, new_ms = timed_decode(optimized, name)
                expected, old_ms = timed_decode(legacy, name)
            legacy_ms += old_ms
            optimized_ms += new_ms
            if not np.array_equal(expected, observed, equal_nan=False):
                delta = np.abs(expected - observed)
                mismatch = {
                    "index": index,
                    "name": name,
                    "max_abs": float(delta.max(initial=0.0)),
                    "mismatch_count": int(np.count_nonzero(expected != observed)),
                }
                break
            count += 1
            elements += int(expected.size)
            del expected, observed
            gc.collect()
    finally:
        legacy.close()
        optimized.close()

    speedup = legacy_ms / optimized_ms if optimized_ms > 0 else 0.0
    passed = mismatch is None and count == 98 and speedup > 1.0
    result = {
        "date": "2026-09-01",
        "gate": "M222-ARM64-vectorized-visual-W4-decoder",
        "status": "PASS" if passed else "FAIL",
        "classification": (
            "Real-KV260 ARM64 decoder equivalence/timing only; not full vision, "
            "FPGA E2E, continuous-stream, or seconds-level performance evidence."
        ),
        "module_count": count,
        "expected_module_count": 98,
        "total_elements": elements,
        "bit_exact": mismatch is None and count == 98,
        "mismatch": mismatch,
        "legacy_decode_ms": legacy_ms,
        "vectorized_decode_ms": optimized_ms,
        "arm64_decode_speedup": speedup,
        "wall_ms": (time.monotonic() - started) * 1000.0,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "model_math_changed": False,
        "quantization_changed": False,
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Only after PASS, stage M222 service delta; then run one fixed four-frame "
            "board numerical/performance gate before any speed claim."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("__M222_BOARD_RESULT_BEGIN__")
    print(json.dumps(result, separators=(",", ":")))
    print("__M222_BOARD_RESULT_END__")
    print("M222_ARM64_DECODE_PASS" if passed else "M222_ARM64_DECODE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

