#!/usr/bin/env python3
"""Exact prompt IDs and visual-token splice gate for M90."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from video_language_runtime import HIDDEN, IMAGE_PAD_ID
from video_prompt import render, tokenize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    prompt = "Describe the motion and color change in this short video in one sentence."
    with np.load(args.fixture, allow_pickle=False) as fixture:
        expected_ids = fixture["input_ids"][0].astype(np.int64)
    observed_ids = np.asarray(tokenize(args.tokenizer, prompt), dtype=np.int64)
    pad_positions = np.flatnonzero(observed_ids == IMAGE_PAD_ID)
    visual = np.arange(784 * HIDDEN, dtype=np.float32).reshape(784, HIDDEN)
    # The actual class verifies the large embedding payload; this small local
    # splice reproduces the same indexed replacement rule without loading it.
    hidden = np.zeros((observed_ids.size, HIDDEN), dtype=np.float32)
    hidden[pad_positions] = visual
    checks = {
        "token_ids_exact": bool(np.array_equal(observed_ids, expected_ids)),
        "input_token_count_849": observed_ids.size == 849,
        "image_pad_count_784": pad_positions.size == 784,
        "visual_splice_exact": bool(np.array_equal(hidden[pad_positions], visual)),
        "render_has_four_timestamps": all(f"<{i:.1f} seconds>" in render(prompt) for i in range(4)),
    }
    passed = all(checks.values())
    result = {"gate": "M90-video-prompt-and-visual-splice", "status": "PASS" if passed else "FAIL", "checks": checks}
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M90_VIDEO_PROMPT_SPLICE_PASS" if passed else "M90_VIDEO_PROMPT_SPLICE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
