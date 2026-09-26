#!/usr/bin/env python3
"""Offline M333 scheduler regression; no detector, model, FPGA or Web server."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace

import numpy as np

ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "tmp/m223_realtime/m223_realtime_delta/live_stream_core.py").is_file()
)
LIVE_CORE = ROOT / "tmp/m223_realtime/m223_realtime_delta"
sys.path.insert(0, str(LIVE_CORE))

from live_stream_core import EventJournal  # noqa: E402
from m333_review_bridge import AlarmReviewScheduler, SemanticTerminalMonitor  # noqa: E402


def frame(sequence: int) -> np.ndarray:
    return np.full((448, 448, 3), sequence % 256, dtype=np.uint8)


def fast(sequence: int, active: bool) -> dict:
    return {"window_index": sequence, "alarm": {"active": active}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("RESULT_REPRODUCED.json"))
    args = parser.parse_args()
    checks: dict[str, bool] = {}
    journal = EventJournal()
    submitted: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

    def publish(name: str, payload: dict) -> None:
        journal.publish(name, payload)

    def submit(window: tuple[np.ndarray, ...]) -> tuple[int, ...]:
        local = tuple(range(4 * len(submitted), 4 * len(submitted) + 4))
        submitted.append((tuple(int(item[0, 0, 0]) for item in window), local))
        return local

    scheduler = AlarmReviewScheduler(publish, submit)
    monitor = SemanticTerminalMonitor(journal, scheduler)
    monitor.start()
    try:
        for sequence in range(11):
            scheduler.remember(sequence, frame(sequence))
            if sequence == 3:
                scheduler.on_fast_result(fast(sequence, True))
            elif sequence == 4:
                scheduler.on_fast_result(fast(sequence, True))
            elif sequence in (5, 7, 9):
                scheduler.on_fast_result(fast(sequence, False))
            elif sequence in (6, 8):
                scheduler.on_fast_result(fast(sequence, True))
        checks["first_alarm_exact_four_frames"] = submitted == [((0, 1, 2, 3), (0, 1, 2, 3))]
        checks["busy_keeps_only_latest_distinct_incident"] = (
            scheduler.status()["active_task_id"] == 1
            and scheduler.status()["waiting_task_id"] == 3
            and scheduler.status()["waiting_source_sequences"] == [5, 6, 7, 8]
        )
        journal.publish("window_complete", {"sequences": [0, 1, 2, 3]})
        deadline = time.monotonic() + 2.0
        while len(submitted) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        checks["completed_review_dispatches_latest_waiting"] = submitted == [
            ((0, 1, 2, 3), (0, 1, 2, 3)),
            ((5, 6, 7, 8), (4, 5, 6, 7)),
        ]
        journal.publish("window_complete", {"sequences": [0, 1, 2, 3]})
        time.sleep(0.05)
        checks["old_terminal_does_not_clear_new_job"] = scheduler.status()["active_task_id"] == 3
        journal.publish("window_error", {"sequences": [4, 5, 6, 7], "error": "fixture"})
        deadline = time.monotonic() + 2.0
        while scheduler.status()["active_task_id"] is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        checks["error_releases_capacity"] = (
            scheduler.status()["semantic_reviews_completed"] == 1
            and scheduler.status()["semantic_reviews_failed"] == 1
            and scheduler.status()["active_task_id"] is None
        )
        scheduler.on_fast_result(fast(10, True))
        checks["new_incident_after_failure_can_retry"] = (
            scheduler.status()["active_task_id"] == 4
            and submitted[-1][0] == (7, 8, 9, 10)
        )
        names = [event["name"] for event in journal.after(0)]
        checks["fast_alarm_never_waits_for_semantic"] = (
            names.index("safety_result") < names.index("semantic_review_queued")
            and len([name for name in names if name == "safety_result"]) == 8
        )
        checks["monitor_has_no_error"] = monitor.error is None
    finally:
        monitor.close()

    # A delayed fast result must use frames at or before its own sequence.
    delayed = []
    delayed_scheduler = AlarmReviewScheduler(lambda *_: None, lambda window: delayed.append(tuple(int(x[0, 0, 0]) for x in window)) or (0, 1, 2, 3))
    for sequence in range(8):
        delayed_scheduler.remember(sequence, frame(sequence))
    delayed_scheduler.on_fast_result(fast(4, True))
    checks["delayed_alarm_uses_its_own_window"] = delayed == [(1, 2, 3, 4)]

    # A failed submit is recorded without killing the fast path or locking out
    # a later, separate alarm incident.
    failure_events = []
    failing = AlarmReviewScheduler(
        lambda name, payload: failure_events.append((name, payload)),
        lambda _window: (_ for _ in ()).throw(RuntimeError("fixture submit failure")),
    )
    for sequence in range(5):
        failing.remember(sequence, frame(sequence))
    failing.on_fast_result(fast(3, True))
    failing.on_fast_result(fast(4, False))
    checks["submission_failure_recovers"] = (
        failing.status()["semantic_reviews_failed"] == 1
        and failing.status()["active_task_id"] is None
        and any(name == "safety_result" for name, _ in failure_events)
    )

    early_scheduler = None

    def immediate_submit(_window):
        early_scheduler.on_semantic_terminal("window_complete", {"sequences": [0, 1, 2, 3]})
        return (0, 1, 2, 3)

    early_scheduler = AlarmReviewScheduler(lambda *_: None, immediate_submit)
    for sequence in range(4):
        early_scheduler.remember(sequence, frame(sequence))
    early_scheduler.on_fast_result(fast(3, True))
    checks["terminal_during_submit_is_not_lost"] = (
        early_scheduler.status()["semantic_reviews_completed"] == 1
        and early_scheduler.status()["active_task_id"] is None
    )

    # Import the isolated Web wrapper against a fake predecessor. This checks
    # the callback wiring without loading the board model or HTTP listener.
    fake_m254 = ModuleType("m254_video_server")

    class FakeFrames:
        def __init__(self) -> None:
            self.values = []

        def push(self, value):
            sequence = len(self.values)
            self.values.append(np.asarray(value).copy())
            return sequence

    class FakeController:
        def __init__(self, _runtime):
            self.engine = None
            self.fast_engine = None
            self.review = None

        def _publish(self, name, payload):
            self.engine.events.publish(name, payload)

        def start(self, *_args):
            self.engine = SimpleNamespace(events=EventJournal(), frames=FakeFrames())
            self.fast_engine = SimpleNamespace(pipeline=SimpleNamespace(callback=None))
            self.review = object()
            return self.status()

        def status(self):
            return {"started": self.engine is not None}

        def close(self):
            self.engine = None

    fake_m254.M254DualPathController = FakeController
    fake_m254._server = SimpleNamespace(LiveController=FakeController, main=lambda: 0)
    sys.modules["m254_video_server"] = fake_m254
    try:
        server_path = Path(__file__).with_name("m333_video_server.py")
        spec = importlib.util.spec_from_file_location("m333_video_server_offline", server_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        controller = module.M333DualPathController(None)
        controller.start("fixture", 1)
        for sequence in range(4):
            controller.review.remember(sequence, frame(sequence))
        controller.fast_engine.pipeline.callback(fast(3, True))
        checks["isolated_web_callback_wired"] = (
            len(controller.engine.frames.values) == 4
            and controller.status()["semantic_terminal_monitor_error"] is None
        )
        controller.engine.events.publish("window_complete", {"sequences": [0, 1, 2, 3]})
        deadline = time.monotonic() + 2.0
        while controller.review.status()["active_task_id"] is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        checks["isolated_web_completion_releases"] = controller.review.status()["active_task_id"] is None
        controller.close()
    finally:
        sys.modules.pop("m254_video_server", None)

    source = Path(__file__).with_name("m333_review_bridge.py")
    server_source = Path(__file__).with_name("m333_video_server.py")
    result = {
        "gate": "M333-Web-review-loop-offline-contract",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "classification": "Offline scheduler and journal simulation only; no HTTP, detector, 4B forward, FPGA or KV260 deployment.",
        "candidate_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "candidate_web_wrapper_sha256": hashlib.sha256(server_source.read_bytes()).hexdigest(),
        "checks": checks,
        "stable_build_id": "0x4D395832",
        "stable_implementation_modified": False,
    }
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_text(encoding="utf-8") != json.dumps(result, indent=2, ensure_ascii=False) + "\n":
        raise FileExistsError(f"refusing to overwrite different result: {output}")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
