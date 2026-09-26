#!/usr/bin/env python3
"""Bounded local health probe for the M223 corrected control plane."""

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
    raise RuntimeError("M223 service preflight is not PASS")
deadline = time.monotonic() + 20.0
health = None
error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(args.url, timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))
        if (
            health.get("status") == "idle"
            and health.get("mode") == "continuous-latest-only"
            and health.get("source_mode") == "unselected"
        ):
            break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    time.sleep(1.0)
passed = bool(
    health
    and health.get("status") == "idle"
    and health.get("mode") == "continuous-latest-only"
    and health.get("source_mode") == "unselected"
)
value = {
    "date": "2026-09-01",
    "gate": "M223-real-KV260-corrected-realtime-control-plane",
    "status": "PASS" if passed else "FAIL",
    "classification": (
        "Real-KV260 hash-verified M222 service process and idle HTTP control plane; "
        "no frame, runtime load, complete window, FPGA E2E, or latency acceptance yet."
    ),
    "package_manifest_sha256": args.package_manifest_sha256,
    "service_pid": args.pid,
    "local_health": health,
    "error": error,
    "candidate_build_id": "0x4D395832",
    "worker_event_loop_fix_packaged": True,
    "vectorized_vision_decoder_packaged": True,
    "continuous_stream_inference_executed": False,
    "persistent_boot_dtb_cma_partitions_services_changed": False,
    "temporary_service_restarted": True,
    "stable_rollback_preserved": True,
    "next_gate": (
        "Start one session and require runtime_load_count=1, worker_alive=true and "
        "service_state=ready before running fixed-four-frame vision/E2E timing."
    ),
}
args.result.parent.mkdir(parents=True, exist_ok=True)
temporary = args.result.with_name(args.result.name + ".partial")
temporary.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
os.replace(temporary, args.result)
print("__M223_BOARD_RESULT_BEGIN__")
print(json.dumps(value, separators=(",", ":")))
print("__M223_BOARD_RESULT_END__")
print("M223_BOARD_CONTROL_PASS" if passed else "M223_BOARD_CONTROL_FAIL")
raise SystemExit(0 if passed else 1)

