#!/usr/bin/env python3
"""Verify the clean M162 board-control bootstrap before any network mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m162_bootstrap_v2").resolve()
    if root != allowed:
        raise RuntimeError("M162 unsafe bootstrap root")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M162 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M162-M120-network-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("M162 bootstrap identity mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 4:
        raise RuntimeError("M162 bootstrap file count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M162 bootstrap closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M162 bootstrap member mismatch: {item['path']}")
    print(json.dumps({"status": "PASS", "file_count": len(entries), "package_manifest_sha256": args.expected_manifest_sha256}))
    print("M162_NETWORK_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
