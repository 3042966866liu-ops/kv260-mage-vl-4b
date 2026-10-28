#!/usr/bin/env python3
"""Dependency-light fixed M90 frame preprocessing for the KV260 PS.

This module intentionally accepts decoded RGB frames rather than a video
codec.  The browser samples four frames, which removes FFmpeg/decord/OpenCV
from the board runtime and makes the input memory bound explicit.
"""

from __future__ import annotations

import numpy as np


FRAME_COUNT = 4
FRAME_SIZE = 448
PATCH_SIZE = 16
MERGE_SIZE = 2
CHANNELS = 3
PATCH_DIM = CHANNELS * PATCH_SIZE * PATCH_SIZE
PATCHES_PER_FRAME = (FRAME_SIZE // PATCH_SIZE) ** 2
TOTAL_PATCHES = FRAME_COUNT * PATCHES_PER_FRAME
MERGED_VISUAL_TOKENS = TOTAL_PATCHES // (MERGE_SIZE**2)
IMAGE_MEAN = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
IMAGE_STD = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def validate_frames(frames: np.ndarray) -> np.ndarray:
    array = np.asarray(frames)
    expected = (FRAME_COUNT, FRAME_SIZE, FRAME_SIZE, CHANNELS)
    if array.shape != expected:
        raise ValueError(f"frames must have shape {expected}, got {array.shape}")
    if array.dtype != np.uint8:
        raise ValueError(f"frames must be uint8, got {array.dtype}")
    return array


def patchify_rgb_u8(frames: np.ndarray) -> np.ndarray:
    """Match Qwen2VLImageProcessor.patchify for fixed 4x448 RGB input."""

    array = validate_frames(frames)
    # The official processor converts to channels-first before float32
    # rescale/normalize, then uses 2x2 block-layout patch ordering.
    normalized = array.transpose(0, 3, 1, 2).astype(np.float32)
    normalized = normalized * np.float32(1.0 / 255.0)
    normalized = (normalized - IMAGE_MEAN.reshape(1, 3, 1, 1)) / IMAGE_STD.reshape(1, 3, 1, 1)
    grid_h = FRAME_SIZE // PATCH_SIZE
    grid_w = FRAME_SIZE // PATCH_SIZE
    patches = normalized.reshape(
        FRAME_COUNT,
        CHANNELS,
        grid_h // MERGE_SIZE,
        MERGE_SIZE,
        PATCH_SIZE,
        grid_w // MERGE_SIZE,
        MERGE_SIZE,
        PATCH_SIZE,
    )
    patches = patches.transpose(0, 2, 5, 3, 6, 1, 4, 7)
    return np.ascontiguousarray(patches.reshape(FRAME_COUNT * grid_h * grid_w, PATCH_DIM))


def patch_positions() -> np.ndarray:
    """Match Mage-VL dense-frame 3-D RoPE positions in 2x2 block layout."""

    h = FRAME_SIZE // PATCH_SIZE
    w = FRAME_SIZE // PATCH_SIZE
    t = FRAME_COUNT
    t_coords = np.repeat(np.arange(t, dtype=np.int64), h * w)
    h_coords = np.tile(np.repeat(np.arange(h, dtype=np.int64), w), t)
    w_coords = np.tile(np.arange(w, dtype=np.int64), t * h)
    positions = np.stack((t_coords, h_coords, w_coords), axis=1)
    indices = np.arange(t * h * w).reshape(t, h, w)
    indices = indices.reshape(t, h // MERGE_SIZE, MERGE_SIZE, w // MERGE_SIZE, MERGE_SIZE)
    indices = indices.transpose(0, 1, 3, 2, 4).reshape(-1)
    return positions[indices]


def preprocess(frames: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "pixel_values": patchify_rgb_u8(frames),
        "image_grid_thw": np.repeat(
            np.asarray([[1, FRAME_SIZE // PATCH_SIZE, FRAME_SIZE // PATCH_SIZE]], dtype=np.int64),
            FRAME_COUNT,
            axis=0,
        ),
        "patch_positions": patch_positions(),
    }
