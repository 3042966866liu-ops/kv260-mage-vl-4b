#!/usr/bin/env python3
"""Numerical gate for the memory-bounded PS W4/high-precision vision route."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

from ps_vision_runtime import M90PSVisionRuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-code", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--processor-fixture", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.processor_fixture, allow_pickle=False) as fixture:
        pixels = fixture["pixel_values"]
        grid = fixture["image_grid_thw"]
        positions = fixture["patch_positions"]
    runtime = M90PSVisionRuntime(args.model_code, args.layout, args.raw_manifest)
    try:
        observed = runtime(pixels, grid, positions)
    finally:
        runtime.close()
    with np.load(args.golden, allow_pickle=False) as fixture:
        bits = fixture["merged_vision_w4_bf16_bits"]
    expected = (bits.astype(np.uint32) << 16).view(np.float32)
    delta = observed.astype(np.float64) - expected.astype(np.float64)
    cosine = float(np.vdot(observed.astype(np.float64), expected.astype(np.float64)) /
                   (np.linalg.norm(observed.astype(np.float64)) * np.linalg.norm(expected.astype(np.float64))))
    metrics = {
        "cosine_similarity": cosine,
        "max_abs_error": float(np.max(np.abs(delta))),
        "mean_abs_error": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(delta * delta))),
    }
    passed = cosine >= 0.999 and metrics["rmse"] <= 0.05
    result = {
        "gate": "M90-memory-bounded-PS-W4-high-precision-vision",
        "status": "PASS" if passed else "FAIL",
        "output_shape": list(observed.shape),
        "metrics_vs_M56_W4_BF16_golden": metrics,
        "activation_precision": "BF16 on PS (M63 accepted semantic route)",
        "packed_weight_precision": "exact M56 W4/FP16-scale/orientation storage",
        "peak_weight_policy": "one Linear dequantized at a time",
        "visual_a8_used": False,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M90_PS_VISION_RUNTIME_PASS" if passed else "M90_PS_VISION_RUNTIME_FAIL")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
