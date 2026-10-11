#!/usr/bin/env python3
"""Offline HTTP and scheduling gate for the M212 latest-only service."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m212_live_stream_source"
BASE = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
sys.dont_write_bytecode = True
sys.path[:0] = [str(SOURCE), str(BASE)]

from video_server import Handler, LiveController  # noqa: E402


class FakeRuntime:
    def __init__(self):
        self.load_count = 0
        self.stream_count = 0
        self.close_count = 0
        self.board = None
        self.callback = None

    def set_progress_callback(self, callback) -> None:
        self.callback = callback

    def load(self) -> None:
        self.load_count += 1
        self.board = object()

    def stream(self, request):
        self.stream_count += 1
        assert request.frames_rgb_u8.shape == (4, 448, 448, 3)
        assert request.frames_rgb_u8.dtype == np.uint8
        yield "stage", {"name": "vision", "label": "fake vision"}
        if self.callback:
            self.callback("vision_layer_begin", {"index": 0, "total_layers": 24})
        time.sleep(0.04)
        yield "token", {"text": "测", "token_id": 1, "generated_tokens": 1}
        yield "complete", {
            "status": "PASS",
            "generated_tokens": 1,
            "proof": {"result": "PASS", "build_id": "0x4D395832"},
        }

    def close(self) -> None:
        self.close_count += 1


def request(port: int, method: str, path: str, body: bytes = b"", content_type: str = ""):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Length": str(len(body))}
    if content_type:
        headers["Content-Type"] = content_type
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    status = response.status
    connection.close()
    return status, json.loads(payload) if payload else None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    runtime = FakeRuntime()
    controller = LiveController(runtime)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.controller = controller
    port = server.server_address[1]
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        start_body = json.dumps({"prompt": "持续视频测试", "max_new_tokens": 1}).encode()
        status, started = request(port, "POST", "/api/4b/video/live/start", start_body, "application/json")
        if status != 202 or started["mode"] != "continuous-latest-only":
            raise RuntimeError("M212 live start contract failed")
        for sequence in range(64):
            frame = np.full((448, 448, 3), sequence, dtype=np.uint8)
            status, accepted = request(
                port, "POST", "/api/4b/video/live/frame", frame.tobytes(),
                "application/x-tellme-rgb448",
            )
            if status != 202 or accepted["sequence"] != sequence:
                raise RuntimeError(f"M212 frame {sequence} acceptance failed")
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            status, snapshot = request(port, "GET", "/api/4b/video/live/status")
            if snapshot["windows_completed"] >= 2 and snapshot["last_completed_newest_sequence"] == 63:
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("M212 latest-only worker did not converge to the newest frame")

        sse = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        sse.request("GET", "/api/4b/video/live/events?after=0")
        response = sse.getresponse()
        if response.status != 200 or response.getheader("Content-Type") != "text/event-stream; charset=utf-8":
            raise RuntimeError("M212 SSE response contract failed")
        sse_prefix = b"".join(response.readline() for _ in range(4))
        sse.close()

        events = controller.engine.events.after(0)
        names = [item["name"] for item in events]
        checks = {
            "http_start_accepted": True,
            "unbounded_source_contract": snapshot["source_is_unbounded"] is True,
            "fixed_ring_capacity_16": snapshot["buffer"]["capacity"] == 16,
            "all_64_frames_accepted": snapshot["buffer"]["accepted_frames"] == 64,
            "old_frames_overwritten": snapshot["buffer"]["overwritten_frames"] == 48,
            "latest_window_completed": snapshot["last_completed_newest_sequence"] == 63,
            "runtime_loaded_once": runtime.load_count == 1 and snapshot["runtime_load_count"] == 1,
            "no_window_backlog": snapshot["window_backlog_capacity"] == 1,
            "sse_stage_event_present": "stage" in names,
            "sse_layer_event_present": "vision_layer_begin" in names,
            "sse_token_event_present": "token" in names,
            "sse_fpga_complete_event_present": "complete" in names,
            "sse_window_complete_present": "window_complete" in names,
            "http_sse_endpoint_streamed": b"event:" in sse_prefix and b"data:" in sse_prefix,
        }
        result = {
            "date": "2026-09-01",
            "gate": "M212-latest-only-live-HTTP-SSE-offline-contract",
            "status": "PASS" if all(checks.values()) else "FAIL",
            "classification": "Offline HTTP/SSE/latest-only pressure proof with FakeRuntime; not camera permission, KV260 inference, public Web or latency acceptance.",
            "checks": checks,
            "snapshot": snapshot,
            "event_names": names,
            "source_files": {
                str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                for path in sorted(SOURCE.rglob("*")) if path.is_file()
            },
            "board_state_changed": False,
            "next_gate": "Build a clean M212 delta and run one bounded real-KV260 latest-only live smoke over COM3; keep M202 as rollback.",
        }
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_name(args.result.name + ".partial")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, args.result)
        print("M212_LIVE_SERVICE_OFFLINE_PASS" if result["status"] == "PASS" else "M212_LIVE_SERVICE_OFFLINE_FAIL")
        return 0 if result["status"] == "PASS" else 1
    finally:
        controller.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5.0)


if __name__ == "__main__":
    raise SystemExit(main())
