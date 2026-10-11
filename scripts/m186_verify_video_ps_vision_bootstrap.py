#!/usr/bin/env python3
"""Verify the fixed M186 PS-vision board-gate bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
EXPECTED_M184_SHA = "790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84"
EXPECTED_PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if root != Path("/home/ubuntu/tellme_m120_m89x2_20260901/m186_gate").resolve():
        raise RuntimeError("M186 unsafe bootstrap root")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M186 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M186-M181-PS-vision-board-gate-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("M186 bootstrap identity mismatch")
    if manifest.get("m184_formal_result_sha256") != EXPECTED_M184_SHA or manifest.get("video_package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
        raise RuntimeError("M186 predecessor/package mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 4 or int(manifest.get("file_count", -1)) != 4:
        raise RuntimeError("M186 bootstrap file count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M186 bootstrap closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M186 bootstrap member mismatch: {item['path']}")
    predecessor = root / "M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json"
    value = json.loads(predecessor.read_text(encoding="utf-8"))
    if sha256(predecessor) != EXPECTED_M184_SHA or value.get("status") != "PASS" or value.get("package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
        raise RuntimeError("M186 staged M184 result mismatch")
    print(json.dumps({"status": "PASS", "file_count": 4, "package_manifest_sha256": args.expected_manifest_sha256}))
    print("M186_PS_VISION_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
