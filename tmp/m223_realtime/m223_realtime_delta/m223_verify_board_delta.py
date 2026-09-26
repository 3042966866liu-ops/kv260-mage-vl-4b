#!/usr/bin/env python3
"""Verify the exact M223 COM3 service delta closure."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--expected-manifest-sha256", required=True)
args = parser.parse_args()
root = args.root.resolve()
manifest_path = root / "PACKAGE_MANIFEST.json"
if sha(manifest_path) != args.expected_manifest_sha256:
    raise RuntimeError("M223 package manifest hash mismatch")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
expected = {item["path"] for item in manifest["files"]} | {"PACKAGE_MANIFEST.json"}
actual = {
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file()
}
if (
    manifest.get("gate") != "M223-realtime-service-board-delta"
    or manifest.get("status") != "PASS"
    or actual != expected
):
    raise RuntimeError("M223 package identity/closure mismatch")
for item in manifest["files"]:
    path = root / item["path"]
    if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
        raise RuntimeError(f"M223 member mismatch: {item['path']}")
print("M223_BOARD_DELTA_VERIFY_PASS")

