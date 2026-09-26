#!/usr/bin/env python3
"""Verify the clean hash-locked M269 board delta without importing it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    manifest_path = candidate / "PACKAGE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "tellme-m269-delta-v1":
        raise RuntimeError("M269 manifest schema mismatch")
    if manifest.get("status") != "OFFLINE_PACKAGE_PASS_BOARD_MEMORY_TTFT_PENDING":
        raise RuntimeError("M269 package status mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != manifest.get("file_count"):
        raise RuntimeError("M269 manifest file count mismatch")
    if sorted(item["path"] for item in files) != manifest.get("path_whitelist"):
        raise RuntimeError("M269 path whitelist mismatch")
    expected_names = {"PACKAGE_MANIFEST.json"} | {item["path"] for item in files}
    actual_names = {
        path.relative_to(candidate).as_posix()
        for path in candidate.rglob("*")
        if path.is_file()
    }
    if actual_names != expected_names:
        raise RuntimeError(f"M269 package closure mismatch: {sorted(actual_names ^ expected_names)}")
    total = 0
    for item in files:
        path = candidate / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M269 member mismatch: {item['path']}")
        total += path.stat().st_size
    if total != manifest.get("total_bytes"):
        raise RuntimeError("M269 package byte count mismatch")
    forbidden = [
        path for path in candidate.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if forbidden:
        raise RuntimeError(f"M269 forbidden cache: {forbidden}")
    statuses = {
        "M264_GPU_RESOLUTION_SEMANTIC_SUITE_RESULT.json": "FAIL_OR_BASELINE_UNSUPPORTED_REQUIRES_RESOLUTION_SWEEP",
        "M265_GPU_RESOLUTION_SWEEP_RESULT.json": "FAIL_NO_TESTED_RESOLUTION_PASSES_SMALL_LABELLED_SUITE",
        "M266_GPU_MULTISCALE_SEMANTIC_RESULT.json": "FAIL_SMALL_LABELLED_MULTISCALE_SUITE",
        "M267_GPU_BINARY_MULTISCALE_RESULT.json": "PASS_SMALL_LABELLED_BINARY_MULTISCALE_SUITE_BOARD_PENDING",
        "M268_GPU_FAST_ROI_BINARY_RESULT.json": "PASS_HASH_LOCKED_FAST_ROI_BINARY_SUITE_BOARD_PENDING",
        "M269_GPU_EXACT_RUNTIME_SEMANTIC_RESULT.json": "PASS_EXACT_RUNTIME_VIEW_SMALL_BINARY_SUITE_BOARD_PENDING",
        "M269_EXACT_RUNTIME_OFFLINE_RESULT.json": "PASS_OFFLINE_EXACT_BOARD_MEMORY_TTFT_PENDING",
    }
    for name, status in statuses.items():
        value = json.loads((candidate / name).read_text(encoding="utf-8"))
        if value.get("status") != status:
            raise RuntimeError(f"M269 evidence status mismatch: {name}")
    for path in candidate.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    contract = (candidate / "m269_multiscale_contract.py").read_text(encoding="utf-8")
    runtime = (candidate / "m269_video_runtime.py").read_text(encoding="utf-8")
    vision = (candidate / "m269_multiscale_vision_runtime.py").read_text(encoding="utf-8")
    required = (
        "VISUAL_TOKENS = VIEW_COUNT * VISUAL_TOKENS_PER_VIEW",
        "DETAIL_SOURCE_SIZE = 224",
        "_area_downsample_2x",
        "np.ascontiguousarray(frame[offset:end, offset:end])",
    )
    if any(fragment not in contract for fragment in required) or "import cv2" in contract:
        raise RuntimeError("M269 NumPy-only view contract mismatch")
    if (
        "constrained_knife_decision(logits)" not in runtime
        or '"decode_calls": 0' not in runtime
        or ".decode(" in runtime
        or "expected_physical_calls(len(ids), 1)" not in runtime
    ):
        raise RuntimeError("M269 constrained no-decode runtime contract mismatch")
    if "[196, 2560]" not in vision or "M261-bounded-exact" not in vision:
        raise RuntimeError("M269 vision contract mismatch")
    print(
        "M269_CANDIDATE_VERIFY_PASS "
        f"files={manifest['file_count']} bytes={manifest['total_bytes']} "
        f"manifest_sha256={sha256(manifest_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
