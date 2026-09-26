#!/usr/bin/env python3
"""No-frame runtime-ready proof for the M243 Web integration."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


def request_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    raw = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=raw, method=method)
    if raw is not None:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(request, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://127.0.0.1:8001")
parser.add_argument("--manifest-sha256", required=True)
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--result", type=Path, required=True)
parser.add_argument("--timeout-seconds", type=float, default=180.0)
args = parser.parse_args()
started_at = time.monotonic()
history = []
error = None
started = None
final = None
status = "FAIL"
try:
    base = args.base_url.rstrip("/")
    initial = None
    listen_deadline = time.monotonic() + 30.0
    while time.monotonic() < listen_deadline:
        try:
            initial = request_json(base + "/api/4b/video/live/status")
            break
        except OSError:
            time.sleep(1.0)
    if initial is None:
        raise TimeoutError("M243 HTTP service did not begin listening")
    if initial.get("status") != "idle":
        raise RuntimeError(f"M243 expected idle service, got {initial.get('status')}")
    started = request_json(
        base + "/api/4b/video/live/start",
        "POST",
        {
            "prompt": "请判断监控画面中人物的工作状态；如出现刀具请立即报警。",
            "max_new_tokens": 1,
            "source_mode": "browser-camera",
            "source_label": "M243-no-frame-runtime-ready",
        },
    )
    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        final = request_json(base + "/api/4b/video/live/status")
        sample = {
            "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
            "service_state": final.get("service_state"),
            "runtime_load_count": final.get("runtime_load_count"),
            "worker_alive": final.get("worker_alive"),
            "worker_error": final.get("worker_error"),
            "board_runtime_loaded": final.get("board_runtime_loaded"),
            "windows_started": final.get("windows_started"),
            "web_language_runtime": final.get("web_language_runtime"),
            "web_prefill_attention": final.get("web_prefill_attention"),
            "web_runtime_class": final.get("web_runtime_class"),
            "web_board_runtime_class": final.get("web_board_runtime_class"),
            "web_language_model_class": final.get("web_language_model_class"),
        }
        history.append(sample)
        if final.get("worker_error"):
            raise RuntimeError(str(final["worker_error"]))
        if (
            final.get("service_state") == "ready"
            and final.get("runtime_load_count") == 1
            and final.get("worker_alive") is True
            and final.get("board_runtime_loaded") is True
            and final.get("windows_started") == 0
            and final.get("web_language_runtime") == "M243-M238-T32-pack-prefetch-fused-parse"
            and final.get("web_prefill_attention") == "M241-grouped-GQA-reference-RoPE"
            and final.get("web_runtime_class") == "M243VideoRuntime"
            and final.get("web_board_runtime_class") == "M238PrefillRuntime"
            and final.get("web_language_model_class") == "M241VideoLanguageModel"
            and final.get("web_prefill_hash_locked") is True
            and final.get("t64_used") is False
        ):
            status = "PASS"
            break
        time.sleep(5.0)
    else:
        raise TimeoutError("M243 runtime-ready gate timed out")
except Exception as exc:
    error = f"{type(exc).__name__}: {exc}"

value = {
    "date": "2026-09-02",
    "gate": "M243-real-KV260-hash-locked-Web-Prefill-runtime-ready-no-frame",
    "status": status,
    "classification": "Real-KV260 M238/M241 Web-runtime selection and no-frame worker readiness only; no visual window, latency, semantic, continuous-video, T64, or real-time PASS.",
    "package_manifest_sha256": args.manifest_sha256,
    "service_pid": args.pid,
    "started": started,
    "final": final,
    "history": history,
    "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
    "frames_submitted": 0,
    "error": error,
    "stable_rollback_preserved": True,
    "next_gate": "Run one exact fixed four-frame input through this hash-locked Web runtime; preserve numerical and stage timing evidence before continuous video.",
}
args.result.parent.mkdir(parents=True, exist_ok=True)
partial = args.result.with_name(args.result.name + ".partial")
partial.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
os.replace(partial, args.result)
print("__M243_BOARD_RESULT_BEGIN__")
print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
print("__M243_BOARD_RESULT_END__")
print("M243_WEB_PREFILL_RUNTIME_READY_PASS" if status == "PASS" else "M243_WEB_PREFILL_RUNTIME_READY_FAIL")
raise SystemExit(0 if status == "PASS" else 1)
