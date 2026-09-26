#!/usr/bin/env python3
"""Strict binary request envelope for four decoded browser video frames."""

from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np

from board_preprocess import CHANNELS, FRAME_COUNT, FRAME_SIZE


MAGIC = b"M90F"
VERSION = 1
HEADER = struct.Struct("<4sHHHHHHHHI")
FRAME_BYTES = FRAME_COUNT * FRAME_SIZE * FRAME_SIZE * CHANNELS
MAX_PROMPT_BYTES = 3000
MAX_NEW_TOKENS = 256
CONTENT_TYPE = "application/x-tellme-m90-video"


@dataclass(frozen=True)
class VideoRequest:
    prompt: str
    max_new_tokens: int
    frames_rgb_u8: np.ndarray


def encode(prompt: str, max_new_tokens: int, frames: np.ndarray) -> bytes:
    prompt_bytes = prompt.strip().encode("utf-8")
    array = np.asarray(frames)
    if not prompt_bytes or len(prompt_bytes) > MAX_PROMPT_BYTES:
        raise ValueError("prompt must be 1..3000 UTF-8 bytes")
    if not 1 <= max_new_tokens <= MAX_NEW_TOKENS:
        raise ValueError("max_new_tokens must be 1..256")
    expected_shape = (FRAME_COUNT, FRAME_SIZE, FRAME_SIZE, CHANNELS)
    if array.shape != expected_shape or array.dtype != np.uint8:
        raise ValueError(f"frames must be uint8 {expected_shape}")
    raw = np.ascontiguousarray(array).tobytes()
    header = HEADER.pack(MAGIC, VERSION, 0, FRAME_COUNT, FRAME_SIZE, FRAME_SIZE,
                         CHANNELS, max_new_tokens, len(prompt_bytes), len(raw))
    return header + prompt_bytes + raw


def decode(payload: bytes) -> VideoRequest:
    if len(payload) < HEADER.size:
        raise ValueError("request is shorter than the fixed header")
    fields = HEADER.unpack_from(payload)
    magic, version, flags, frame_count, width, height, channels, max_tokens, prompt_size, frame_size = fields
    if magic != MAGIC or version != VERSION or flags != 0:
        raise ValueError("unsupported M90 frame envelope identity")
    if (frame_count, width, height, channels, frame_size) != (
        FRAME_COUNT, FRAME_SIZE, FRAME_SIZE, CHANNELS, FRAME_BYTES
    ):
        raise ValueError("M90 frame geometry is not the fixed 4x448x448xRGB contract")
    if not 1 <= max_tokens <= MAX_NEW_TOKENS or not 1 <= prompt_size <= MAX_PROMPT_BYTES:
        raise ValueError("M90 prompt/token bounds failed")
    expected_size = HEADER.size + prompt_size + frame_size
    if len(payload) != expected_size:
        raise ValueError(f"M90 request length mismatch expected={expected_size} got={len(payload)}")
    prompt_start = HEADER.size
    try:
        prompt = payload[prompt_start:prompt_start + prompt_size].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("prompt is not valid UTF-8") from exc
    if not prompt.strip():
        raise ValueError("prompt is empty")
    frames = np.frombuffer(payload, dtype=np.uint8, offset=prompt_start + prompt_size,
                           count=FRAME_BYTES).reshape(FRAME_COUNT, FRAME_SIZE, FRAME_SIZE, CHANNELS)
    return VideoRequest(prompt=prompt, max_new_tokens=max_tokens, frames_rgb_u8=frames)
