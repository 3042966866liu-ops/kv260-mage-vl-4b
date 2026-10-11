#!/usr/bin/env python3
"""Build the clean M283 BACT 159/160/161 KV260 package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deployment/mage_vl4b/m277_m276_fixed_window_board_candidate"
M281_SOURCE = ROOT / "deployment/mage_vl4b/m281_bact_boundary_source"
M283_SOURCE = ROOT / "deployment/mage_vl4b/m283_bact_boundary_source"
DEST = ROOT / "deployment/mage_vl4b/m283_bact_boundary_board_candidate"
PARTIAL = DEST.with_name(DEST.name + ".partial")
ARCHIVE = ROOT / "deployment/mage_vl4b/m283_bact_boundary_board_candidate.tar.gz"
BUILD_RESULT = ROOT / "deployment/mage_vl4b/M283_BACT_BOUNDARY_BUILD_RESULT.json"
BASE_MANIFEST_SHA256 = "0e1bdfa578f655b2bb6d07b097f1dda115a7936906e3e112137123db65e7f2fa"
EXCLUDE_BASE = {
    "PACKAGE_MANIFEST.json",
    "M277_BOUNDARY.md",
    "m277_fixed_window_gate.py",
    "m277_stage_archive.py",
    "m277_verify_package.py",
    "run_m277_m276_fixed_window_gate.sh",
}
EVIDENCE = (
    ROOT / "deployment/mage_vl4b/M277_M276_FIXED_WINDOW_BOARD_RESULT_01.json",
    ROOT / "deployment/mage_vl4b/M280_BACT_METHOD_PLAN_RESULT.json",
    ROOT / "deployment/mage_vl4b/M281_BACT_159_160_161_GEOMETRY_RESULT.json",
    ROOT / "deployment/mage_vl4b/M282_GPU_BACT_159_160_161_RESULT.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    outputs = (DEST, PARTIAL, ARCHIVE, BUILD_RESULT)
    if any(path.exists() for path in outputs):
        raise RuntimeError("M283 output already exists; refuse overwrite")
    base_manifest = BASE / "PACKAGE_MANIFEST.json"
    if sha256(base_manifest) != BASE_MANIFEST_SHA256:
        raise RuntimeError("M283 M277 base manifest hash mismatch")
    sources = {
        path.name: path
        for path in BASE.iterdir()
        if path.is_file() and path.name not in EXCLUDE_BASE
    }
    for source_root in (M281_SOURCE, M283_SOURCE):
        for path in source_root.iterdir():
            if path.is_file():
                sources[path.name] = path
    for path in EVIDENCE:
        sources[path.name] = path
    PARTIAL.mkdir(parents=False)
    try:
        files = []
        for name, source in sorted(sources.items()):
            if not source.is_file():
                raise RuntimeError(f"M283 missing source {name}")
            destination = PARTIAL / name
            shutil.copy2(source, destination)
            files.append({
                "path": name,
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            })
        manifest = {
            "schema": "tellme-m283-bact-boundary-v1",
            "status": "PASS_OFFLINE_READY_FOR_M283_BOARD_GATE",
            "classification": (
                "Hash-locked one-load, one-vision, controlled 159/160/161 real-KV260 "
                "boundary package; not yet board-executed or performance-promoted."
            ),
            "predecessor_m277_manifest_sha256": sha256(base_manifest),
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "build_id": "0x4D395832",
            "kernel": "mage_m120_m89x2_0",
            "probe_order": [159, 160, 161],
            "expected_t32_batches": [5, 5, 6],
            "expected_logical_calls": [778, 778, 932],
            "expected_total_logical_calls": 2488,
            "runtime_load_count": 1,
            "vision_execution_count": 1,
            "new_hls_or_rtl": False,
            "kernel_math_changed": False,
            "stable_restore_attempts": 2,
            "stable_rollback_preserved": True,
            "excluded": ["__pycache__", "*.pyc", "temporary logs", "superseded M277 runner"],
        }
        (PARTIAL / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(PARTIAL, DEST)
        with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as archive:
            for path in sorted(DEST.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)
        result = {
            "date": "2026-09-02",
            "gate": "M283-BACT-boundary-clean-package",
            "status": "M283_BUILD_PASS",
            "classification": "Clean hash-locked boundary package only; no new board or speed claim.",
            "directory": str(DEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(DEST / "PACKAGE_MANIFEST.json"),
            "file_count": manifest["file_count"],
            "total_bytes": manifest["total_bytes"],
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_bytes": ARCHIVE.stat().st_size,
            "archive_sha256": sha256(ARCHIVE),
            "probe_order": manifest["probe_order"],
            "expected_logical_calls": manifest["expected_logical_calls"],
            "expected_total_logical_calls": manifest["expected_total_logical_calls"],
            "board_execution_run": False,
            "active_board_service_changed": False,
            "stable_rollback_preserved": True,
            "source_sha256": sha256(Path(__file__).resolve()),
            "next_gate": (
                "Run local AST/hash/import/bash closure; only then request same-COM3 sudo "
                "for one isolated M283 attempt."
            ),
        }
        partial_result = BUILD_RESULT.with_name(BUILD_RESULT.name + f".partial-{os.getpid()}")
        partial_result.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(partial_result, BUILD_RESULT)
    except Exception:
        if PARTIAL.exists():
            shutil.rmtree(PARTIAL)
        if DEST.exists():
            shutil.rmtree(DEST)
        if ARCHIVE.exists():
            ARCHIVE.unlink()
        raise
    print(
        f"M283_BUILD_PASS files={result['file_count']} bytes={result['total_bytes']} "
        f"manifest={result['manifest_sha256']} archive={result['archive_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
