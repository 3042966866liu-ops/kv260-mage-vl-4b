#!/usr/bin/env python3
"""Verify the fixed M184 board bootstrap before temporary network setup."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
EXPECTED_M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"
EXPECTED_PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m184_bootstrap").resolve()
    if root != allowed:
        raise RuntimeError("M184 unsafe bootstrap root")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M184 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M184-M181-video-PC-push-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("M184 bootstrap identity mismatch")
    if manifest.get("m182_result_sha256") != EXPECTED_M182_SHA or manifest.get("video_package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
        raise RuntimeError("M184 bootstrap predecessor/package mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 4 or int(manifest.get("file_count", -1)) != 4:
        raise RuntimeError("M184 bootstrap file count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M184 bootstrap closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M184 bootstrap member mismatch: {item['path']}")
    predecessor = root / "M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json"
    predecessor_json = json.loads(predecessor.read_text(encoding="utf-8"))
    if sha256(predecessor) != EXPECTED_M182_SHA or predecessor_json.get("status") != "PASS_OFFLINE_VIDEO_CANDIDATE_BOARD_NOT_EXECUTED":
        raise RuntimeError("M184 staged predecessor mismatch")
    print(json.dumps({"status": "PASS", "file_count": 4, "package_manifest_sha256": args.expected_manifest_sha256}))
    print("M184_VIDEO_PUSH_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
