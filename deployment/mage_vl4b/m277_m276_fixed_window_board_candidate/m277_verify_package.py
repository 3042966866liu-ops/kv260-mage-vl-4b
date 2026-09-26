#!/usr/bin/env python3
"""Verify the M277/M276 package, frozen evidence and runtime closure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
EXPECTED = {
    "M275_GPU_EXACT_PROMPT_SWEEP_RESULT.json": "234bba1a9b2796a2a231efd539427d39435715bda69a4f401b87f9273defb5bd",
    "M276_EXACT_PROMPT_RUNTIME_OFFLINE_RESULT.json": "5987ae3c517197f791c5afe3ad78f0f902d4ba8fc528c4a4e216aaf2b7adc844",
    "M273_GPU_EXACT_LATEST_BINARY_RESULT.json": "23e53a0e020c169e5dcaf4a191835bc0f37dba7e58026495b5c37cb23eea36c7",
    "M273_EXACT_RUNTIME_OFFLINE_RESULT.json": "c656fcdd20b93ee6fa6811a50c4857c0932d112bcb84d407813b0c8518b31b7c",
    "M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json": "8e768b513664ab1b3a6caaf5dfe00bb39ba1e186ee1d8f27780d2a91e96f18d9",
    "M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json": "b134fc00f7e2be60d9444f0e81203561972455d78907cdb6515462a98243e392",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--runtime-imports", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M277 manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "tellme-m277-m276-fixed-window-v1"
        or manifest.get("status") != "PASS_OFFLINE_READY_FOR_M277_BOARD_GATE"
    ):
        raise RuntimeError("M277 manifest identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != manifest.get("file_count"):
        raise RuntimeError("M277 manifest count mismatch")
    expected_paths = sorted(item["path"] for item in files)
    observed_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    )
    if observed_paths != expected_paths:
        raise RuntimeError("M277 file closure mismatch")
    for item in files:
        path = root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M277 payload mismatch {item['path']}")
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if any(path.suffix == ".pyc" or "__pycache__" in path.parts for path in root.rglob("*")):
        raise RuntimeError("M277 forbidden bytecode/cache path")
    for name, expected_hash in EXPECTED.items():
        if sha256(root / name) != expected_hash:
            raise RuntimeError(f"M277 frozen evidence mismatch {name}")
    exact = json.loads((root / "M276_EXACT_PROMPT_RUNTIME_OFFLINE_RESULT.json").read_text(encoding="utf-8"))
    memory = json.loads((root / "M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json").read_text(encoding="utf-8"))
    if exact.get("status") != "PASS_OFFLINE_EXACT_BOARD_TTFT_PENDING":
        raise RuntimeError("M277 M276 predecessor status mismatch")
    if exact.get("prompt_tokens") != 159 or exact.get("logical_calls") != 778:
        raise RuntimeError("M277 M276 geometry mismatch")
    if memory.get("status") != "PASS_READ_ONLY_HEADROOM":
        raise RuntimeError("M277 memory predecessor status mismatch")
    if args.runtime_imports:
        import m276_m254_video_server  # noqa: F401
        import m222_video_server
        import video_server

        if m222_video_server.M222PSVisionRuntime.__name__ != "M273LatestPSVisionRuntime":
            raise RuntimeError("M277 vision import identity mismatch")
        if video_server.M120VideoRuntime.__name__ != "M276ShortPromptBinaryRuntime":
            raise RuntimeError("M277 video import identity mismatch")
    print(
        f"M277_PACKAGE_VERIFY_PASS files={manifest['file_count']} "
        f"bytes={manifest['total_bytes']} imports={args.runtime_imports}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

