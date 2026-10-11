#!/usr/bin/env python3
"""Build a clean, whitelisted, hash-locked M259 board delta package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m259_prevision_keyframe_source"
M258 = ROOT / "deployment/mage_vl4b/m258_vision_state_sweep_source"
M257 = ROOT / "deployment/mage_vl4b/m257_alarm_keyframe_source"
DESTINATION = ROOT / "deployment/mage_vl4b/m259_prevision_keyframe_board_candidate"
PARTIAL = DESTINATION.with_name(DESTINATION.name + ".partial")

WHITELIST = {
    "m259_variable_vision_runtime.py": SOURCE / "m259_variable_vision_runtime.py",
    "m259_video_runtime.py": SOURCE / "m259_video_runtime.py",
    "m259_m254_video_server.py": SOURCE / "m259_m254_video_server.py",
    "m258_vectorized_w4_runtime.py": M258 / "m258_vectorized_w4_runtime.py",
    "keyframe_reducer.py": M257 / "keyframe_reducer.py",
    "variable_video_contract.py": M257 / "variable_video_contract.py",
    "m259_verify_candidate.py": SOURCE / "m259_verify_candidate.py",
    "M259_BOUNDARY.md": SOURCE / "M259_BOUNDARY.md",
    "M259_PREVISION_KEYFRAME_OFFLINE_RESULT.json": (
        ROOT / "deployment/mage_vl4b/M259_PREVISION_KEYFRAME_OFFLINE_RESULT.json"
    ),
    "M258_VISION_STATE_POLICY_OFFLINE_RESULT.json": (
        ROOT / "deployment/mage_vl4b/M258_VISION_STATE_POLICY_OFFLINE_RESULT.json"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if DESTINATION.exists() or PARTIAL.exists():
        raise RuntimeError("M259 destination/partial already exists; refuse overwrite")
    for name, source in WHITELIST.items():
        if not source.is_file():
            raise RuntimeError(f"M259 source missing: {name}/{source}")
    result = json.loads(WHITELIST["M259_PREVISION_KEYFRAME_OFFLINE_RESULT.json"].read_text())
    if result.get("status") != "PASS_OFFLINE_FINITE_SEMANTIC_AND_BOARD_PENDING":
        raise RuntimeError("M259 source evidence is not offline PASS")

    PARTIAL.mkdir(parents=False)
    try:
        entries = []
        for relative, source in sorted(WHITELIST.items()):
            destination = PARTIAL / relative
            shutil.copy2(source, destination)
            entries.append({
                "path": relative,
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            })
        manifest = {
            "schema": "tellme-m259-delta-v1",
            "status": "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED",
            "classification": (
                "Hash-locked source/evidence delta only; not deployed, board-timed, "
                "semantically accepted, or Web-promoted."
            ),
            "files": entries,
            "file_count": len(entries),
            "total_bytes": sum(item["bytes"] for item in entries),
            "path_whitelist": sorted(WHITELIST),
            "excluded": ["__pycache__", "*.pyc", "temporary logs"],
            "stable_rollback_preserved": True,
        }
        manifest_path = PARTIAL / "PACKAGE_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(PARTIAL, DESTINATION)
    except Exception:
        if PARTIAL.exists():
            shutil.rmtree(PARTIAL)
        raise
    print(
        "M259_PACKAGE_BUILD_PASS "
        f"files={manifest['file_count']} bytes={manifest['total_bytes']} "
        f"manifest_sha256={sha256(DESTINATION / 'PACKAGE_MANIFEST.json')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
