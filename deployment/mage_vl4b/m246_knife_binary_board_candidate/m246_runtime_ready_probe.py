#!/usr/bin/env python3
"""Start the M246 no-frame session and prove exact constrained runtime identity."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from m246_knife_binary import KNIFE_PROMPT


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


parser = argparse.ArgumentParser()
parser.add_argument("--manifest-sha256", required=True)
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--result", type=Path, required=True)
parser.add_argument("--timeout-seconds", type=float, default=180.0)
args = parser.parse_args()
started_at = time.monotonic()
history = []
started = None
final = None
error = None
status = "FAIL"
try:
    listen_deadline = time.monotonic() + 30.0
    while True:
        try:
            initial = request_json("http://127.0.0.1:8001/api/4b/video/live/status")
            break
        except urllib.error.URLError:
            if time.monotonic() >= listen_deadline:
                raise TimeoutError("M246 HTTP listen timeout")
            time.sleep(0.5)
    if initial.get("status") != "idle":
        raise RuntimeError(f"M246 initial service not idle: {initial}")
    started = request_json(
        "http://127.0.0.1:8001/api/4b/video/live/start",
        "POST",
        {
            "prompt": KNIFE_PROMPT,
            "max_new_tokens": 1,
            "source_mode": "browser-camera",
            "source_label": "M246-no-frame-runtime-ready",
        },
    )
    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        final = request_json("http://127.0.0.1:8001/api/4b/video/live/status")
        sample = {
            "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
            "service_state": final.get("service_state"),
            "runtime_load_count": final.get("runtime_load_count"),
            "worker_alive": final.get("worker_alive"),
            "worker_error": final.get("worker_error"),
            "web_runtime_class": final.get("web_runtime_class"),
            "web_board_runtime_class": final.get("web_board_runtime_class"),
            "web_language_model_class": final.get("web_language_model_class"),
            "knife_classifier": final.get("knife_classifier"),
            "knife_alarm_state": final.get("knife_alarm_state"),
        }
        history.append(sample)
        print("M246_STATUS " + json.dumps(sample, ensure_ascii=False), flush=True)
        if final.get("worker_error"):
            raise RuntimeError(str(final["worker_error"]))
        if (
            final.get("service_state") == "ready"
            and final.get("worker_alive") is True
            and final.get("runtime_load_count") == 1
            and final.get("web_runtime_class") == "M246KnifeVideoRuntime"
            and final.get("web_board_runtime_class") == "M238PrefillRuntime"
            and final.get("web_language_model_class") == "M241VideoLanguageModel"
            and final.get("knife_classifier") == "M246-constrained-token-15-vs-16"
            and final.get("knife_thresholds_calibrated") is False
            and final.get("knife_alarm_state") == "REVIEW"
            and final.get("windows_started") == 0
            and final.get("buffer", {}).get("accepted_frames") == 0
            and final.get("t64_used") is False
        ):
            status = "PASS"
            break
        time.sleep(5.0)
    else:
        raise TimeoutError("M246 runtime-ready timeout")
except (OSError, ValueError, RuntimeError, TimeoutError, urllib.error.URLError) as exc:
    error = f"{type(exc).__name__}: {exc}"

result = {
    "date": "2026-09-02",
    "gate": "M246-real-KV260-constrained-knife-runtime-ready-no-frame",
    "status": status,
    "classification": (
        "Real-KV260 constrained knife-runtime identity and no-frame worker readiness only; "
        "not a fixed-window, knife-accuracy, calibrated-threshold, latency, continuous-video, "
        "T64, or real-time PASS."
    ),
    "package_manifest_sha256": args.manifest_sha256,
    "service_pid": args.pid,
    "prompt": KNIFE_PROMPT,
    "started": started,
    "final": final,
    "history": history,
    "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
    "frames_submitted": 0,
    "error": error,
    "stable_rollback_preserved": True,
    "next_gate": "Run the same deterministic four-frame gate through M246 and require a 0/1 knife observation plus complete FPGA proof.",
}
atomic_json(args.result, result)
print("__M246_BOARD_RESULT_BEGIN__", flush=True)
print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
print("__M246_BOARD_RESULT_END__", flush=True)
print("M246_RUNTIME_READY_PASS" if status == "PASS" else "M246_RUNTIME_READY_FAIL", flush=True)
raise SystemExit(0 if status == "PASS" else 1)
