#!/usr/bin/env python3
"""Offline M335 HTTP/SSE contract against a fake model; never a board PASS."""

from __future__ import annotations

import ast
from http import HTTPStatus
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
from urllib.parse import parse_qs, urlparse

import numpy as np

RELEASE = Path(__file__).resolve().parents[2]
CORE = RELEASE / "tmp/m223_realtime/m223_realtime_delta"
sys.path.insert(0, str(CORE))
from live_stream_core import EventJournal  # noqa: E402


class FakeFrames:
    def __init__(self):
        self.values = []

    def push(self, value):
        sequence = len(self.values)
        self.values.append(np.asarray(value).copy())
        return sequence


class FakeController:
    def __init__(self, runtime):
        self.runtime = runtime
        self.engine = None
        self.fast_engine = None
        self.review = None
        self._sequence = 0

    def _publish(self, name, payload):
        self.engine.events.publish(name, payload)

    def start(self, *_args, **_kwargs):
        self.engine = SimpleNamespace(events=EventJournal(), frames=FakeFrames(), runtime_load_count=1)
        self.fast_engine = SimpleNamespace(pipeline=SimpleNamespace(callback=None))
        return self.status()

    def submit(self, frame):
        sequence = self._sequence
        self._sequence += 1
        self.review.remember(sequence, frame)
        self.fast_engine.pipeline.callback({"window_index": sequence, "alarm": {"active": False}})
        self._publish("frame", {"sequence": sequence})
        return sequence

    def status(self):
        return {"started": self.engine is not None,
                "semantic_review": None if self.review is None else self.review.status()}

    def close(self):
        self.engine = None


def actual_handler():
    source = (CORE / "video_server.py").read_text(encoding="utf-8")
    node = next(item for item in ast.parse(source).body
                if isinstance(item, ast.ClassDef) and item.name == "Handler")
    namespace = {
        "BaseHTTPRequestHandler": BaseHTTPRequestHandler, "HTTPStatus": HTTPStatus,
        "json": json, "STATIC": CORE / "static", "urlparse": urlparse,
        "parse_qs": parse_qs, "FRAME_RGB_BYTES": 448 * 448 * 3,
        "LiveController": FakeController,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(CORE / "video_server.py"), "exec"), namespace)
    return namespace["Handler"]


