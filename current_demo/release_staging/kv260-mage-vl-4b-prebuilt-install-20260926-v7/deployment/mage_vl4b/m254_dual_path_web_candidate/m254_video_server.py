#!/usr/bin/env python3
"""M254 dual-path Web service: M253 immediate safety + M243/M241 review."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time

import m243_video_server  # noqa: F401 - installs accepted M238/M241 globals
import video_server as _server
from fast_frame_pipeline import FastFramePipeline
from latest_fast_stream import LatestFastSafetyEngine
from m253_board_latest_stream import SSDLiteDetector
from m254_dual_path_core import (
    AlarmOnlySemanticReview,
    M243_BOARD_RESULT_SHA256,
    M249_BOARD_RESULT_SHA256,
    M253_BOARD_RESULT_SHA256,
    PublishingPipeline,
)


ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class M254DualPathController(_server.LiveController):
    """Share one SSE journal while keeping the fast path non-blocking."""

    def __init__(self, runtime):
        super().__init__(runtime)
        self.fast_engine = None
        self.review = None
        self._source_sequence = 0
        self._dual_lock = threading.RLock()

    def _publish(self, name: str, payload: dict) -> None:
        engine = self.engine
        if engine is not None:
            engine.events.publish(name, payload)

    def _submit_semantic_window(self, frames: tuple) -> None:
        engine = self.engine
        if engine is None:
            raise RuntimeError("M254 semantic engine is not active")
        for frame in frames:
            engine.frames.push(frame)

    def _verify_predecessors(self) -> None:
        values = (
            (Path(os.environ.get("M254_M243_RESULT", ROOT / "results/M243_WEB_PREFILL_BOARD_RESULT_05.json")), M243_BOARD_RESULT_SHA256, "M243"),
            (Path(os.environ.get("M254_M253_RESULT", ROOT / "results/m253_latest_fast_stream_02/result.json")), M253_BOARD_RESULT_SHA256, "M253"),
            (Path(os.environ.get("M254_M249_RESULT", ROOT / "m253_latest_fast_stream_candidate/M249_KV260_SSDLITE_BOARD_RESULT_03.json")), M249_BOARD_RESULT_SHA256, "M249"),
        )
        for path, expected, name in values:
            if not path.is_file() or _sha256(path) != expected:
                raise RuntimeError(f"M254 {name} predecessor hash mismatch: {path}")

    def start(self, prompt: str, max_new_tokens: int, source_mode: str = "browser-camera", source_label: str = "") -> dict:
        with self._dual_lock:
            if self.fast_engine is not None:
                raise RuntimeError("an M254 dual-path session is already active")
            self._verify_predecessors()
            # Starts M243/M241 loading in its own worker. No semantic frames are
            # submitted until the fast path emits an actual alarm.
            super().start(prompt, max_new_tokens, source_mode, source_label)
            self.review = AlarmOnlySemanticReview(self._publish, self._submit_semantic_window)
            candidate = Path(os.environ.get("M254_M249_CANDIDATE", ROOT / "m249_ssdlite_board_candidate"))
            detector = SSDLiteDetector(
                candidate / "model/ssdlite320_mobilenet_v3_large_coco-a79551df.pth",
                int(os.environ.get("M254_FAST_THREADS", "4")),
            )
            pipeline = PublishingPipeline(FastFramePipeline(), self.review.on_fast_result)
            self.fast_engine = LatestFastSafetyEngine(detector, pipeline)
            self.fast_engine.start()
            self._publish("dual_path_ready", {
                "fast_path": "M253-M249-M251-M248",
                "semantic_path": "M243-M238-M241-T32",
                "semantic_policy": "alarm-only-capacity-one",
                "fast_alarm_blocks_on_semantic_review": False,
            })
            return self.status()

    def submit(self, frame_rgb_u8) -> int:
        with self._dual_lock:
            fast = self.fast_engine
            review = self.review
            sequence = self._source_sequence
            self._source_sequence += 1
        if fast is None or review is None:
            raise RuntimeError("M254 dual-path session has not started")
        review.remember(sequence, frame_rgb_u8)
        fast_sequence = fast.submit(frame_rgb_u8, int(time.time() * 1000))
        if fast_sequence != sequence:
            raise RuntimeError(f"M254 fast/source sequence mismatch {fast_sequence}/{sequence}")
        self._publish("frame", {
            "sequence": sequence,
            "path": "M253-fast-immediate",
            "fast_status": fast.status(),
        })
        return sequence

    def status(self) -> dict:
        value = super().status()
        value.update({
            "mode": "M254-dual-path-latest-only",
            "fast_path": None if self.fast_engine is None else self.fast_engine.status(),
            "semantic_review": None if self.review is None else self.review.status(),
            "semantic_language_runtime": "M243-M238-T32-pack-prefetch-fused-parse",
            "semantic_prefill_attention": "M241-grouped-GQA-reference-RoPE",
            "t64_used": False,
        })
        return value

    def close(self) -> None:
        with self._dual_lock:
            fast = self.fast_engine
            self.fast_engine = None
        if fast is not None:
            fast.close(timeout_s=15.0)
        super().close()


_server.LiveController = M254DualPathController


if __name__ == "__main__":
    raise SystemExit(_server.main())
