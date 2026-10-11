#!/usr/bin/env python3
"""Build a clean, hash-closed M253 board candidate from exact source files."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m253_latest_fast_stream_source"
DESTINATION = ROOT / "deployment/mage_vl4b/m253_latest_fast_stream_candidate_r2"
MAPPINGS = {
    SOURCE / "latest_fast_stream.py": "latest_fast_stream.py",
    SOURCE / "m253_board_latest_stream.py": "m253_board_latest_stream.py",
    SOURCE / "run_m253_board_gate.sh": "run_m253_board_gate.sh",
    SOURCE / "verify_m253_candidate.py": "verify_m253_candidate.py",
    ROOT / "deployment/mage_vl4b/m251_fast_frame_pipeline_source/fast_frame_pipeline.py": "fast_frame_pipeline.py",
    ROOT / "deployment/mage_vl4b/m251_fast_frame_pipeline_source/immediate_safety_monitor.py": "immediate_safety_monitor.py",
    ROOT / "deployment/mage_vl4b/m250_temporal_action_source/temporal_action_adapter.py": "temporal_action_adapter.py",
    ROOT / "deployment/mage_vl4b/m248_fast_safety_source/fast_safety_monitor.py": "fast_safety_monitor.py",
    ROOT / "deployment/mage_vl4b/m245_knife_alarm_source/knife_alarm.py": "knife_alarm.py",
    ROOT / "deployment/mage_vl4b/M249_KV260_SSDLITE_BOARD_RESULT_03.json": "M249_KV260_SSDLITE_BOARD_RESULT_03.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError(f"candidate already exists: {DESTINATION}")
    staging = DESTINATION.with_name(DESTINATION.name + f".staging-{os.getpid()}")
    staging.mkdir(parents=True)
    try:
        entries = []
        for source, relative in MAPPINGS.items():
            if not source.is_file():
                raise RuntimeError(f"missing source: {source}")
            target = staging / relative
            shutil.copyfile(source, target)
            entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
        manifest = {
            "date": "2026-09-02",
            "gate": "M253-KV260-latest-fast-stream-board-candidate",
            "status": "PASS",
            "classification": (
                "Clean M253 runtime package only; not board execution, camera/Web, accuracy, "
                "FPGA detector, or complete real-time PASS."
            ),
            "m249_board_predecessor_sha256": "e45597c3cc14a68420b09d389dde8c2b1cd81ab23eacc5833b5a527d4f633681",
            "file_count": len(entries),
            "total_bytes": sum(item["bytes"] for item in entries),
            "files": sorted(entries, key=lambda item: item["path"]),
        }
        (staging / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        cache = [path for path in staging.rglob("*") if "__pycache__" in path.parts or path.suffix == ".pyc"]
        if cache:
            raise RuntimeError(f"cache pollution: {cache}")
        os.replace(staging, DESTINATION)
        result = {
            "date": "2026-09-02",
            "gate": "M253-board-candidate-build",
            "status": "PASS",
            "candidate": str(DESTINATION.relative_to(ROOT)).replace("\\", "/"),
            "package_manifest_sha256": sha256(DESTINATION / "PACKAGE_MANIFEST.json"),
            "file_count": len(entries),
            "total_bytes": manifest["total_bytes"],
            "next_gate": "Verify closure, upload through COM3, and run only M253 latest-only board pressure.",
        }
        output = ROOT / "deployment/mage_vl4b/M253_LATEST_FAST_STREAM_BOARD_CANDIDATE_RESULT.json"
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        print("M253_BOARD_CANDIDATE_BUILD_PASS")
        return 0
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
