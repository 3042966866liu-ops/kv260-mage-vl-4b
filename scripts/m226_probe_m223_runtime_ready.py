#!/usr/bin/env python3
"""Start one M223 session and fail closed on the worker-ready contract."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def request_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    raw = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=raw, method=method)
    if raw is not None:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(request, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://192.168.0.2:8001")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    started_at = time.monotonic()
    history: list[dict] = []
    status = "FAIL"
    error = None
    started = None
    final = None
    try:
        initial = request_json(base + "/api/4b/video/live/status")
        if initial.get("status") == "idle":
            started = request_json(
                base + "/api/4b/video/live/start",
                "POST",
                {
                    "prompt": "请描述当前四帧中最重要的物体、动作和变化。",
                    "max_new_tokens": 1,
                    "source_mode": "browser-camera",
                    "source_label": "M226-no-frames",
                },
            )
        deadline = time.monotonic() + args.timeout_seconds
        while time.monotonic() < deadline:
            final = request_json(base + "/api/4b/video/live/status")
            sample = {
                "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
                "service_state": final.get("service_state"),
                "worker_alive": final.get("worker_alive"),
                "worker_error": final.get("worker_error"),
                "runtime_load_count": final.get("runtime_load_count"),
                "board_runtime_loaded": final.get("board_runtime_loaded"),
                "windows_started": final.get("windows_started"),
            }
            if not history or sample != {**history[-1], "elapsed_ms": sample["elapsed_ms"]}:
                history.append(sample)
                print("M226_STATUS " + json.dumps(sample, ensure_ascii=False), flush=True)
            if final.get("service_state") == "worker-failed" or final.get("worker_error"):
                raise RuntimeError(str(final.get("worker_error") or "worker-failed"))
            if (
                final.get("service_state") == "ready"
                and final.get("worker_alive") is True
                and final.get("runtime_load_count") == 1
                and final.get("board_runtime_loaded") is True
                and final.get("windows_started") == 0
            ):
                status = "PASS"
                break
            time.sleep(5.0)
        else:
            raise TimeoutError("M223 runtime-ready gate timed out")
    except (OSError, ValueError, RuntimeError, TimeoutError, urllib.error.URLError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    result = {
        "date": "2026-09-01",
        "gate": "M226-real-KV260-M223-runtime-ready-no-frame",
        "status": status,
        "classification": (
            "Real-KV260 M223 runtime-load and live-worker readiness only; no frame was "
            "submitted and no complete-window, FPGA E2E, latency or seconds-level claim is made."
        ),
        "base_url": base,
        "started": started,
        "final": final,
        "history": history,
        "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
        "error": error,
        "frames_submitted": 0,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Submit exactly four fixed reference frames, preserve all stage timings and "
            "numerical evidence, and compare complete-window time against the 5000 ms target."
        ),
    }
    atomic_json(args.result, result)
    print("M226_M223_RUNTIME_READY_PASS" if status == "PASS" else "M226_M223_RUNTIME_READY_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
