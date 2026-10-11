#!/usr/bin/env python3
"""Offline regression gate for the M218 background-thread event-loop failure."""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M222 = ROOT / "deployment/mage_vl4b/m222_realtime_vision_source"
M218 = ROOT / "deployment/mage_vl4b/m218_file_replay_source"
sys.path[:0] = [str(M222), str(M218)]

from m222_live_stream_core import M222ContinuousVideoEngine  # noqa: E402


class EventLoopRuntime:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.loop_seen = False
        self.closed = False

    def load(self) -> None:
        self.loop_seen = asyncio.get_event_loop() is not None
        if self.fail:
            raise RuntimeError("synthetic-load-failure")

    def stream(self, _request):
        return iter(())

    def close(self) -> None:
        self.closed = True


def wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise TimeoutError("M222 worker regression gate timed out")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    good_runtime = EventLoopRuntime()
    good = M222ContinuousVideoEngine(good_runtime, "test")
    good.start()
    wait_until(lambda: good.runtime_load_count == 1)
    ready = good.status()
    good.close()

    bad_runtime = EventLoopRuntime(fail=True)
    bad = M222ContinuousVideoEngine(bad_runtime, "test")
    bad.start()
    wait_until(lambda: bad.worker_error is not None)
    failed = bad.status()

    checks = {
        "event_loop_created_in_worker": good_runtime.loop_seen,
        "ready_state_visible": ready["service_state"] == "ready",
        "runtime_loaded_once": ready["runtime_load_count"] == 1,
        "worker_failure_visible": failed["service_state"] == "worker-failed",
        "worker_error_preserved": failed["worker_error"] == "RuntimeError: synthetic-load-failure",
        "failed_runtime_closed": bad_runtime.closed,
    }
    result = {
        "gate": "M222-live-worker-event-loop-regression",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "board_state_changed": False,
    }
    if args.result is not None:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_name(args.result.name + ".partial")
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
