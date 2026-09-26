#!/usr/bin/env python3
"""Isolated, offline-first repair for the M254 alarm-to-review scheduler.

This module is not the deployed M254 implementation. One semantic review may
be outstanding at a time; completed or failed reviews release that capacity.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import threading
from typing import Callable

import numpy as np


@dataclass
class ReviewJob:
    task_id: int
    source_sequences: tuple[int, ...]
    frames: tuple[np.ndarray, ...]
    semantic_sequences: tuple[int, ...] | None = None
    early_terminals: list[tuple[str, dict]] = field(default_factory=list)


class AlarmReviewScheduler:
    def __init__(
        self,
        publish: Callable[[str, dict], None],
        submit_window: Callable[[tuple[np.ndarray, ...]], tuple[int, ...]],
        source_capacity: int = 16,
    ) -> None:
        if source_capacity < 4:
            raise ValueError("source_capacity must be at least four")
        self.publish = publish
        self.submit_window = submit_window
        self._lock = threading.Lock()
        self._frames: deque[tuple[int, np.ndarray]] = deque(maxlen=source_capacity)
        self._active: ReviewJob | None = None
        self._waiting: ReviewJob | None = None
        self._next_task_id = 1
        self._incident_open = False
        self._incident_needs_window = False
        self.fast_results = 0
        self.semantic_reviews_queued = 0
        self.semantic_reviews_completed = 0
        self.semantic_reviews_failed = 0

    def remember(self, sequence: int, frame: np.ndarray) -> None:
        value = np.asarray(frame)
        if value.shape != (448, 448, 3) or value.dtype != np.uint8:
            raise ValueError("M333 frame must be RGB uint8 448x448x3")
        with self._lock:
            if self._frames and sequence <= self._frames[-1][0]:
                raise ValueError("source sequence must increase")
            self._frames.append((int(sequence), np.ascontiguousarray(value).copy()))

    def on_fast_result(self, result: dict) -> None:
        payload = dict(result)
        payload["path"] = "M253-fast-immediate"
        payload["semantic_review_blocks_alarm"] = False
        # The safety event must be visible even if a review is busy or fails.
        self.publish("safety_result", payload)

        skip_reason = None
        job: ReviewJob | None = None
        dispatch_now = False
        replaced_task_id: int | None = None
        with self._lock:
            self.fast_results += 1
            active_alarm = bool(result.get("alarm", {}).get("active"))
            if not active_alarm:
                self._incident_open = False
                self._incident_needs_window = False
                return
            if not self._incident_open:
                self._incident_open = True
                self._incident_needs_window = True
            if not self._incident_needs_window:
                return  # Repeated frames in one continuous alarm are deduplicated.
            try:
                alarm_sequence = int(result["window_index"])
            except (KeyError, TypeError, ValueError):
                skip_reason = "alarm-source-sequence-unavailable"
            else:
                eligible = tuple(item for item in self._frames if item[0] <= alarm_sequence)
                if len(eligible) < 4 or eligible[-1][0] != alarm_sequence:
                    skip_reason = "alarm-source-window-unavailable"
                else:
                    selected = eligible[-4:]
                    job = ReviewJob(
                        task_id=self._next_task_id,
                        source_sequences=tuple(item[0] for item in selected),
                        frames=tuple(item[1] for item in selected),
                    )
                    self._next_task_id += 1
                    self._incident_needs_window = False
                    self.semantic_reviews_queued += 1
                    if self._active is None:
                        self._active = job
                        dispatch_now = True
                    else:
                        replaced_task_id = None if self._waiting is None else self._waiting.task_id
                        self._waiting = job

        if skip_reason is not None:
            self.publish("semantic_review_skipped", {
                "reason": skip_reason,
                "fast_window_index": result.get("window_index"),
            })
            return

        assert job is not None
        if dispatch_now:
            self._dispatch(job)
        else:
            self.publish("semantic_review_waiting", {
                "task_id": job.task_id,
                "source_sequences": list(job.source_sequences),
                "replaced_task_id": replaced_task_id,
                "policy": "latest-pending-only",
            })

    def _dispatch(self, job: ReviewJob) -> None:
        self.publish("semantic_review_queued", {
            "policy": "alarm-only-one-active-one-latest-waiting",
            "task_id": job.task_id,
            "sequences": list(job.source_sequences),
            "fast_alarm_already_emitted": True,
        })
        try:
            semantic_sequences = tuple(int(item) for item in self.submit_window(job.frames))
            if len(semantic_sequences) != 4:
                raise ValueError("semantic submit must return four local sequences")
            with self._lock:
                if self._active is not job:
                    raise RuntimeError("active semantic job changed during submission")
                job.semantic_sequences = semantic_sequences
                early = list(job.early_terminals)
                job.early_terminals.clear()
            for name, payload in early:
                if self.on_semantic_terminal(name, payload):
                    break
        except BaseException as error:
            self._finish_submission_error(job, error)

    def _finish_submission_error(self, job: ReviewJob, error: BaseException) -> None:
        next_job = None
        with self._lock:
            if self._active is not job:
                return
            self._active = self._waiting
            self._waiting = None
            next_job = self._active
            self.semantic_reviews_failed += 1
        self.publish("semantic_review_released", {
            "task_id": job.task_id,
            "terminal_event": "submission_error",
            "source_sequences": list(job.source_sequences),
            "error": f"{type(error).__name__}: {error}",
        })
        if next_job is not None:
            self._dispatch(next_job)

    def on_semantic_terminal(self, name: str, payload: dict) -> bool:
        if name not in ("window_complete", "window_error"):
            return False
        next_job = None
        with self._lock:
            job = self._active
            if job is None:
                return False
            if job.semantic_sequences is None:
                job.early_terminals.append((name, dict(payload)))
                return False
            # Old terminal events must not release a newer review.
            if tuple(payload.get("sequences", ())) != job.semantic_sequences:
                return False
            self._active = self._waiting
            self._waiting = None
            next_job = self._active
            if name == "window_complete":
                self.semantic_reviews_completed += 1
            else:
                self.semantic_reviews_failed += 1
        self.publish("semantic_review_released", {
            "task_id": job.task_id,
            "terminal_event": name,
            "source_sequences": list(job.source_sequences),
            "error": payload.get("error") if name == "window_error" else None,
        })
        if next_job is not None:
            self._dispatch(next_job)
        return True

    def status(self) -> dict:
        with self._lock:
            return {
                "policy": "alarm-only-one-active-one-latest-waiting",
                "latest_frame_capacity": self._frames.maxlen,
                "latest_frame_depth": len(self._frames),
                "fast_results": self.fast_results,
                "semantic_review_queued": self._active is not None,
                "active_task_id": None if self._active is None else self._active.task_id,
                "active_source_sequences": [] if self._active is None else list(self._active.source_sequences),
                "waiting_task_id": None if self._waiting is None else self._waiting.task_id,
                "waiting_source_sequences": [] if self._waiting is None else list(self._waiting.source_sequences),
                "semantic_reviews_queued": self.semantic_reviews_queued,
                "semantic_reviews_completed": self.semantic_reviews_completed,
                "semantic_reviews_failed": self.semantic_reviews_failed,
                "fast_alarm_blocks_on_semantic_review": False,
            }


class SemanticTerminalMonitor:
    """Observe existing semantic journal events without modifying the engine."""

    def __init__(self, journal, scheduler: AlarmReviewScheduler) -> None:
        self.journal = journal
        self.scheduler = scheduler
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cursor = 0
        self.error: str | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("terminal monitor already started")
        self._thread = threading.Thread(target=self._run, name="m333-semantic-terminal", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                events = self.journal.wait_after(self._cursor, timeout=0.2)
                for event in events:
                    event_id = int(event["id"])
                    if event_id <= self._cursor:
                        continue
                    if event_id != self._cursor + 1:
                        raise RuntimeError("semantic event journal gap; review state unknown")
                    self._cursor = event_id
                    self.scheduler.on_semantic_terminal(event["name"], event["payload"])
        except BaseException as error:
            self.error = f"{type(error).__name__}: {error}"
            self.scheduler.publish("semantic_review_monitor_error", {"error": self.error})

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                raise TimeoutError("semantic terminal monitor did not stop")
