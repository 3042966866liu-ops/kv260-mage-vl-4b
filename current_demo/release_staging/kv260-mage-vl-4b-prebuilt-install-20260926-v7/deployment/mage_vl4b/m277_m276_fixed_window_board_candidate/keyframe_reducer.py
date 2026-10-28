#!/usr/bin/env python3
"""Deterministic latest-alarm-frame plus motion-context selection for M257."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Selection:
    indices: tuple[int, ...]
    timestamps_seconds: tuple[float, ...]
    context_scores: tuple[float, ...]
    latest_index: int


def _validate(frames: np.ndarray) -> np.ndarray:
    array = np.asarray(frames)
    if array.ndim != 4 or array.shape[-1] != 3 or array.dtype != np.uint8:
        raise ValueError("frames must be uint8 NHWC RGB")
    if array.shape[0] < 2:
        raise ValueError("at least two source frames are required")
    return array


def _luma_thumbnail(frame: np.ndarray, stride: int = 16) -> np.ndarray:
    sample = frame[::stride, ::stride].astype(np.float32)
    return (
        sample[..., 0] * np.float32(0.299)
        + sample[..., 1] * np.float32(0.587)
        + sample[..., 2] * np.float32(0.114)
    )


def select_alarm_keyframes(
    frames: np.ndarray,
    *,
    keep: int,
    timestamps_seconds: tuple[float, ...] | None = None,
) -> tuple[np.ndarray, Selection]:
    """Always keep the newest alarm frame and the most changed context frames.

    The result stays in chronological order. Ties prefer the more recent
    context frame, which reduces the temporal distance from the alarm frame.
    """

    array = _validate(frames)
    count = int(array.shape[0])
    if keep < 2 or keep > count:
        raise ValueError("keep must be in [2, frame_count]")
    if timestamps_seconds is None:
        timestamps_seconds = tuple(float(index) for index in range(count))
    if len(timestamps_seconds) != count:
        raise ValueError("timestamp count must match frame count")
    if any(
        timestamps_seconds[index] >= timestamps_seconds[index + 1]
        for index in range(count - 1)
    ):
        raise ValueError("timestamps must be strictly increasing")

    latest_index = count - 1
    latest = _luma_thumbnail(array[latest_index])
    scores = []
    for index in range(latest_index):
        context = _luma_thumbnail(array[index])
        score = float(np.mean(np.abs(context - latest)))
        scores.append(score)
    ranked = sorted(range(latest_index), key=lambda index: (scores[index], index), reverse=True)
    selected = tuple(sorted((*ranked[: keep - 1], latest_index)))
    selection = Selection(
        indices=selected,
        timestamps_seconds=tuple(float(timestamps_seconds[index]) for index in selected),
        context_scores=tuple(scores),
        latest_index=latest_index,
    )
    return np.ascontiguousarray(array[list(selected)]), selection


def select_merged_visual_tokens(
    visual_tokens: np.ndarray,
    indices: tuple[int, ...],
    *,
    source_frame_count: int = 4,
    tokens_per_frame: int = 196,
) -> np.ndarray:
    """Select whole per-frame token blocks after the frozen four-frame tower.

    This is the first boardable M257 stage: the accepted M207 vision path stays
    byte-for-byte unchanged, while only the language Prefill sees fewer visual
    tokens. A later variable-frame vision candidate is a separate gate.
    """

    visual = np.asarray(visual_tokens)
    if visual.ndim != 2 or visual.shape[0] != source_frame_count * tokens_per_frame:
        raise ValueError("visual tokens do not match the frozen four-frame block layout")
    if not indices or tuple(sorted(set(indices))) != indices:
        raise ValueError("indices must be unique and chronological")
    if indices[0] < 0 or indices[-1] >= source_frame_count:
        raise ValueError("selected frame index is outside the source layout")
    blocks = [
        visual[index * tokens_per_frame : (index + 1) * tokens_per_frame]
        for index in indices
    ]
    return np.ascontiguousarray(np.concatenate(blocks, axis=0))
