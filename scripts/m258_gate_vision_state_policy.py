#!/usr/bin/env python3
"""Fixed-four-frame numerical gate for one isolated M258 state policy."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import resource
import sys
import time
import warnings
from pathlib import Path

import numpy as np

# The executed script directory contains historical M206/M207 copies.  They
# must not shadow the hash-locked deployment modules supplied through
# PYTHONPATH, because the active M254 service uses the deployment copies.
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [
    item for item in sys.path
    if Path(item or ".").resolve() != _SCRIPT_DIR
]

from m258_vectorized_w4_runtime import M258PSVisionRuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-code", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--processor-fixture", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--bf16-prefix", type=int, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    with np.load(args.processor_fixture, allow_pickle=False) as fixture:
        pixels = fixture["pixel_values"]
        grid = fixture["image_grid_thw"]
        positions = fixture["patch_positions"]

    init_started = time.monotonic()
    runtime = M258PSVisionRuntime(
        args.model_code,
        args.layout,
        args.raw_manifest,
        bf16_prefix=args.bf16_prefix,
        heartbeat_seconds=3600.0,
    )
    init_ms = (time.monotonic() - init_started) * 1000.0
    try:
        started = time.monotonic()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Runtime progress remains enabled in the deployable module.  The
            # offline sweep suppresses it so one concise PASS/FAIL line is the
            # complete machine-readable console contract.
            with contextlib.redirect_stdout(io.StringIO()):
                observed = runtime(pixels, grid, positions)
        forward_ms = (time.monotonic() - started) * 1000.0
        decoder = runtime.decoder_evidence()
        policy = runtime.state_policy_evidence()
    finally:
        runtime.close()

    with np.load(args.golden, allow_pickle=False) as fixture:
        bits = fixture["merged_vision_w4_bf16_bits"]
    expected = (bits.astype(np.uint32) << 16).view(np.float32)
    delta = observed.astype(np.float64) - expected.astype(np.float64)
    cosine = float(
        np.vdot(observed.astype(np.float64), expected.astype(np.float64))
        / (np.linalg.norm(observed.astype(np.float64))
           * np.linalg.norm(expected.astype(np.float64)))
    )
    metrics = {
        "cosine_similarity": cosine,
        "max_abs_error": float(np.max(np.abs(delta))),
        "mean_abs_error": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
    }
    finite = bool(np.isfinite(observed).all())
    passed = (
        finite
        and cosine >= 0.999
        and metrics["rmse"] <= 0.05
        and decoder["decode_calls"] == 98
    )
    messages = [str(item.message) for item in caught]
    result = {
        "gate": "M258-fixed-four-frame-vision-state-policy",
        "status": "PASS" if passed else "FAIL",
        "classification": (
            "Offline numerical and host timing evidence only; not ARM64, board, "
            "FPGA, E2E, Web, semantic-accuracy, or measured board speed evidence."
        ),
        "policy": policy,
        "output_shape": list(observed.shape),
        "finite": finite,
        "metrics_vs_M56_W4_BF16_golden": metrics,
        "decoder_evidence": decoder,
        "init_ms": init_ms,
        "vision_forward_ms": forward_ms,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "warning_count": len(messages),
        "thresholds": {
            "cosine_minimum": 0.999,
            "rmse_maximum": 0.05,
            "decode_calls": 98,
        },
        "model_math_changed": True,
        "quantization_changed": False,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, args.result)
    print(
        f"M258_VISION_STATE_POLICY_{'PASS' if passed else 'FAIL'} "
        f"bf16_prefix={args.bf16_prefix} cosine={cosine:.12f} "
        f"rmse={metrics['rmse']:.12f} forward_ms={forward_ms:.3f}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
