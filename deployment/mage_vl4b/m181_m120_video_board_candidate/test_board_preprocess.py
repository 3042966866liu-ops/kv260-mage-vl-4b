#!/usr/bin/env python3
"""Differential gate: lightweight PS preprocessing versus official fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from board_preprocess import MERGED_VISUAL_TOKENS, TOTAL_PATCHES, preprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--official-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    official_result = json.loads(args.official_result.read_text(encoding="utf-8"))
    if official_result.get("status") != "PASS":
        raise RuntimeError("official fixture result is not PASS")
    if sha256(args.fixture) != official_result.get("fixture_sha256"):
        raise RuntimeError("fixture hash does not match official result")
    with np.load(args.fixture, allow_pickle=False) as fixture:
        actual = preprocess(fixture["frames_rgb_u8"])
        expected_pixel = fixture["pixel_values"]
        expected_grid = fixture["image_grid_thw"]
        expected_positions = fixture["patch_positions"]
    pixel_delta = np.abs(actual["pixel_values"] - expected_pixel)
    max_abs = float(pixel_delta.max(initial=0.0))
    mean_abs = float(pixel_delta.mean())
    grid_equal = bool(np.array_equal(actual["image_grid_thw"], expected_grid))
    positions_equal = bool(np.array_equal(actual["patch_positions"], expected_positions))
    shape_ok = actual["pixel_values"].shape == (TOTAL_PATCHES, 768)
    # One float32 rounding step may differ between NumPy and Torch.  This is
    # far below BF16 input precision, while all layout tensors must be exact.
    passed = shape_ok and grid_equal and positions_equal and max_abs <= 5e-7
    payload = {
        "gate": "M90-lightweight-board-preprocess-differential",
        "status": "PASS" if passed else "FAIL",
        "official_fixture_sha256": official_result["fixture_sha256"],
        "pixel_values_shape": list(actual["pixel_values"].shape),
        "image_grid_thw": actual["image_grid_thw"].tolist(),
        "patch_positions_exact": positions_equal,
        "grid_exact": grid_equal,
        "pixel_values_max_abs_error": max_abs,
        "pixel_values_mean_abs_error": mean_abs,
        "merged_visual_tokens": MERGED_VISUAL_TOKENS,
        "boundary": "Decoded RGB frames through official-compatible patch tensors; no vision tower or language generation is claimed.",
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    os.replace(temporary, args.result)
    print("M90_BOARD_PREPROCESS_DIFFERENTIAL_PASS" if passed else "M90_BOARD_PREPROCESS_DIFFERENTIAL_FAIL")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
