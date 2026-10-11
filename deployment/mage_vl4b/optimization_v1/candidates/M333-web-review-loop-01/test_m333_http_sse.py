#!/usr/bin/env python3
"""Exercise the unchanged HTTP Handler with a fake M333 runtime; no board use."""

from __future__ import annotations

import argparse
import ast
import hashlib
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

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "tmp/m223_realtime/m223_realtime_delta/live_stream_core.py").is_file())
CORE = ROOT / "tmp/m223_realtime/m223_realtime_delta"
SERVER_SOURCE = CORE / "video_server.py"
sys.path.insert(0, str(CORE))
from live_stream_core import EventJournal  # noqa: E402


class FakeFrames:
    def __init__(self):
        self.values = []

    def push(self, frame):
        sequence = len(self.values)
        self.values.append(np.asarray(frame).copy())
        return sequence


class FakeController:
    def __init__(self, _runtime):
        self.engine = None
        self.fast_engine = None
        self.review = None
        self._sequence = 0

    def _publish(self, name, payload):
        self.engine.events.publish(name, payload)

    def start(self, *_args, **_kwargs):
        self.engine = SimpleNamespace(events=EventJournal(), frames=FakeFrames())
        self.fast_engine = SimpleNamespace(pipeline=SimpleNamespace(callback=None))
        return self.status()

    def submit(self, frame):
        sequence = self._sequence
        self._sequence += 1
        self.review.remember(sequence, frame)
        self.fast_engine.pipeline.callback({
            "window_index": sequence,
            "alarm": {"active": sequence in (3, 5)},
        })
        self._publish("frame", {"sequence": sequence})
        return sequence

    def status(self):
        return {
            "started": self.engine is not None,
            "semantic_review": None if self.review is None else self.review.status(),
        }

    def close(self):
        self.engine = None


def load_candidate():
    predecessor = ModuleType("m254_video_server")
    predecessor.M254DualPathController = FakeController
    predecessor._server = SimpleNamespace(LiveController=FakeController, main=lambda: 0)
    sys.modules["m254_video_server"] = predecessor
    path = Path(__file__).with_name("m333_video_server.py")
    spec = importlib.util.spec_from_file_location("m333_http_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.M333DualPathController


def load_real_handler():
    # Compile the actual, unedited Handler class without importing its board-only
    # module dependencies. This is an HTTP protocol integration test, not a model test.
    source = SERVER_SOURCE.read_text(encoding="utf-8")
    handler = next(node for node in ast.parse(source).body
                   if isinstance(node, ast.ClassDef) and node.name == "Handler")
    namespace = {
        "BaseHTTPRequestHandler": BaseHTTPRequestHandler,
        "HTTPStatus": HTTPStatus,
        "HTTPConnection": HTTPConnection,
        "json": json,
        "STATIC": CORE / "static",
        "urlparse": urlparse,
        "parse_qs": parse_qs,
        "FRAME_RGB_BYTES": 448 * 448 * 3,
        "LiveController": FakeController,
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(SERVER_SOURCE), "exec"), namespace)
    return namespace["Handler"]


def request(port, method, path, body=None, content_type=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {} if content_type is None else {"Content-Type": content_type}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    status = response.status
    connection.close()
    return status, json.loads(raw)


def wait_until(predicate, seconds=2):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    Candidate = load_candidate()
    controller = Candidate(None)
    Handler = load_real_handler()

    class QuietHandler(Handler):
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
        status, body = request(port, "POST", "/api/4b/video/live/start",
                               json.dumps({"prompt": "fixture", "max_new_tokens": 1}).encode(),
                               "application/json")
        checks["http_start_accepted"] = status == 202 and body["started"]
        for sequence in range(6):
            frame = np.full((448, 448, 3), sequence, dtype=np.uint8)
            status, body = request(port, "POST", "/api/4b/video/live/frame",
                                   frame.tobytes(), "application/x-tellme-rgb448")
            checks[f"http_frame_{sequence}"] = status == 202 and body["sequence"] == sequence
        review = controller.review
        checks["first_active_second_waiting"] = (
            review.status()["active_source_sequences"] == [0, 1, 2, 3]
            and review.status()["waiting_source_sequences"] == [2, 3, 4, 5]
        )
        controller.engine.events.publish("window_complete", {"sequences": [0, 1, 2, 3]})
        checks["second_dispatched_after_first_completion"] = wait_until(
            lambda: len(controller.engine.frames.values) == 8
            and review.status()["active_source_sequences"] == [2, 3, 4, 5]
        )
        controller.engine.events.publish("window_complete", {"sequences": [4, 5, 6, 7]})
        checks["second_completion_releases_capacity"] = wait_until(
            lambda: review.status()["semantic_reviews_completed"] == 2
            and review.status()["active_task_id"] is None
        )
        status, body = request(port, "GET", "/api/4b/video/live/status")
        checks["http_status_two_reviews"] = (
            status == 200 and body["semantic_review"]["semantic_reviews_completed"] == 2
        )
        connection = HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/api/4b/video/live/events?after=0")
        response = connection.getresponse()
        sse_names = []
        try:
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline and len(sse_names) < len(controller.engine.events.after(0)):
                line = response.fp.readline().decode("utf-8")
                if line.startswith("event: "):
                    sse_names.append(line[7:].strip())
        finally:
            connection.close()
        checks["sse_two_review_cycles"] = (
            response.status == 200
            and sse_names.count("safety_result") == 6
            and sse_names.count("semantic_review_queued") == 2
            and sse_names.count("semantic_review_released") == 2
            and sse_names.count("window_complete") == 2
        )
        checks["terminal_monitor_healthy"] = controller.status()["semantic_terminal_monitor_error"] is None
    finally:
        controller.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        sys.modules.pop("m254_video_server", None)
    result = {
        "gate": "M333-real-handler-fake-runtime-HTTP-SSE",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "classification": "Real unedited HTTP Handler class with fake detector/model; no board, 4B forward or FPGA execution.",
        "real_handler_sha256": hashlib.sha256(SERVER_SOURCE.read_bytes()).hexdigest(),
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
