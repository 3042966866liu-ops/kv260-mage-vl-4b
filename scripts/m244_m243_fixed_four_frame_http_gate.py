#!/usr/bin/env python3
"""Run one deterministic four-frame window through the active M243 Web runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np


BUILD_ID = "0x4d395832"
RUNTIME_CLASS = "M243VideoRuntime"
BOARD_RUNTIME_CLASS = "M238PrefillRuntime"
LANGUAGE_MODEL_CLASS = "M241VideoLanguageModel"


def request_json(url: str, method: str = "GET", body: bytes | None = None,
                 content_type: str | None = None) -> dict:
    request = urllib.request.Request(url, data=body, method=method)
    if content_type:
        request.add_header("Content-Type", content_type)
    with urllib.request.urlopen(request, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def fixed_frames() -> np.ndarray:
    y, x = np.indices((448, 448), dtype=np.uint16)
    frames = []
    for index in range(4):
        red = (x + 29 * index) & 255
        green = (y + 47 * index) & 255
        blue = (x // 2 + y // 3 + 61 * index) & 255
        frames.append(np.stack((red, green, blue), axis=-1).astype(np.uint8))
    return np.stack(frames, axis=0)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://192.168.0.2:8001")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    parser.add_argument("--target-window-ms", type=float, default=5000.0)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    started_at = time.monotonic()
    events: list[dict] = []
    event_error: list[str] = []
    terminal_event = threading.Event()
    initial = None
    final = None
    submitted: list[dict] = []
    error = None

    def read_sse() -> None:
        current_name = None
        current_data = None
        try:
            with urllib.request.urlopen(
                base + "/api/4b/video/live/events?after=0",
                timeout=args.timeout_seconds + 60.0,
            ) as response:
                for raw in response:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if line.startswith("event: "):
                        current_name = line[7:]
                    elif line.startswith("data: "):
                        current_data = json.loads(line[6:])
                    elif not line and current_name is not None and current_data is not None:
                        item = {"event": current_name, "payload": current_data}
                        events.append(item)
                        if current_name in {
                            "window_begin", "stage", "vision_layer_begin",
                            "vision_layer_pass", "vision_heartbeat", "token",
                            "complete", "window_complete", "window_error",
                        }:
                            print("M244_EVENT " + json.dumps(item, ensure_ascii=False), flush=True)
                        if current_name in {"window_complete", "window_error"}:
                            terminal_event.set()
                            return
                        current_name = None
                        current_data = None
        except BaseException as exc:
            event_error.append(f"{type(exc).__name__}: {exc}")
            terminal_event.set()

    try:
        initial = request_json(base + "/api/4b/video/live/status")
        exact_ready = (
            initial.get("service_state") == "ready"
            and initial.get("worker_alive") is True
            and initial.get("runtime_load_count") == 1
            and initial.get("windows_started") == 0
            and initial.get("windows_completed") == 0
            and initial.get("buffer", {}).get("accepted_frames") == 0
            and initial.get("web_runtime_class") == RUNTIME_CLASS
            and initial.get("web_board_runtime_class") == BOARD_RUNTIME_CLASS
            and initial.get("web_language_model_class") == LANGUAGE_MODEL_CLASS
            and initial.get("web_prefill_hash_locked") is True
            and initial.get("t64_used") is False
            and str(initial.get("build_id", "")).lower() == BUILD_ID
        )
        if not exact_ready:
            raise RuntimeError(f"M244 initial M243 identity/readiness mismatch: {initial}")

        sse = threading.Thread(target=read_sse, name="m244-sse", daemon=True)
        sse.start()
        frames = fixed_frames()
        frames_sha256 = hashlib.sha256(frames.tobytes()).hexdigest()
        for index, frame in enumerate(frames):
            response = request_json(
                base + "/api/4b/video/live/frame",
                "POST",
                frame.tobytes(),
                "application/x-tellme-rgb448",
            )
            if response.get("accepted") is not True or response.get("sequence") != index:
                raise RuntimeError(f"M244 frame {index} acceptance mismatch: {response}")
            submitted.append(response)

        deadline = time.monotonic() + args.timeout_seconds
        next_heartbeat = 0.0
        while time.monotonic() < deadline:
            final = request_json(base + "/api/4b/video/live/status")
            elapsed = time.monotonic() - started_at
            if elapsed >= next_heartbeat:
                print("M244_HEARTBEAT " + json.dumps({
                    "elapsed_s": elapsed,
                    "windows_started": final.get("windows_started"),
                    "windows_completed": final.get("windows_completed"),
                    "inference_busy": final.get("inference_busy"),
                    "last_window_sequences": final.get("last_window_sequences"),
                }, ensure_ascii=False), flush=True)
                next_heartbeat = elapsed + 30.0
            if terminal_event.is_set():
                break
            time.sleep(5.0)
        else:
            raise TimeoutError("M244 complete-window timeout")
        sse.join(timeout=5.0)
        if event_error:
            raise RuntimeError("SSE failure: " + event_error[-1])
    except (OSError, ValueError, RuntimeError, TimeoutError, urllib.error.URLError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    complete = [item["payload"] for item in events if item["event"] == "complete"]
    window_complete = [item["payload"] for item in events if item["event"] == "window_complete"]
    window_error = [item["payload"] for item in events if item["event"] == "window_error"]
    proof = complete[0].get("proof", {}) if len(complete) == 1 else {}
    inference_ms = window_complete[0].get("inference_ms") if len(window_complete) == 1 else None
    identity_still_exact = bool(
        final
        and final.get("web_runtime_class") == RUNTIME_CLASS
        and final.get("web_board_runtime_class") == BOARD_RUNTIME_CLASS
        and final.get("web_language_model_class") == LANGUAGE_MODEL_CLASS
        and final.get("runtime_load_count") == 1
        and final.get("t64_used") is False
    )
    functional_pass = bool(
        error is None and not window_error and len(complete) == 1 and len(window_complete) == 1
        and complete[0].get("status") == "PASS"
        and str(proof.get("build_id", "")).lower() == BUILD_ID
        and proof.get("language_cpu_linear_fallback") is False
        and proof.get("pl_logical_chain_calls") == proof.get("expected_pl_logical_chain_calls")
        and int(proof.get("pl_expected_macros", 0)) > 0
        and proof.get("language_scheduler") == "M238 T32 input-pack prefetch + fused parse overlap"
        and proof.get("prefill_attention") == "M241 grouped-GQA with reference RoPE"
        and identity_still_exact
        and final.get("windows_completed") == 1
        and final.get("last_completed_newest_sequence") == 3
    )
    performance_pass = bool(
        functional_pass and inference_ms is not None
        and float(inference_ms) <= args.target_window_ms
    )
    result = {
        "date": "2026-09-02",
        "gate": "M244-real-KV260-M243-fixed-four-frame-HTTP-SSE-E2E-and-5s-target",
        "status": "PASS" if functional_pass and performance_pass else "FAIL",
        "functional_status": "PASS" if functional_pass else "FAIL",
        "performance_status": "PASS" if performance_pass else "FAIL",
        "classification": (
            "Real-KV260 deterministic four-frame HTTP/SSE PS-vision plus M238/M241 FPGA "
            "language E2E; the 5000 ms target is independently fail-closed."
        ),
        "target_window_ms": args.target_window_ms,
        "inference_ms": inference_ms,
        "complete": complete,
        "window_complete": window_complete,
        "window_error": window_error,
        "events": events,
        "submitted": submitted,
        "fixed_frames_sha256": locals().get("frames_sha256"),
        "initial": initial,
        "final": final,
        "elapsed_ms": (time.monotonic() - started_at) * 1000.0,
        "error": error,
        "runtime_loaded_once": bool(final and final.get("runtime_load_count") == 1),
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "If functionally correct but slower than 5000 ms, preserve this exact baseline and "
            "optimize only the measured dominant stage before knife-alert promotion."
        ),
    }
    atomic_json(args.result, result)
    print("M244_FIXED_WINDOW_FUNCTIONAL_PASS" if functional_pass else "M244_FIXED_WINDOW_FUNCTIONAL_FAIL")
    print("M244_FIXED_WINDOW_5S_PASS" if performance_pass else "M244_FIXED_WINDOW_5S_FAIL")
    return 0 if functional_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
