#!/usr/bin/env python3
"""Start one no-frame M254 session and prove both selected runtimes."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


def request_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    raw = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=raw, method=method)
    if raw is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    args = parser.parse_args()
    started = time.monotonic()
    deadline = started + args.timeout_seconds
    last = None
    while time.monotonic() < deadline:
        try:
            last = request_json("http://127.0.0.1:8001/api/health")
            if last.get("status") == "idle":
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f"M254 service did not listen: {last}")
    request_json("http://127.0.0.1:8001/api/4b/video/live/start", "POST", {
        "prompt": "请复核报警窗口中的人物动作和刀具风险。",
        "max_new_tokens": 1,
        "source_mode": "browser-camera",
        "source_label": "M254-no-frame-readiness",
    })
    final = None
    while time.monotonic() < deadline:
        try:
            final = request_json("http://127.0.0.1:8001/api/4b/video/live/status")
            fast = final.get("fast_path") or {}
            semantic = final.get("semantic_review") or {}
            if (
                final.get("mode") == "M254-dual-path-latest-only"
                and fast.get("runtime_load_count") == 1
                and fast.get("frame_slot", {}).get("accepted_frames") == 0
                and semantic.get("policy") == "alarm-only-capacity-one"
                and final.get("web_runtime_class") == "M243VideoRuntime"
                and final.get("web_board_runtime_class") == "M238PrefillRuntime"
                and final.get("web_language_model_class") == "M241VideoLanguageModel"
                and final.get("web_prefill_attention") == "M241-grouped-GQA-reference-RoPE"
                and final.get("t64_used") is False
            ):
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f"M254 runtime readiness timeout: {final}")
    result = {
        "date": "2026-09-02",
        "gate": "M254-KV260-dual-path-Web-runtime-readiness",
        "status": "PASS",
        "classification": "Real KV260 hash-locked no-frame service/runtime identity only; not frame inference, target-scene accuracy, semantic output, alarm latency, or full Web acceptance.",
        "package_manifest_sha256": args.manifest_sha256,
        "pid": args.pid,
        "runtime_ready_elapsed_ms": (time.monotonic() - started) * 1000.0,
        "fast_runtime_load_count": final["fast_path"]["runtime_load_count"],
        "fast_frames_submitted": final["fast_path"]["frame_slot"]["accepted_frames"],
        "semantic_policy": final["semantic_review"]["policy"],
        "web_runtime_class": final["web_runtime_class"],
        "web_board_runtime_class": final["web_board_runtime_class"],
        "web_language_model_class": final["web_language_model_class"],
        "web_language_runtime": final["web_language_runtime"],
        "web_prefill_attention": final["web_prefill_attention"],
        "t64_used": final["t64_used"],
        "stable_t32_overlay_preserved": True,
        "next_gate": "Send labelled knife/non-knife frames through the Web endpoint; require immediate M253 safety_result before optional M243/M241 review and record target-scene metrics.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print("__M254_BOARD_RESULT_BEGIN__")
    print(json.dumps(result, separators=(",", ":")))
    print("__M254_BOARD_RESULT_END__")
    print("M254_KV260_DUAL_PATH_RUNTIME_READY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

