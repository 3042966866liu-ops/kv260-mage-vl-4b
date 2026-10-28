#!/usr/bin/env python3
"""Bounded latest-only per-frame safety engine for the M249/M251 fast path."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time

import numpy as np


@dataclass(frozen=True)
class LatestFrame:
    sequence: int
    captured_unix_ms: int
    rgb_u8: np.ndarray


class LatestFrameSlot:
    """A one-item mailbox: new input replaces pending stale input."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._latest: LatestFrame | None = None
        self._last_claimed = -1
        self.accepted_frames = 0
        self.overwritten_pending_frames = 0

    def push(self, frame: np.ndarray, captured_unix_ms: int) -> int:
        value = np.asarray(frame)
        if value.shape != (448, 448, 3) or value.dtype != np.uint8:
            raise ValueError("frame must be RGB uint8 448x448x3")
        with self._condition:
            sequence = self.accepted_frames
            if self._latest is not None and self._latest.sequence > self._last_claimed:
                self.overwritten_pending_frames += 1
            self._latest = LatestFrame(
                sequence=sequence,
                captured_unix_ms=int(captured_unix_ms),
                rgb_u8=np.ascontiguousarray(value).copy(),
            )
            self.accepted_frames += 1
            self._condition.notify_all()
            return sequence

    def wait_latest(self, stop: threading.Event, timeout_s: float = 1.0) -> LatestFrame | None:
        with self._condition:
            self._condition.wait_for(
                lambda: stop.is_set() or (
                    self._latest is not None and self._latest.sequence > self._last_claimed
                ),
                timeout=timeout_s,
            )
            if stop.is_set() or self._latest is None or self._latest.sequence <= self._last_claimed:
                return None
            item = self._latest
            self._last_claimed = item.sequence
            return item

    def wake(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def snapshot(self) -> dict:
        with self._condition:
            pending = int(self._latest is not None and self._latest.sequence > self._last_claimed)
            return {
                "capacity": 1,
                "depth": pending,
                "accepted_frames": self.accepted_frames,
                "overwritten_pending_frames": self.overwritten_pending_frames,
                "newest_sequence": None if self._latest is None else self._latest.sequence,
                "last_claimed_sequence": self._last_claimed,
            }


class LatestFastSafetyEngine:
    """Load the detector once and always process the newest available frame."""

    def __init__(self, detector, pipeline) -> None:
        self.detector = detector
        self.pipeline = pipeline
        self.frames = LatestFrameSlot()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._condition = threading.Condition()
        self.runtime_load_count = 0
        self.processed_frames = 0
        self.last_completed_sequence = -1
        self.records: list[dict] = []
        self.error: str | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        print("M253_RUNTIME_LOAD_BEGIN", flush=True)
        self.detector.load()
        self.runtime_load_count += 1
        print("M253_RUNTIME_LOAD_PASS", flush=True)
        self._thread = threading.Thread(target=self._worker, name="m253-latest-fast-safety", daemon=True)
        self._thread.start()

    def submit(self, frame: np.ndarray, captured_unix_ms: int) -> int:
        return self.frames.push(frame, captured_unix_ms)

    def wait_completed(self, sequence: int, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        with self._condition:
            while self.last_completed_sequence < sequence and self.error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=remaining)
            return self.last_completed_sequence >= sequence

    def _worker(self) -> None:
        try:
            while not self._stop.is_set():
                item = self.frames.wait_latest(self._stop)
                if item is None:
                    continue
                print(f"M253_DETECT_BEGIN sequence={item.sequence}", flush=True)
                started = time.monotonic()
                detections = self.detector.detect(item.rgb_u8)
                inference_ms = (time.monotonic() - started) * 1000.0
                print(f"M253_DETECT_PASS sequence={item.sequence} detector_ms={inference_ms:.3f}", flush=True)
                evaluated_unix_ms = max(item.captured_unix_ms, int(time.time() * 1000))
                print(f"M253_EVENT_BEGIN sequence={item.sequence}", flush=True)
                event = self.pipeline.process_frame(
                    frame_rgb=item.rgb_u8,
                    detections=detections,
                    sequence=item.sequence,
                    captured_unix_ms=item.captured_unix_ms,
                    evaluated_unix_ms=evaluated_unix_ms,
                )
                print(f"M253_EVENT_PASS sequence={item.sequence}", flush=True)
                record = {
                    "sequence": item.sequence,
                    "detector_ms": inference_ms,
                    "capture_to_result_ms": event["capture_to_result_ms"],
                    "person_count": event["person_count"],
                    "action_counts": event["action_counts"],
                    "alarm": event["alarm"],
                    "realtime_deadline_met": event["realtime_deadline_met"],
                    "evidence_sha256": event["evidence_sha256"],
                }
                with self._condition:
                    self.records.append(record)
                    self.processed_frames += 1
                    self.last_completed_sequence = item.sequence
                    self._condition.notify_all()
                print(
                    f"M253_FRAME_RESULT sequence={item.sequence} detector_ms={inference_ms:.3f} "
                    f"latency_ms={event['capture_to_result_ms']} people={event['person_count']} "
                    f"alarm={event['alarm']['state']}",
                    flush=True,
                )
        except BaseException as error:
            with self._condition:
                self.error = f"{type(error).__name__}: {error}"
                self._condition.notify_all()
            print(f"M253_WORKER_ERROR error={self.error}", flush=True)

    def status(self) -> dict:
        return {
            "mode": "continuous-latest-only-per-frame",
            "source_is_unbounded_contract": True,
            "window_backlog_capacity": 1,
            "runtime_load_count": self.runtime_load_count,
            "processed_frames": self.processed_frames,
            "last_completed_sequence": self.last_completed_sequence,
            "frame_slot": self.frames.snapshot(),
            "error": self.error,
        }

    def close(self, timeout_s: float = 10.0) -> None:
        self._stop.set()
        self.frames.wake()
        if self._thread is not None:
            self._thread.join(timeout_s)
            if self._thread.is_alive():
                raise TimeoutError("M253 worker did not stop")
        self.detector.close()
