#!/usr/bin/env python3
"""Verify the exact M190 board bootstrap after COM3 upload."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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
    manifest_path = args.root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M190 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("gate") != "M190-ARM64-runtime-board-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("M190 bootstrap identity mismatch")
    expected = {item["path"] for item in manifest["files"]} | {"PACKAGE_MANIFEST.json"}
    actual = {p.name for p in args.root.iterdir() if p.is_file()}
    if actual != expected:
        raise RuntimeError("M190 bootstrap closure mismatch")
    for item in manifest["files"]:
        path = args.root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M190 bootstrap member mismatch: {item['path']}")
    print("M190_RUNTIME_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
