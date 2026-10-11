#!/usr/bin/env python3
"""Build a clean whitelisted M269 board delta over the verified M261 package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m269_multiscale_binary_source"
M261_PACKAGE = ROOT / "deployment/mage_vl4b/m261_bounded_cache_board_candidate"
M246 = ROOT / "deployment/mage_vl4b/m246_knife_binary_source/m246_knife_binary.py"
DESTINATION = ROOT / "deployment/mage_vl4b/m269_multiscale_binary_board_candidate"
PARTIAL = DESTINATION.with_name(DESTINATION.name + ".partial")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if DESTINATION.exists() or PARTIAL.exists():
        raise RuntimeError("M269 destination/partial already exists; refuse overwrite")
    m261_manifest_path = M261_PACKAGE / "PACKAGE_MANIFEST.json"
    m261_manifest = json.loads(m261_manifest_path.read_text(encoding="utf-8"))
    if m261_manifest.get("status") != "OFFLINE_PACKAGE_PASS_BOARD_MEMORY_AND_SPEED_PENDING":
        raise RuntimeError("M269 exact M261 predecessor package not accepted")
    inherited = {
        path.name: path
        for path in M261_PACKAGE.iterdir()
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    evidence_names = (
        "M264_GPU_RESOLUTION_SEMANTIC_SUITE_RESULT.json",
        "M265_GPU_RESOLUTION_SWEEP_RESULT.json",
        "M266_GPU_MULTISCALE_SEMANTIC_RESULT.json",
        "M267_GPU_BINARY_MULTISCALE_RESULT.json",
        "M268_GPU_FAST_ROI_BINARY_RESULT.json",
        "M269_GPU_EXACT_RUNTIME_SEMANTIC_RESULT.json",
        "M269_EXACT_RUNTIME_OFFLINE_RESULT.json",
    )
    whitelist = {
        **inherited,
        "m246_knife_binary.py": M246,
        **{path.name: path for path in SOURCE.iterdir() if path.is_file()},
        **{name: ROOT / "deployment/mage_vl4b" / name for name in evidence_names},
    }
    for name, path in whitelist.items():
        if not path.is_file():
            raise RuntimeError(f"M269 source missing: {name}/{path}")
    offline = json.loads(
        whitelist["M269_EXACT_RUNTIME_OFFLINE_RESULT.json"].read_text(encoding="utf-8")
    )
    if (
        offline.get("status") != "PASS_OFFLINE_EXACT_BOARD_MEMORY_TTFT_PENDING"
        or offline.get("warm_output_bit_exact_to_cold") is not True
        or offline.get("decode_calls") != 0
    ):
        raise RuntimeError("M269 exact runtime evidence is not accepted")

    PARTIAL.mkdir(parents=False)
    try:
        entries = []
        for relative, source in sorted(whitelist.items()):
            destination = PARTIAL / relative
            shutil.copy2(source, destination)
            entries.append({
                "path": relative,
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            })
        manifest = {
            "schema": "tellme-m269-delta-v1",
            "status": "OFFLINE_PACKAGE_PASS_BOARD_MEMORY_TTFT_PENDING",
            "classification": (
                "Hash-locked M261+M269 source/evidence delta only; not deployed, board-memory "
                "accepted, board-timed, target-scene calibrated, Web-promoted or realtime accepted."
            ),
            "predecessor_m261_manifest_sha256": sha256(m261_manifest_path),
            "files": entries,
            "file_count": len(entries),
            "total_bytes": sum(item["bytes"] for item in entries),
            "path_whitelist": sorted(whitelist),
            "external_runtime_modules_locked_by_predecessors": [
                "m254_video_server", "m243_video_server", "m222_video_server",
                "video_server", "video_language_runtime", "m238_prefill_runtime",
                "m241_video_language_runtime",
            ],
            "new_board_runtime_dependencies": ["numpy"],
            "cv2_required_on_board": False,
            "decode_calls": 0,
            "visual_tokens": 196,
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
        "M269_PACKAGE_BUILD_PASS "
        f"files={manifest['file_count']} bytes={manifest['total_bytes']} "
        f"manifest_sha256={sha256(DESTINATION / 'PACKAGE_MANIFEST.json')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
