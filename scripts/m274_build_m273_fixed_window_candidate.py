#!/usr/bin/env python3
"""Build the clean M274/M273 board package and compressed UART archive."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deployment/mage_vl4b/m269_multiscale_binary_board_candidate"
M273_SOURCE = ROOT / "deployment/mage_vl4b/m273_latest_binary_source"
M274_SOURCE = ROOT / "deployment/mage_vl4b/m274_m273_fixed_window_source"
DEST = ROOT / "deployment/mage_vl4b/m274_m273_fixed_window_board_candidate"
PARTIAL = DEST.with_name(DEST.name + ".partial")
ARCHIVE = ROOT / "deployment/mage_vl4b/m274_m273_fixed_window_board_candidate.tar.gz"
BUILD_RESULT = ROOT / "deployment/mage_vl4b/M274_M273_FIXED_WINDOW_BUILD_RESULT.json"
EVIDENCE = (
    ROOT / "deployment/mage_vl4b/M273_GPU_EXACT_LATEST_BINARY_RESULT.json",
    ROOT / "deployment/mage_vl4b/M273_EXACT_RUNTIME_OFFLINE_RESULT.json",
    ROOT / "deployment/mage_vl4b/M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json",
    ROOT / "deployment/mage_vl4b/M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if any(path.exists() for path in (DEST, PARTIAL, ARCHIVE, BUILD_RESULT)):
        raise RuntimeError("M274 output already exists; refuse overwrite")
    base_manifest = BASE / "PACKAGE_MANIFEST.json"
    if sha256(base_manifest) != "9213111ac31effbaf1c1775fe0e254249f11bf4c3d88396ac29eb81172e240fc":
        raise RuntimeError("M274 M269 base hash mismatch")
    sources = {path.name: path for path in BASE.iterdir() if path.is_file() and path.name != "PACKAGE_MANIFEST.json"}
    for root in (M273_SOURCE, M274_SOURCE):
        sources.update({path.name: path for path in root.iterdir() if path.is_file()})
    sources.update({path.name: path for path in EVIDENCE})
    PARTIAL.mkdir(parents=False)
    try:
        files = []
        for name, source in sorted(sources.items()):
            if not source.is_file():
                raise RuntimeError(f"M274 missing source {name}")
            destination = PARTIAL / name
            shutil.copy2(source, destination)
            files.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
        manifest = {
            "schema": "tellme-m274-m273-fixed-window-v1",
            "status": "PASS_OFFLINE_READY_FOR_M274_BOARD_GATE",
            "classification": "Exact M273 runtime plus stage-timed real-board gate and retrying M254 restore; not yet board-executed or Web-promoted.",
            "predecessor_m269_manifest_sha256": sha256(base_manifest),
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "visual_tokens": 98,
            "prompt_tokens": 164,
            "expected_t32_calls": 932,
            "decode_calls": 0,
            "per_stage_timing": True,
            "stable_restore_attempts": 2,
            "stable_rollback_preserved": True,
            "excluded": ["__pycache__", "*.pyc", "temporary logs"],
        }
        (PARTIAL / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(PARTIAL, DEST)
        with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as archive:
            for path in sorted(DEST.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)
        result = {
            "date": "2026-09-02",
            "gate": "M274-M273-fixed-window-clean-package",
            "status": "M274_BUILD_PASS",
            "classification": "Clean hash-locked stage-timed package only; no board or TTFT claim.",
            "directory": str(DEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(DEST / "PACKAGE_MANIFEST.json"),
            "file_count": manifest["file_count"],
            "total_bytes": manifest["total_bytes"],
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_bytes": ARCHIVE.stat().st_size,
            "archive_sha256": sha256(ARCHIVE),
            "board_execution_run": False,
            "stable_rollback_preserved": True,
            "next_gate": "Run attempt 01 through authenticated COM3 and require exact M254 restoration.",
        }
        partial_result = BUILD_RESULT.with_name(BUILD_RESULT.name + f".partial-{os.getpid()}")
        partial_result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(partial_result, BUILD_RESULT)
    except Exception:
        if PARTIAL.exists(): shutil.rmtree(PARTIAL)
        if DEST.exists(): shutil.rmtree(DEST)
        if ARCHIVE.exists(): ARCHIVE.unlink()
        raise
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
