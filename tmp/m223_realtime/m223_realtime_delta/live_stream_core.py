#!/usr/bin/env python3
"""Bounded latest-only core for an actually continuous video source."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, Iterable

import numpy as np


@dataclass(frozen=True)
class CapturedFrame:
    sequence: int
    captured_monotonic: float
    received_monotonic: float
    rgb_u8: np.ndarray


class LatestFrameBuffer:
    """Fixed-capacity frame ring; it never creates a window backlog."""

    def __init__(self, capacity: int = 16, window_size: int = 4):
        if capacity < window_size or window_size < 1:
            raise ValueError("invalid live frame buffer geometry")
        self.capacity = int(capacity)
        self.window_size = int(window_size)
        self._frames: deque[CapturedFrame] = deque(maxlen=self.capacity)
        self._condition = threading.Condition()
        self.accepted_frames = 0
        self.overwritten_frames = 0

    def push(self, frame: np.ndarray, captured_monotonic: float | None = None) -> int:
        value = np.asarray(frame)
        if value.shape != (448, 448, 3) or value.dtype != np.uint8:
            raise ValueError("live frame must be contiguous RGB uint8 448x448x3")
        value = np.ascontiguousarray(value).copy()
        with self._condition:
            sequence = self.accepted_frames
            if len(self._frames) == self.capacity:
                self.overwritten_frames += 1
            now = time.monotonic()
            self._frames.append(CapturedFrame(
                sequence=sequence,
                captured_monotonic=(now if captured_monotonic is None else float(captured_monotonic)),
                received_monotonic=now,
                rgb_u8=value,
            ))
            self.accepted_frames += 1
            self._condition.notify_all()
            return sequence

    def wait_latest(self, after_sequence: int, stop: threading.Event,
                    timeout: float = 1.0) -> tuple[CapturedFrame, ...] | None:
        with self._condition:
            self._condition.wait_for(
                lambda: stop.is_set() or (
                    len(self._frames) >= self.window_size
                    and self._frames[-1].sequence > after_sequence
                ),
                timeout=timeout,
            )
            if stop.is_set() or len(self._frames) < self.window_size:
                return None
            latest = tuple(self._frames)[-self.window_size:]
            if latest[-1].sequence <= after_sequence:
                return None
            return latest

    def wake(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def snapshot(self) -> dict:
        with self._condition:
            return {
                "capacity": self.capacity,
                "depth": len(self._frames),
                "accepted_frames": self.accepted_frames,
                "overwritten_frames": self.overwritten_frames,
                "oldest_sequence": self._frames[0].sequence if self._frames else None,
                "newest_sequence": self._frames[-1].sequence if self._frames else None,
            }


class EventJournal:
    def __init__(self, capacity: int = 256):
        self._events: deque[dict] = deque(maxlen=int(capacity))
        self._condition = threading.Condition()
        self._next_id = 1

    def publish(self, name: str, payload: dict) -> dict:
        with self._condition:
            event = {
                "id": self._next_id,
                "name": str(name),
                "emitted_monotonic": time.monotonic(),
                "payload": dict(payload),
            }
            self._next_id += 1
            self._events.append(event)
            self._condition.notify_all()
            return event

    def after(self, event_id: int) -> list[dict]:
        with self._condition:
            return [event for event in self._events if event["id"] > event_id]

    def wait_after(self, event_id: int, timeout: float = 15.0) -> list[dict]:
        with self._condition:
            self._condition.wait_for(
                lambda: bool(self._events and self._events[-1]["id"] > event_id),
                timeout=timeout,
            )
            return [event for event in self._events if event["id"] > event_id]


class ContinuousVideoEngine:
    """One inference worker that always skips directly to the newest window."""

    def __init__(self, runtime, prompt: str, max_new_tokens: int = 1,
                 buffer_capacity: int = 16, window_size: int = 4):
        self.runtime = runtime
        self.prompt = str(prompt)
        self.max_new_tokens = int(max_new_tokens)
        self.frames = LatestFrameBuffer(buffer_capacity, window_size)
        self.events = EventJournal()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.runtime_load_count = 0
        self.inference_busy = False
        self.windows_started = 0
        self.windows_completed = 0
        self.last_started_newest_sequence = -1
        self.last_completed_newest_sequence = -1
        self.last_window_sequences: list[int] = []
        self.last_result_monotonic: float | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._thread = threading.Thread(target=self._worker, name="m209-live-inference", daemon=True)
            self._thread.start()

    def submit(self, frame: np.ndarray, captured_monotonic: float | None = None) -> int:
        sequence = self.frames.push(frame, captured_monotonic)
        self.events.publish("frame", {
            "sequence": sequence,
            "buffer": self.frames.snapshot(),
            "inference_busy": self.inference_busy,
        })
        return sequence

    def _worker(self) -> None:
        try:
            self.runtime.load()
            self.runtime_load_count += 1
            self.events.publish("runtime", {"status": "ready", "load_count": 1})
            while not self._stop.is_set():
                window = self.frames.wait_latest(
                    self.last_started_newest_sequence, self._stop, timeout=1.0
                )
                if window is None:
                    continue
                sequences = [item.sequence for item in window]
                captured = [item.captured_monotonic for item in window]
                newest = sequences[-1]
                self.last_started_newest_sequence = newest
                self.last_window_sequences = sequences
                self.windows_started += 1
                self.inference_busy = True
                started = time.monotonic()
                self.events.publish("window_begin", {
                    "window_index": self.windows_started - 1,
                    "sequences": sequences,
                    "newest_capture_age_ms": (started - captured[-1]) * 1000.0,
                    "buffer": self.frames.snapshot(),
                })
                request = SimpleNamespace(
                    prompt=self.prompt,
                    max_new_tokens=self.max_new_tokens,
                    frames_rgb_u8=np.stack([item.rgb_u8 for item in window], axis=0),
                )
                try:
                    for name, payload in self.runtime.stream(request):
                        self.events.publish(name, {
                            **dict(payload),
                            "window_sequences": sequences,
                            "window_newest_sequence": newest,
                        })
                    completed = time.monotonic()
                    self.windows_completed += 1
                    self.last_completed_newest_sequence = newest
                    self.last_result_monotonic = completed
                    self.events.publish("window_complete", {
                        "sequences": sequences,
                        "inference_ms": (completed - started) * 1000.0,
                        "result_age_from_newest_capture_ms": (completed - captured[-1]) * 1000.0,
                        "buffer": self.frames.snapshot(),
                    })
                except BaseException as error:
                    self.events.publish("window_error", {
                        "sequences": sequences,
                        "error": f"{type(error).__name__}: {error}",
                    })
                finally:
                    self.inference_busy = False
        finally:
            self.runtime.close()
            self.events.publish("runtime", {"status": "closed", "load_count": self.runtime_load_count})

    def status(self) -> dict:
        return {
            "mode": "continuous-latest-only",
            "source_is_unbounded": True,
            "window_backlog_capacity": 1,
            "inference_busy": self.inference_busy,
            "runtime_load_count": self.runtime_load_count,
            "windows_started": self.windows_started,
            "windows_completed": self.windows_completed,
            "last_started_newest_sequence": self.last_started_newest_sequence,
            "last_completed_newest_sequence": self.last_completed_newest_sequence,
            "last_window_sequences": list(self.last_window_sequences),
            "buffer": self.frames.snapshot(),
            "last_result_monotonic": self.last_result_monotonic,
        }

    def close(self, timeout: float = 10.0) -> None:
        self._stop.set()
        self.frames.wake()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                raise TimeoutError("live inference worker did not stop")
