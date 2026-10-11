#!/usr/bin/env python3
"""Deterministic pressure test for the M209 latest-only stream core."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from m209_live_stream_core import ContinuousVideoEngine


class FakeRuntime:
    def __init__(self):
        self.load_count = 0
        self.close_count = 0
        self.calls = 0

    def load(self):
        self.load_count += 1

    def stream(self, request):
        self.calls += 1
        time.sleep(0.12)
        newest_marker = int(request.frames_rgb_u8[-1, 0, 0, 0])
        yield "stage", {"name": "vision", "marker": newest_marker}
        yield "token", {"text": str(newest_marker), "token_id": newest_marker}
        yield "complete", {"status": "PASS", "generated_tokens": 1}

    def close(self):
        self.close_count += 1


def frame(index: int) -> np.ndarray:
    value = np.empty((448, 448, 3), dtype=np.uint8)
    value.fill(index & 255)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    runtime = FakeRuntime()
    engine = ContinuousVideoEngine(
        runtime,
        prompt="continuous stream test",
        max_new_tokens=1,
        buffer_capacity=16,
        window_size=4,
    )
    engine.start()
    for index in range(64):
        engine.submit(frame(index), captured_monotonic=time.monotonic())
        time.sleep(0.005)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and engine.last_completed_newest_sequence != 63:
        time.sleep(0.02)
    status = engine.status()
    events = engine.events.after(0)
    engine.close()
    checks = {
        "runtime_loaded_once": runtime.load_count == 1,
        "runtime_closed_once": runtime.close_count == 1,
        "all_frames_received": status["buffer"]["accepted_frames"] == 64,
        "buffer_is_bounded": status["buffer"]["depth"] <= 16,
        "old_frames_were_overwritten": status["buffer"]["overwritten_frames"] > 0,
        "latest_window_completed": status["last_completed_newest_sequence"] == 63,
        "latest_window_geometry": status["last_window_sequences"] == [60, 61, 62, 63],
        "no_window_backlog": status["window_backlog_capacity"] == 1,
        "input_outpaced_inference": runtime.calls < 16,
        "continuous_events_emitted": any(event["name"] == "window_complete" for event in events),
    }
    result = {
        "gate": "M209-continuous-latest-only-ring-buffer-pressure",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "final_status": status,
        "runtime_calls": runtime.calls,
        "event_count": len(events),
        "classification": (
            "Offline scheduler pressure proof only; no camera/RTSP, KV260 inference, "
            "HTTP/SSE or latency acceptance is claimed."
        ),
    }
    if args.result is not None:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_name(args.result.name + ".partial")
        temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temporary, args.result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("M209_LIVE_STREAM_CORE_PASS" if result["status"] == "PASS" else "M209_LIVE_STREAM_CORE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