def request(port, method, path, body=None, content_type=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {} if content_type is None else {"Content-Type": content_type}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    result = (response.status, json.loads(response.read()))
    connection.close()
    return result


def wait_until(predicate, seconds=2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def main():
    predecessor = ModuleType("m254_video_server")
    predecessor.__file__ = str(CORE / "m254_video_server_fake.py")
    predecessor.M254DualPathController = FakeController
    predecessor._server = SimpleNamespace(LiveController=FakeController,
                                          Handler=actual_handler(), main=lambda: 0,
                                          M120VideoRuntime=object)
    sys.modules["m254_video_server"] = predecessor
    m276 = ModuleType("m276_video_runtime")
    m276.M276ShortPromptBinaryRuntime = type("M276ShortPromptBinaryRuntime", (), {})
    sys.modules["m276_video_runtime"] = m276
    path = Path(__file__).with_name("m335_video_server.py")
    spec = importlib.util.spec_from_file_location("m335_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controller = module.M335DualPathController(SimpleNamespace(board=object()))

    class QuietHandler(module.M335Handler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    server.daemon_threads = True
    server.controller = controller
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    checks = {}
    try:
        status, body = request(port, "POST", "/api/4b/video/live/review")
        checks["model_not_ready_explicit"] = status == 503 and body["code"] == "MODEL_NOT_READY"
        status, body = request(port, "POST", "/api/4b/video/live/start",
                               json.dumps({"prompt": "fixture", "max_new_tokens": 1}).encode(), "application/json")
        checks["start"] = status == 202 and body["manual_review_available"]
        status, body = request(port, "POST", "/api/4b/video/live/review")
        checks["missing_frames_explicit"] = status == 409 and body["code"] == "MISSING_FRAMES"
        for sequence in range(4):
            frame = np.full((448, 448, 3), sequence, dtype=np.uint8)
            status, body = request(port, "POST", "/api/4b/video/live/frame",
                                   frame.tobytes(), "application/x-tellme-rgb448")
            checks[f"frame_{sequence}"] = status == 202 and body["sequence"] == sequence
        status, first = request(port, "POST", "/api/4b/video/live/review")
        checks["manual_first_active"] = (status == 202 and first["trigger"] == "manual"
                                         and first["source_sequences"] == [0, 1, 2, 3])
        for sequence in range(4, 6):
            frame = np.full((448, 448, 3), sequence, dtype=np.uint8)
            request(port, "POST", "/api/4b/video/live/frame",
                    frame.tobytes(), "application/x-tellme-rgb448")
        status, second = request(port, "POST", "/api/4b/video/live/review")
        checks["busy_latest_waiting"] = (status == 202 and second["state"] == "waiting"
                                         and second["source_sequences"] == [2, 3, 4, 5]
                                         and second["task_id"] != first["task_id"])
        journal = controller.engine.events
        journal.publish("token", {"window_sequences": [0, 1, 2, 3], "text": "0", "token_id": 15})
        journal.publish("complete", {"window_sequences": [0, 1, 2, 3], "proof": {"result": "PASS"}})
        journal.publish("window_complete", {"sequences": [0, 1, 2, 3]})
        checks["second_dispatch_after_first"] = wait_until(
            lambda: len(controller.engine.frames.values) == 8
            and controller.review.status()["active_task_id"] == second["task_id"])
        journal.publish("window_error", {"sequences": [4, 5, 6, 7], "error": "fixture failure"})
        checks["failure_releases"] = wait_until(
            lambda: controller.review.status()["active_task_id"] is None
            and controller.review.status()["semantic_reviews_failed"] == 1)
        status, third = request(port, "POST", "/api/4b/video/live/review")
        checks["retry_after_failure"] = status == 202 and third["task_id"] > second["task_id"]
        journal.publish("token", {"window_sequences": [8, 9, 10, 11], "text": "0", "token_id": 15})
        journal.publish("complete", {"window_sequences": [8, 9, 10, 11], "proof": {"result": "PASS"}})
        journal.publish("window_complete", {"sequences": [8, 9, 10, 11]})
        checks["recovered_completion"] = wait_until(
            lambda: controller.review.status()["semantic_reviews_completed"] == 2)
        events = journal.after(0)
        manual = [event for event in events if event["name"] == "semantic_review_queued"
                  and event["payload"].get("trigger") == "manual"]
        checks["three_manual_jobs_identified"] = [event["payload"]["task_id"] for event in manual] == [1, 2, 3]
        results = [event["payload"] for event in events if event["name"] == "semantic_review_result"]
        checks["result_bound_to_correct_tasks"] = [item["task_id"] for item in results] == [1, 3]
        checks["no_fake_auto_alarm"] = all(
            not event["payload"].get("alarm", {}).get("active")
            for event in events if event["name"] == "safety_result")
        checks["monitor_healthy"] = controller.status()["semantic_terminal_monitor_error"] is None
    finally:
        controller.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        sys.modules.pop("m254_video_server", None)
    from m335_review_bridge import AlarmReviewScheduler
    priority_events = []
    priority = AlarmReviewScheduler(
        lambda name, payload: priority_events.append((name, payload)),
        lambda _frames: (0, 1, 2, 3),
    )
    for sequence in range(4):
        priority.remember(sequence, np.full((448, 448, 3), sequence, dtype=np.uint8))
    priority.request_manual_review()
    priority.remember(4, np.full((448, 448, 3), 4, dtype=np.uint8))
    priority.request_manual_review()
    priority.remember(5, np.full((448, 448, 3), 5, dtype=np.uint8))
    priority.on_fast_result({"window_index": 5, "alarm": {"active": True}})
    checks["auto_alarm_replaces_waiting_manual"] = (
        priority.status()["waiting_trigger"] == "auto"
        and any(name == "semantic_review_superseded" and payload["task_id"] == 2
                for name, payload in priority_events)
    )
    try:
        priority.request_manual_review()
    except RuntimeError as error:
        checks["manual_cannot_displace_auto_alarm"] = "AUTO_ALARM_WAITING" in str(error)
    else:
        checks["manual_cannot_displace_auto_alarm"] = False
    print(json.dumps({"gate": "M335-manual-HTTP-fake-model", "status": "PASS" if all(checks.values()) else "FAIL",
                      "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
