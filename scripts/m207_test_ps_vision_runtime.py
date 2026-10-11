#!/usr/bin/env python3
"""Offline numerical/performance gate for M207 FP32 Linear GEMM."""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
import warnings
from pathlib import Path

import numpy as np

from m207_ps_vision_runtime import M207PSVisionRuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-code", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--processor-fixture", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--heartbeat-seconds", type=float, default=30.0)
    args = parser.parse_args()
    with np.load(args.processor_fixture, allow_pickle=False) as fixture:
        pixels = fixture["pixel_values"]
        grid = fixture["image_grid_thw"]
        positions = fixture["patch_positions"]
    init_started = time.monotonic()
    runtime = M207PSVisionRuntime(
        args.model_code,
        args.layout,
        args.raw_manifest,
        heartbeat_seconds=args.heartbeat_seconds,
    )
    init_ms = (time.monotonic() - init_started) * 1000.0
    try:
        forward_started = time.monotonic()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            observed = runtime(pixels, grid, positions)
        forward_ms = (time.monotonic() - forward_started) * 1000.0
    finally:
        runtime.close()
    messages = [str(item.message) for item in caught]
    bf16_gemm = [
        message for message in messages
        if "mkldnn_matmul" in message and "bf16" in message.lower()
    ]
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
    passed = finite and cosine >= 0.999 and metrics["rmse"] <= 0.05
    result = {
        "gate": "M207-M198-policy-FP32-W4-GEMM-BF16-output-PS-vision",
        "status": "PASS" if passed else "FAIL",
        "output_shape": list(observed.shape),
        "finite": finite,
        "metrics_vs_M56_W4_BF16_golden": metrics,
        "gemm_dtype": "FP32 for every W4 Linear",
        "state_policy": "M198: layers 0-5 BF16, layers 6-23 FP32, block boundaries BF16",
        "fp32_encoder_layers": list(M207PSVisionRuntime.FP32_LAYERS),
        "packed_weight_precision": "exact M56 W4/FP16-scale/orientation storage",
        "progress_policy": "24 layer begin/pass events plus 30-second in-layer heartbeat",
        "init_ms": init_ms,
        "vision_forward_ms": forward_ms,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "bf16_gemm_warning_count": len(bf16_gemm),
        "warning_count": len(messages),
        "thresholds": {"cosine_minimum": 0.999, "rmse_maximum": 0.05},
        "reference_boundary": "M56 W4/BF16 fixed-four-frame golden",
        "visual_a8_used": False,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M207_PS_VISION_RUNTIME_PASS" if passed else "M207_PS_VISION_RUNTIME_FAIL")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
