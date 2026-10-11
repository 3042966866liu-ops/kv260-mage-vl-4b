#!/usr/bin/env python3
"""Verify the clean M202 UART bootstrap on the board before execution."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
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
        raise RuntimeError("M202 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {item["path"] for item in manifest["files"]}
    observed = {
        path.relative_to(root).as_posix() for path in root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
        and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if observed != expected:
        raise RuntimeError(f"M202 bootstrap path closure mismatch missing={expected-observed} extra={observed-expected}")
    for item in manifest["files"]:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M202 bootstrap member mismatch: {item['path']}")
    print("M202_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
