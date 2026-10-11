#!/usr/bin/env python3
"""Verify the fixed M163 board receiver bootstrap before network mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m163_bootstrap").resolve()
    if root != allowed:
        raise RuntimeError("M163 unsafe bootstrap root")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M163 bootstrap manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M163-M120-PC-push-bootstrap" or manifest.get("status") != "PASS":
        raise RuntimeError("M163 bootstrap identity mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 4:
        raise RuntimeError("M163 bootstrap file count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M163 bootstrap closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M163 bootstrap member mismatch: {item['path']}")
    print(json.dumps({"status": "PASS", "file_count": 4, "package_manifest_sha256": args.expected_manifest_sha256}))
    print("M163_PUSH_BOOTSTRAP_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
