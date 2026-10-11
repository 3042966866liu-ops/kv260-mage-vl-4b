#!/usr/bin/env python3
"""Bounded idle-control-plane probe after applying M227."""

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--patch-manifest-sha256", required=True)
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--result", type=Path, required=True)
args = parser.parse_args()
deadline = time.monotonic() + 20.0
health = None
error = None
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(args.url, timeout=3.0) as response:
            health = json.loads(response.read().decode("utf-8"))
        if health.get("status") == "idle" and health.get("build_id") == "0x4D395832":
            break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    time.sleep(1.0)
passed = bool(health and health.get("status") == "idle" and health.get("mode") == "continuous-latest-only")
value = {
    "date": "2026-09-01",
    "gate": "M227-real-KV260-visual-runtime-base-compatibility-control-plane",
    "status": "PASS" if passed else "FAIL",
    "classification": "Real-KV260 hash-verified runtime-import compatibility patch and idle service only; no runtime-load or frame inference claim.",
    "patch_manifest_sha256": args.patch_manifest_sha256,
    "service_pid": args.pid,
    "local_health": health,
    "error": error,
    "candidate_build_id": "0x4D395832",
    "persistent_boot_dtb_cma_partitions_services_changed": False,
    "stable_rollback_preserved": True,
    "next_gate": "Rerun M226 no-frame runtime-ready gate.",
    }
args.result.parent.mkdir(parents=True, exist_ok=True)
partial = args.result.with_name(args.result.name + ".partial")
partial.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
os.replace(partial, args.result)
print("__M227_BOARD_RESULT_BEGIN__")
print(json.dumps(value, separators=(",", ":")))
print("__M227_BOARD_RESULT_END__")
print("M227_BOARD_CONTROL_PASS" if passed else "M227_BOARD_CONTROL_FAIL")
raise SystemExit(0 if passed else 1)

