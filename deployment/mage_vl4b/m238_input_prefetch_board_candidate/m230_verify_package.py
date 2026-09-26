#!/usr/bin/env python3
"""Verify the clean M230 delta package before any overlay command."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M230 manifest identity mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {entry["path"]: entry for entry in manifest["files"]}
    observed = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    )
    if observed != sorted(expected):
        raise RuntimeError(f"M230 package path whitelist mismatch: {observed}")
    if any("__pycache__" in path or path.endswith(".pyc") for path in observed):
        raise RuntimeError("M230 package contains Python cache files")
    total = 0
    for relative in observed:
        path = root / relative
        record = expected[relative]
        if path.stat().st_size != int(record["bytes"]) or sha256(path) != record["sha256"]:
            raise RuntimeError(f"M230 package file identity mismatch: {relative}")
        total += path.stat().st_size
    if len(observed) != int(manifest["file_count"]) or total != int(manifest["total_file_bytes"]):
        raise RuntimeError("M230 package count/bytes mismatch")
    print(f"M230_BOARD_PACKAGE_VERIFY_PASS files={len(observed)} bytes={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
