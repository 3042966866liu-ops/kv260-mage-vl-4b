#!/usr/bin/env python3
"""Verify the exact M218 COM3 dual-source service delta closure."""

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
manifest_path = args.root / "PACKAGE_MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if sha(manifest_path) != args.expected_manifest_sha256:
    raise RuntimeError("M218 package manifest hash mismatch")
expected = {item["path"]: item for item in manifest["files"]}
actual = {
    str(path.relative_to(args.root)).replace("\\", "/")
    for path in args.root.rglob("*")
    if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
}
if (
    manifest.get("gate") != "M218-dual-source-service-board-delta"
    or manifest.get("status") != "PASS"
    or actual != set(expected)
):
    raise RuntimeError("M218 package identity/closure mismatch")
for name, item in expected.items():
    path = args.root / name
    if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
        raise RuntimeError(f"M218 member mismatch: {name}")
if any("__pycache__" in name or name.endswith((".pyc", ".log", ".partial")) for name in actual):
    raise RuntimeError("M218 forbidden cache/log member")
print("M218_BOARD_DELTA_VERIFY_PASS")
