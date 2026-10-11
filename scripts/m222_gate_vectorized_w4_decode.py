#!/usr/bin/env python3
"""Bit-exact offline gate for the M222 vectorized visual W4 decoder."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    source = workspace / "deployment/mage_vl4b/m200_video_e2e_overlay_source"
    m218_source = workspace / "deployment/mage_vl4b/m218_file_replay_source"
    candidate = workspace / "deployment/mage_vl4b/m222_realtime_vision_source"
    layout = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout"
    # M218 contains the accepted Windows-safe progress wrapper.  Put it ahead
    # of the historical scripts/ copies so this offline gate cannot import the
    # old unconditional Linux ``resource`` dependency by accident.
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(m218_source))
    base = load_module("ps_vision_runtime", source / "ps_vision_runtime.py")
    vector = load_module(
        "m222_vectorized_w4_runtime", candidate / "m222_vectorized_w4_runtime.py"
    )

    legacy = base.FourPortW4Store(layout)
    optimized = vector.M222VectorizedFourPortW4Store(layout)
    checked = []
    legacy_ms = 0.0
    optimized_ms = 0.0
    total_elements = 0
    mismatch = None
    try:
        names = sorted(legacy.entries)
        if len(names) != 98 or names != sorted(optimized.entries):
            raise RuntimeError("M222 visual module closure mismatch")
        for index, name in enumerate(names):
            started = time.perf_counter()
            expected = legacy.decode(name)
            legacy_ms += (time.perf_counter() - started) * 1000.0
            started = time.perf_counter()
            observed = optimized.decode(name)
            optimized_ms += (time.perf_counter() - started) * 1000.0
            exact = np.array_equal(expected, observed, equal_nan=False)
            if not exact:
                delta = np.abs(expected - observed)
                mismatch = {
                    "index": index,
                    "name": name,
                    "max_abs": float(delta.max(initial=0.0)),
                    "mismatch_count": int(np.count_nonzero(expected != observed)),
                }
                break
            total_elements += int(expected.size)
            checked.append({
                "name": name,
                "shape": list(expected.shape),
                "sha256_fp32": digest_array(expected),
            })
            del expected, observed
    finally:
        legacy.close()
        optimized.close()

    passed = mismatch is None and len(checked) == 98
    result = {
        "gate": "M222-vectorized-visual-W4-decoder-bitexact-offline",
        "status": "PASS" if passed else "FAIL",
        "classification": (
            "Offline decoder equivalence and host timing only; not ARM64, full vision, "
            "FPGA, E2E, continuous-stream, or seconds-level performance evidence."
        ),
        "module_count": len(checked),
        "expected_module_count": 98,
        "total_elements": total_elements,
        "bit_exact": passed,
        "mismatch": mismatch,
        "legacy_decode_ms": legacy_ms,
        "vectorized_decode_ms": optimized_ms,
        "host_decode_speedup": legacy_ms / optimized_ms if optimized_ms > 0 else None,
        "model_math_changed": False,
        "quantization_changed": False,
        "board_state_changed": False,
        "next_gate": (
            "ARM64 decode microbenchmark and fixed-four-frame numerical/performance gate; "
            "do not promote from this offline result alone."
        ),
        "modules": checked,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("M222_VECTORIZED_W4_DECODE_PASS" if passed else "M222_VECTORIZED_W4_DECODE_FAIL")
    print(json.dumps({key: value for key, value in result.items() if key != "modules"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
