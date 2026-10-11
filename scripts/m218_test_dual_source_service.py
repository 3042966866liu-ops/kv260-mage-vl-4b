#!/usr/bin/env python3
"""Offline HTTP/SSE, dual-source, latest-only and local MP4 contract gate."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import struct
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m218_file_replay_source"
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mp4_probe(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 16 or data[4:8] != b"ftyp":
        raise RuntimeError("selected video is not an ISO BMFF/MP4 file")
    codec = "avc1" if b"avc1" in data else ("avc3" if b"avc3" in data else "unknown")
    duration_seconds = None
    marker = data.find(b"mvhd")
    if marker >= 0 and marker + 24 <= len(data):
        payload = marker + 4
        version = data[payload]
        if version == 0 and payload + 20 <= len(data):
            timescale, duration = struct.unpack_from(">II", data, payload + 12)
        elif version == 1 and payload + 32 <= len(data):
            timescale = struct.unpack_from(">I", data, payload + 20)[0]
            duration = struct.unpack_from(">Q", data, payload + 24)[0]
        else:
            timescale = duration = 0
        if timescale:
            duration_seconds = duration / timescale
    return {
        "path": str(path),
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha(path),
        "container": "MP4/ISO-BMFF",
        "video_sample_entry": codec,
        "h264_marker_present": codec in ("avc1", "avc3"),
        "duration_seconds": duration_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    video_evidence = mp4_probe(args.video)
    runtime = FakeRuntime()
    controller = LiveController(runtime)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.controller = controller
    port = server.server_address[1]
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        start_body = json.dumps({
            "prompt": "持续分析本地视频回放",
            "max_new_tokens": 1,
            "source_mode": "uploaded-file-loop",
            "source_label": args.video.name,
        }, ensure_ascii=False).encode("utf-8")
        status, started = request(
            port, "POST", "/api/4b/video/live/start", start_body, "application/json"
        )
        if status != 202 or started["mode"] != "continuous-latest-only":
            raise RuntimeError("M218 file replay start contract failed")
        for sequence in range(64):
            frame = np.full((448, 448, 3), sequence, dtype=np.uint8)
            status, accepted = request(
                port,
                "POST",
                "/api/4b/video/live/frame",
                frame.tobytes(),
                "application/x-tellme-rgb448",
            )
            if status != 202 or accepted["sequence"] != sequence:
                raise RuntimeError(f"M218 frame {sequence} acceptance failed")
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            _, snapshot = request(port, "GET", "/api/4b/video/live/status")
            if snapshot["windows_completed"] >= 2 and snapshot["last_completed_newest_sequence"] == 63:
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("M218 latest-only worker did not converge to newest frame")

        sse = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        sse.request("GET", "/api/4b/video/live/events?after=0")
        response = sse.getresponse()
        if response.status != 200 or response.getheader("Content-Type") != "text/event-stream; charset=utf-8":
            raise RuntimeError("M218 SSE response contract failed")
        sse_prefix = b"".join(response.readline() for _ in range(4))
        sse.close()

        app = (SOURCE / "static/app.js").read_text(encoding="utf-8")
        html = (SOURCE / "static/index.html").read_text(encoding="utf-8")
        names = [item["name"] for item in controller.engine.events.after(0)]
        checks = {
            "http_start_accepted": True,
            "camera_mode_retained": "getUserMedia" in app and "browser-camera" in app,
            "file_picker_accepts_video": 'type="file"' in html and 'accept="video/mp4,video/*"' in html,
            "browser_local_object_url": "URL.createObjectURL(file)" in app,
            "file_loop_enabled": "video.loop=true" in app.replace(" ", ""),
            "file_source_mode_exact": snapshot["source_mode"] == "uploaded-file-loop",
            "file_source_label_exact": snapshot["source_label"] == args.video.name,
            "finite_content_declared": snapshot["source_content_is_finite"] is True,
            "continuous_delivery_contract": snapshot["source_is_unbounded"] is True,
            "no_whole_video_upload": "FormData" not in app and "/upload" not in app,
            "raw_rgb_frame_endpoint_retained": "/api/4b/video/live/frame" in app,
            "fixed_ring_capacity_16": snapshot["buffer"]["capacity"] == 16,
            "all_64_frames_accepted": snapshot["buffer"]["accepted_frames"] == 64,
            "old_frames_overwritten": snapshot["buffer"]["overwritten_frames"] == 48,
            "latest_window_completed": snapshot["last_completed_newest_sequence"] == 63,
            "runtime_loaded_once": runtime.load_count == 1 and snapshot["runtime_load_count"] == 1,
            "no_window_backlog": snapshot["window_backlog_capacity"] == 1,
            "sse_stage_event_present": "stage" in names,
            "sse_token_event_present": "token" in names,
            "sse_fpga_complete_event_present": "complete" in names,
            "http_sse_endpoint_streamed": b"event:" in sse_prefix and b"data:" in sse_prefix,
            "actual_mp4_h264_marker": video_evidence["h264_marker_present"],
        }
        result = {
            "date": "2026-09-01",
            "gate": "M218-dual-source-local-file-replay-HTTP-SSE-offline-contract",
            "status": "PASS" if all(checks.values()) else "FAIL",
            "classification": "Offline dual-source UI/server contract, actual local MP4 identity, and FakeRuntime latest-only pressure proof; not browser decode, camera permission, KV260 inference, public frame transmission, FPGA complete window, or latency acceptance.",
            "input_semantics": {
                "browser-camera": "unbounded real-world live source",
                "uploaded-file-loop": "finite local content decoded and looped by the browser into a continuing frame source",
            },
            "video_evidence": video_evidence,
            "checks": checks,
            "snapshot": snapshot,
            "event_names": names,
            "source_files": {
                str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                for path in sorted(SOURCE.rglob("*")) if path.is_file()
            },
            "board_state_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "Build a clean M218 delta, restart only the transient M212 HTTP service over COM3, verify local/public control plane, then obtain action-time confirmation before selecting the local video in a browser and transmitting sampled frames.",
        }
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_name(args.result.name + ".partial")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, args.result)
        print("M218_DUAL_SOURCE_OFFLINE_PASS" if result["status"] == "PASS" else "M218_DUAL_SOURCE_OFFLINE_FAIL")
        return 0 if result["status"] == "PASS" else 1
    finally:
        controller.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5.0)


if __name__ == "__main__":
    raise SystemExit(main())
