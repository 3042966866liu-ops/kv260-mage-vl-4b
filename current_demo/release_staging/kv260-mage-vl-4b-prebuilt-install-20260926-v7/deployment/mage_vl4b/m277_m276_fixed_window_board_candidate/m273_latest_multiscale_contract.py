#!/usr/bin/env python3
"""Exact latest-alarm-frame global/detail 224 preprocessing and tokenizer contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np


M273_KNIFE_PROMPT = (
    "[TELLME_KNIFE_BINARY_V2] Inspect these video views. "
    "Answer exactly 1 if a knife is visible, otherwise 0:"
)
IMAGE_PAD = "<|image_pad|>"
VISION_START = "<|vision_start|>"
VISION_END = "<|vision_end|>"
SOURCE_SIZE = 448
VIEW_SIZE = 224
PATCH_SIZE = 16
MERGE_SIZE = 2
CHANNELS = 3
PATCH_DIM = CHANNELS * PATCH_SIZE * PATCH_SIZE
VIEW_COUNT = 2
VISUAL_TOKENS_PER_VIEW = 49
VISUAL_TOKENS = VIEW_COUNT * VISUAL_TOKENS_PER_VIEW
IMAGE_MEAN = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
IMAGE_STD = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def _area_downsample_2x(frame: np.ndarray) -> np.ndarray:
    values = frame.astype(np.float32).reshape(VIEW_SIZE, 2, VIEW_SIZE, 2, CHANNELS)
    return np.rint(values.mean(axis=(1, 3), dtype=np.float32)).clip(0, 255).astype(np.uint8)


def make_views(latest_frame: np.ndarray) -> np.ndarray:
    array = np.asarray(latest_frame)
    if array.shape != (1, SOURCE_SIZE, SOURCE_SIZE, CHANNELS) or array.dtype != np.uint8:
        raise ValueError("M273 requires exactly one uint8 RGB448 latest alarm frame")
    frame = array[0]
    offset = (SOURCE_SIZE - VIEW_SIZE) // 2
    end = offset + VIEW_SIZE
    return np.ascontiguousarray(np.stack((
        _area_downsample_2x(frame),
        np.ascontiguousarray(frame[offset:end, offset:end]),
    )), dtype=np.uint8)


def render(_external_prompt: str, timestamp_seconds: float) -> str:
    frames = "".join(
        f"<{timestamp_seconds:.1f} seconds>{VISION_START}"
        f"{IMAGE_PAD * VISUAL_TOKENS_PER_VIEW}{VISION_END}"
        for _ in range(VIEW_COUNT)
    )
    return (
        "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{frames}{M273_KNIFE_PROMPT}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def tokenize(tokenizer_json: Path, external_prompt: str, timestamp_seconds: float) -> list[int]:
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    return [
        int(value)
        for value in tokenizer.encode(
            render(external_prompt, timestamp_seconds), add_special_tokens=False
        ).ids
    ]


def preprocess(latest_frame: np.ndarray) -> dict[str, np.ndarray]:
    views = make_views(latest_frame)
    normalized = views.astype(np.float32).transpose(0, 3, 1, 2) * np.float32(1.0 / 255.0)
    normalized = (
        normalized - IMAGE_MEAN.reshape(1, 3, 1, 1)
    ) / IMAGE_STD.reshape(1, 3, 1, 1)
    grid_h = VIEW_SIZE // PATCH_SIZE
    grid_w = VIEW_SIZE // PATCH_SIZE
    patches = normalized.reshape(
        VIEW_COUNT, CHANNELS, grid_h // MERGE_SIZE, MERGE_SIZE, PATCH_SIZE,
        grid_w // MERGE_SIZE, MERGE_SIZE, PATCH_SIZE,
    )
    patches = patches.transpose(0, 2, 5, 3, 6, 1, 4, 7)
    pixel_values = np.ascontiguousarray(patches.reshape(VIEW_COUNT * grid_h * grid_w, PATCH_DIM))
    t_coords = np.repeat(np.arange(VIEW_COUNT, dtype=np.int64), grid_h * grid_w)
    h_coords = np.tile(np.repeat(np.arange(grid_h, dtype=np.int64), grid_w), VIEW_COUNT)
    w_coords = np.tile(np.arange(grid_w, dtype=np.int64), VIEW_COUNT * grid_h)
    positions = np.stack((t_coords, h_coords, w_coords), axis=1)
    indices = np.arange(VIEW_COUNT * grid_h * grid_w).reshape(VIEW_COUNT, grid_h, grid_w)
    indices = indices.reshape(
        VIEW_COUNT, grid_h // MERGE_SIZE, MERGE_SIZE, grid_w // MERGE_SIZE, MERGE_SIZE
    )
    indices = indices.transpose(0, 1, 3, 2, 4).reshape(-1)
    return {
        "pixel_values": pixel_values,
        "image_grid_thw": np.repeat(
            np.asarray([[1, grid_h, grid_w]], dtype=np.int64), VIEW_COUNT, axis=0
        ),
        "patch_positions": positions[indices],
        "merged_visual_tokens": np.asarray(VISUAL_TOKENS, dtype=np.int64),
        "view_count": np.asarray(VIEW_COUNT, dtype=np.int64),
    }
