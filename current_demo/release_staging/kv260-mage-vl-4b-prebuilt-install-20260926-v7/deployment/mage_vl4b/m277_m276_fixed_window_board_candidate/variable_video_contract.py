#!/usr/bin/env python3
"""Variable-frame prompt and exact preprocessing contract for M257."""

from __future__ import annotations

from pathlib import Path

import numpy as np


IMAGE_PAD = "<|image_pad|>"
VISION_START = "<|vision_start|>"
VISION_END = "<|vision_end|>"
FRAME_SIZE = 448
PATCH_SIZE = 16
MERGE_SIZE = 2
CHANNELS = 3
PATCH_DIM = CHANNELS * PATCH_SIZE * PATCH_SIZE
VISUAL_TOKENS_PER_FRAME = 196
IMAGE_MEAN = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
IMAGE_STD = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def render(prompt: str, timestamps_seconds: tuple[float, ...]) -> str:
    question = prompt.strip()
    if not question or len(question) > 3000:
        raise ValueError("prompt must contain 1..3000 characters")
    if not 2 <= len(timestamps_seconds) <= 4:
        raise ValueError("M257 supports two to four selected frames")
    frames = "".join(
        f"<{timestamp:.1f} seconds>{VISION_START}{IMAGE_PAD * VISUAL_TOKENS_PER_FRAME}{VISION_END}"
        for timestamp in timestamps_seconds
    )
    return (
        "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{frames}{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def tokenize(tokenizer_json: Path, prompt: str, timestamps_seconds: tuple[float, ...]) -> list[int]:
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    return [
        int(value)
        for value in tokenizer.encode(render(prompt, timestamps_seconds), add_special_tokens=False).ids
    ]


def preprocess(frames: np.ndarray) -> dict[str, np.ndarray]:
    array = np.asarray(frames)
    if array.ndim != 4 or array.shape[1:] != (FRAME_SIZE, FRAME_SIZE, CHANNELS):
        raise ValueError("frames must be N x 448 x 448 x 3")
    if array.dtype != np.uint8 or not 2 <= array.shape[0] <= 4:
        raise ValueError("M257 expects two to four uint8 frames")
    count = int(array.shape[0])
    normalized = array.transpose(0, 3, 1, 2).astype(np.float32)
    normalized = normalized * np.float32(1.0 / 255.0)
    normalized = (normalized - IMAGE_MEAN.reshape(1, 3, 1, 1)) / IMAGE_STD.reshape(1, 3, 1, 1)
    grid_h = FRAME_SIZE // PATCH_SIZE
    grid_w = FRAME_SIZE // PATCH_SIZE
    patches = normalized.reshape(
        count,
        CHANNELS,
        grid_h // MERGE_SIZE,
        MERGE_SIZE,
        PATCH_SIZE,
        grid_w // MERGE_SIZE,
        MERGE_SIZE,
        PATCH_SIZE,
    )
    patches = patches.transpose(0, 2, 5, 3, 6, 1, 4, 7)
    pixel_values = np.ascontiguousarray(patches.reshape(count * grid_h * grid_w, PATCH_DIM))

    t_coords = np.repeat(np.arange(count, dtype=np.int64), grid_h * grid_w)
    h_coords = np.tile(np.repeat(np.arange(grid_h, dtype=np.int64), grid_w), count)
    w_coords = np.tile(np.arange(grid_w, dtype=np.int64), count * grid_h)
    positions = np.stack((t_coords, h_coords, w_coords), axis=1)
    indices = np.arange(count * grid_h * grid_w).reshape(count, grid_h, grid_w)
    indices = indices.reshape(
        count, grid_h // MERGE_SIZE, MERGE_SIZE, grid_w // MERGE_SIZE, MERGE_SIZE
    )
    indices = indices.transpose(0, 1, 3, 2, 4).reshape(-1)
    return {
        "pixel_values": pixel_values,
        "image_grid_thw": np.repeat(
            np.asarray([[1, grid_h, grid_w]], dtype=np.int64), count, axis=0
        ),
        "patch_positions": positions[indices],
        "merged_visual_tokens": np.asarray(count * VISUAL_TOKENS_PER_FRAME, dtype=np.int64),
    }
