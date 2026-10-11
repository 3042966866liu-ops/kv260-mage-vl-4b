#!/usr/bin/env python3
"""Build a clean, whitelisted, hash-locked M260 board delta package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
M260 = ROOT / "deployment/mage_vl4b/m260_cached_w4_source"
M259_PACKAGE = ROOT / "deployment/mage_vl4b/m259_prevision_keyframe_board_candidate"
DESTINATION = ROOT / "deployment/mage_vl4b/m260_cached_w4_board_candidate"
PARTIAL = DESTINATION.with_name(DESTINATION.name + ".partial")

M259_FILES = {
    path.name: path
    for path in M259_PACKAGE.iterdir()
    if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
}
WHITELIST = {
    **M259_FILES,
    "m260_cached_w4_runtime.py": M260 / "m260_cached_w4_runtime.py",
    "m260_video_runtime.py": M260 / "m260_video_runtime.py",
    "m260_m254_video_server.py": M260 / "m260_m254_video_server.py",
    "m260_verify_candidate.py": M260 / "m260_verify_candidate.py",
    "M260_BOUNDARY.md": M260 / "M260_BOUNDARY.md",
    "M260_CACHED_W4_OFFLINE_RESULT.json": (
        ROOT / "deployment/mage_vl4b/M260_CACHED_W4_OFFLINE_RESULT.json"
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
        raise RuntimeError("M260 destination/partial already exists; refuse overwrite")
    if not M259_PACKAGE.is_dir():
        raise RuntimeError("M260 requires the verified M259 package")
    for name, source in WHITELIST.items():
        if not source.is_file():
            raise RuntimeError(f"M260 source missing: {name}/{source}")
    result = json.loads(
        WHITELIST["M260_CACHED_W4_OFFLINE_RESULT.json"].read_text(encoding="utf-8")
    )
    if result.get("status") != "PASS_OFFLINE_EXACT_BOARD_MEMORY_AND_SPEED_PENDING":
        raise RuntimeError("M260 source evidence is not offline PASS")
    if result.get("warm_output_bit_exact_to_cold") is not True:
        raise RuntimeError("M260 source output is not exact")

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
            "schema": "tellme-m260-delta-v1",
            "status": "OFFLINE_PACKAGE_PASS_BOARD_MEMORY_AND_SPEED_PENDING",
            "classification": (
                "Hash-locked M259+M260 source/evidence delta only; not deployed, "
                "board-memory accepted, board-timed, semantically accepted, or promoted."
            ),
            "files": entries,
            "file_count": len(entries),
            "total_bytes": sum(item["bytes"] for item in entries),
            "path_whitelist": sorted(WHITELIST),
            "excluded": ["__pycache__", "*.pyc", "temporary logs"],
            "stable_rollback_preserved": True,
        }
        (PARTIAL / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(PARTIAL, DESTINATION)
    except Exception:
        if PARTIAL.exists():
            shutil.rmtree(PARTIAL)
        raise
    print(
        "M260_PACKAGE_BUILD_PASS "
        f"files={manifest['file_count']} bytes={manifest['total_bytes']} "
        f"manifest_sha256={sha256(DESTINATION / 'PACKAGE_MANIFEST.json')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
