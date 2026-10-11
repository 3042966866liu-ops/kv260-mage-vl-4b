#!/usr/bin/env python3
"""Verify the exact M249 COM3 bootstrap before network transfer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m249_bootstrap").resolve()
    if root != allowed:
        raise RuntimeError("unsafe bootstrap root")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M249-KV260-SSDLite-transfer-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("bootstrap identity mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != int(manifest.get("file_count", -1)):
        raise RuntimeError("bootstrap count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("bootstrap closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"bootstrap member mismatch: {item['path']}")
    print(json.dumps({"status": "PASS", "file_count": len(entries), "package_manifest_sha256": args.expected_manifest_sha256}))
    print("M249_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
