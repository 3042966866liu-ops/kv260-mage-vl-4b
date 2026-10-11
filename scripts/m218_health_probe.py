#!/usr/bin/env python3
"""Bounded local health probe and atomic M218 board service result."""

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--preflight", type=Path, required=True)
parser.add_argument("--package-manifest-sha256", required=True)
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
if preflight.get("status") != "PASS":
    raise RuntimeError("M218 service preflight is not PASS")
deadline = time.monotonic() + 20
health = None
error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(args.url, timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))
        if (
            health.get("mode") == "continuous-latest-only"
            and health.get("status") == "idle"
            and health.get("source_mode") == "unselected"
            and health.get("source_content_is_finite") is False
        ):
            break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    time.sleep(1)
passed = bool(
    health
    and health.get("mode") == "continuous-latest-only"
    and health.get("status") == "idle"
    and health.get("source_mode") == "unselected"
    and health.get("source_content_is_finite") is False
)
value = {
    "date": "2026-09-01",
    "gate": "M218-real-KV260-dual-source-service-control-plane",
    "status": "PASS" if passed else "FAIL",
    "classification": "Real-KV260 hash-verified camera/local-file-loop latest-only HTTP/SSE control plane; no real frames, model inference, FPGA complete window, or latency acceptance yet.",
    "package_manifest_sha256": args.package_manifest_sha256,
    "service_pid": args.pid,
    "local_health": health,
    "error": error,
    "candidate_build_id": "0x4D395832",
    "input_modes": ["browser-camera", "uploaded-file-loop"],
    "continuous_stream_inference_executed": False,
    "persistent_boot_dtb_cma_partitions_services_changed": False,
    "temporary_service_restarted": True,
    "stable_rollback_preserved": True,
    "next_gate": "Verify Windows/public HTTP dual-source UI, then obtain action-time confirmation before selecting the local MP4 and transmitting sampled frames.",
}
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("__M218_BOARD_RESULT_BEGIN__")
print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
print("__M218_BOARD_RESULT_END__")
print("M218_DUAL_SOURCE_BOARD_CONTROL_PASS" if passed else "M218_DUAL_SOURCE_BOARD_CONTROL_FAIL")
raise SystemExit(0 if passed else 1)
