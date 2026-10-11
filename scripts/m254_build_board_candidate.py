#!/usr/bin/env python3
"""Build a clean, hash-closed M254 dual-path Web delta."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m254_dual_path_web_source"
M253 = ROOT / "deployment/mage_vl4b/m253_latest_fast_stream_source"
M251 = ROOT / "deployment/mage_vl4b/m251_fast_frame_pipeline_source"
M250 = ROOT / "deployment/mage_vl4b/m250_temporal_action_source"
M248 = ROOT / "deployment/mage_vl4b/m248_fast_safety_source"
M245 = ROOT / "deployment/mage_vl4b/m245_knife_alarm_source"
M247 = ROOT / "deployment/mage_vl4b/m247_knife_alarm_web_source/static"
OUTPUT = ROOT / "deployment/mage_vl4b/m254_dual_path_web_candidate_r3"
RESULT = ROOT / "deployment/mage_vl4b/M254_DUAL_PATH_WEB_BOARD_CANDIDATE_RESULT_R3.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists() or RESULT.exists():
        raise RuntimeError("M254 clean destination/result required")
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=True)
    files = (
        (SOURCE / "m254_dual_path_core.py", "m254_dual_path_core.py"),
        (SOURCE / "m254_video_server.py", "m254_video_server.py"),
        (SOURCE / "m254_runtime_ready_probe.py", "m254_runtime_ready_probe.py"),
        (SOURCE / "m254_dependency_preflight.py", "m254_dependency_preflight.py"),
        (SOURCE / "verify_m254_candidate.py", "verify_m254_candidate.py"),
        (SOURCE / "run_m254_board_gate.sh", "run_m254_board_gate.sh"),
        (M253 / "latest_fast_stream.py", "latest_fast_stream.py"),
        (M253 / "m253_board_latest_stream.py", "m253_board_latest_stream.py"),
        (M251 / "fast_frame_pipeline.py", "fast_frame_pipeline.py"),
        (M251 / "immediate_safety_monitor.py", "immediate_safety_monitor.py"),
        (M250 / "temporal_action_adapter.py", "temporal_action_adapter.py"),
        (M248 / "fast_safety_monitor.py", "fast_safety_monitor.py"),
        (M245 / "knife_alarm.py", "knife_alarm.py"),
        (M247 / "index.html", "static/index.html"),
        (M247 / "app.js", "static/app.js"),
        (M247 / "style.css", "static/style.css"),
        (ROOT / "deployment/mage_vl4b/M243_WEB_PREFILL_BOARD_RESULT_05.json", "M243_WEB_PREFILL_BOARD_RESULT_05.json"),
        (ROOT / "deployment/mage_vl4b/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json", "M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json"),
        (ROOT / "deployment/mage_vl4b/M249_KV260_SSDLITE_BOARD_RESULT_03.json", "M249_KV260_SSDLITE_BOARD_RESULT_03.json"),
    )
    records = []
    for source, relative in files:
        if not source.is_file():
            raise RuntimeError(f"M254 missing source {source}")
        destination = partial / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        records.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    forbidden = [path for path in partial.rglob("*") if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts)]
    if forbidden:
        raise RuntimeError(f"M254 forbidden cache files {forbidden}")
    manifest = {
        "date": "2026-09-02",
        "gate": "M254-dual-path-Web-board-candidate",
        "status": "PASS",
        "classification": "Immutable R3 hash-closed delta: complete dependency preflight before service stop, then deadline-bearing M253 fast runtime starts before asynchronous M243/M238/M241 semantic loading.",
        "predecessors": {
            "m243_board_result_sha256": sha256(ROOT / "deployment/mage_vl4b/M243_WEB_PREFILL_BOARD_RESULT_05.json"),
            "m253_board_result_sha256": sha256(ROOT / "deployment/mage_vl4b/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json"),
            "m249_board_result_sha256": sha256(ROOT / "deployment/mage_vl4b/M249_KV260_SSDLITE_BOARD_RESULT_03.json"),
        },
        "policy": "M253 immediate; M243/M238/M241 alarm-only capacity-one review; semantic review never blocks alarm.",
        "files": records,
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
        "forbidden_cache_file_count": 0,
    }
    manifest_path = partial / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    partial.replace(OUTPUT)
    value = {
        "date": "2026-09-02",
        "gate": "M254-dual-path-Web-board-candidate-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(records),
        "total_bytes": manifest["total_bytes"],
        "next_gate": "COM3 package verification, environment preflight and no-frame M254 runtime identity; preserve exact M243 rollback on failure.",
    }
    RESULT.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, indent=2))
    print("M254_DUAL_PATH_WEB_BOARD_CANDIDATE_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
