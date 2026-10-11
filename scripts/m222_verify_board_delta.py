#!/usr/bin/env python3
"""Verify the exact M222 ARM64 decoder micro-gate package."""

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
    raise RuntimeError("M222 package manifest hash mismatch")
expected = {item["path"]: item for item in manifest["files"]}
actual = {
    path.relative_to(args.root).as_posix()
    for path in args.root.rglob("*")
    if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
}
if manifest.get("gate") != "M222-ARM64-decoder-microgate-package" or actual != set(expected):
    raise RuntimeError("M222 package identity/closure mismatch")
for name, item in expected.items():
    path = args.root / name
    if path.stat().st_size != int(item["bytes"]) or sha(path) != item["sha256"]:
        raise RuntimeError(f"M222 package member mismatch: {name}")
if any("__pycache__" in name or name.endswith((".pyc", ".log", ".partial")) for name in actual):
    raise RuntimeError("M222 forbidden package member")
print("M222_BOARD_DELTA_VERIFY_PASS")

