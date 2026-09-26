#!/usr/bin/env python3
"""Non-blocking M253 fast-path to M243/M241 semantic-review bridge.

The fast path is authoritative for immediate safety events.  A slow 4B review
is optional, alarm-triggered and capacity-one; it never blocks frame ingress or
suppresses an immediate alarm.
"""

from __future__ import annotations

from collections import deque
import threading
from typing import Callable

import numpy as np


M243_BOARD_RESULT_SHA256 = "80ea2b8e1d142ef4400aa7e545cf62b3c6ae7a5531e4466df06b35758df096c6"
M253_BOARD_RESULT_SHA256 = "d9e56ea4dbb7b981f8aa02ed834317dca430f252b4ac412c7dbf762478ebc4eb"
M249_BOARD_RESULT_SHA256 = "e45597c3cc14a68420b09d389dde8c2b1cd81ab23eacc5833b5a527d4f633681"


class PublishingPipeline:
    """Publish an unchanged M251/M248 result after the exact pipeline runs."""

    def __init__(self, pipeline, callback: Callable[[dict], None]) -> None:
        self.pipeline = pipeline
        self.callback = callback

    def process_frame(self, **kwargs) -> dict:
        result = self.pipeline.process_frame(**kwargs)
        self.callback(result)
        return result


class AlarmOnlySemanticReview:
    """Remember the latest four source frames and queue at most one review."""

    def __init__(self, publish: Callable[[str, dict], None], submit_window: Callable[[tuple[np.ndarray, ...]], None]):
        self.publish = publish
        self.submit_window = submit_window
        self._lock = threading.Lock()
        self._frames: deque[tuple[int, np.ndarray]] = deque(maxlen=4)
        self._review_queued = False
        self.fast_results = 0
        self.semantic_reviews_queued = 0

    def remember(self, sequence: int, frame: np.ndarray) -> None:
        value = np.asarray(frame)
        if value.shape != (448, 448, 3) or value.dtype != np.uint8:
            raise ValueError("M254 frame must be RGB uint8 448x448x3")
        with self._lock:
            self._frames.append((int(sequence), np.ascontiguousarray(value).copy()))

    def on_fast_result(self, result: dict) -> None:
        payload = dict(result)
        payload["path"] = "M253-fast-immediate"
        payload["semantic_review_blocks_alarm"] = False
        self.publish("safety_result", payload)
        with self._lock:
            self.fast_results += 1
            alarm_active = bool(result.get("alarm", {}).get("active"))
            if not alarm_active:
                return
            if self._review_queued:
                self.publish("semantic_review_skipped", {
                    "reason": "capacity-one-review-already-queued",
                    "fast_window_index": result.get("window_index"),
                })
                return
            if len(self._frames) < 4:
                self.publish("semantic_review_skipped", {
                    "reason": "fewer-than-four-source-frames",
                    "fast_window_index": result.get("window_index"),
                })
                return
            sequences = [item[0] for item in self._frames]
            window = tuple(item[1] for item in self._frames)
            self._review_queued = True
            self.semantic_reviews_queued += 1
        self.publish("semantic_review_queued", {
            "policy": "alarm-only-capacity-one",
            "sequences": sequences,
            "language_scheduler": "M238-T32-input-pack-prefetch-fused-parse",
            "prefill_attention": "M241-grouped-GQA-reference-RoPE",
            "fast_alarm_already_emitted": True,
        })
        self.submit_window(window)

    def status(self) -> dict:
        with self._lock:
            return {
                "policy": "alarm-only-capacity-one",
                "latest_frame_capacity": 4,
                "latest_frame_depth": len(self._frames),
                "fast_results": self.fast_results,
                "semantic_review_queued": self._review_queued,
                "semantic_reviews_queued": self.semantic_reviews_queued,
                "fast_alarm_blocks_on_semantic_review": False,
                "m253_board_result_sha256": M253_BOARD_RESULT_SHA256,
                "m243_board_result_sha256": M243_BOARD_RESULT_SHA256,
            }

