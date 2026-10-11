#!/usr/bin/env python3
"""Build M271 R2 with stage timing and retrying stable-service restoration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deployment/mage_vl4b/m269_multiscale_binary_board_candidate"
SOURCE = ROOT / "deployment/mage_vl4b/m271_m269_fixed_window_source"
DEST = ROOT / "deployment/mage_vl4b/m271_m269_fixed_window_board_candidate_r2"
PARTIAL = DEST.with_name(DEST.name + ".partial")
ARCHIVE = ROOT / "deployment/mage_vl4b/m271_m269_fixed_window_board_candidate_r2.tar.gz"
BUILD_RESULT = ROOT / "deployment/mage_vl4b/M271_M269_FIXED_WINDOW_BUILD_RESULT_R2.json"
M270 = ROOT / "deployment/mage_vl4b/M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json"
M244 = ROOT / "deployment/mage_vl4b/M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if any(path.exists() for path in (DEST, PARTIAL, ARCHIVE, BUILD_RESULT)):
        raise RuntimeError("M271 R2 output already exists; refuse overwrite")
    base_manifest = BASE / "PACKAGE_MANIFEST.json"
    if sha256(base_manifest) != "9213111ac31effbaf1c1775fe0e254249f11bf4c3d88396ac29eb81172e240fc":
        raise RuntimeError("M271 R2 M269 package hash mismatch")
    sources = {
        path.name: path for path in BASE.iterdir()
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    sources.update({path.name: path for path in SOURCE.iterdir() if path.is_file()})
    sources["M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json"] = M270
    sources["M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json"] = M244
    PARTIAL.mkdir(parents=False)
    try:
        files = []
        for name, source in sorted(sources.items()):
            if not source.is_file():
                raise RuntimeError(f"M271 R2 missing source {name}")
            destination = PARTIAL / name
            shutil.copy2(source, destination)
            files.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
        manifest = {
            "schema": "tellme-m271-fixed-window-v2",
            "status": "PASS_OFFLINE_READY_FOR_M271_BOARD_GATE",
            "classification": (
                "Hash-locked M269 fixed-window gate with per-stage timing and retrying exact-M254 restoration; "
                "not yet board-executed, Web-promoted or target-scene calibrated."
            ),
            "predecessor_m269_manifest_sha256": sha256(base_manifest),
            "predecessor_m270_result_sha256": sha256(M270),
            "predecessor_m244_result_sha256": sha256(M244),
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "visual_tokens": 196,
            "prompt_tokens": 284,
            "expected_t32_calls": 1394,
            "decode_calls": 0,
            "per_stage_timing": True,
            "stable_restore_attempts": 2,
            "stable_rollback_preserved": True,
            "excluded": ["__pycache__", "*.pyc", "temporary logs"],
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
            "gate": "M271-M269-fixed-window-clean-package-r2",
            "status": "M271_BUILD_PASS",
            "classification": "R2 clean package with stage timing and recovery retry; no board or performance claim.",
            "supersedes_local_package_manifest_sha256": "c2a4cb9800ccc47bc2bc41c4185399c6f1ecc58a9da195fd65991934279babe5",
            "directory": str(DEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(DEST / "PACKAGE_MANIFEST.json"),
            "file_count": manifest["file_count"],
            "total_bytes": manifest["total_bytes"],
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_bytes": ARCHIVE.stat().st_size,
            "archive_sha256": sha256(ARCHIVE),
            "per_stage_timing": True,
            "stable_restore_attempts": 2,
            "board_execution_run": False,
            "stable_rollback_preserved": True,
            "next_gate": "Run attempt 02 through authenticated COM3 and require exact M254 restoration.",
        }
        partial_result = BUILD_RESULT.with_name(BUILD_RESULT.name + f".partial-{os.getpid()}")
        partial_result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(partial_result, BUILD_RESULT)
    except Exception:
        if PARTIAL.exists():
            shutil.rmtree(PARTIAL)
        if DEST.exists():
            shutil.rmtree(DEST)
        if ARCHIVE.exists():
            ARCHIVE.unlink()
        raise
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
