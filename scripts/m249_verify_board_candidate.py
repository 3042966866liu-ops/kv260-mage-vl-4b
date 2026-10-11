#!/usr/bin/env python3
"""Verify exact closure and hashes of the M249 board candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.candidate.resolve()
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("package manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS" or manifest.get("gate") != "M249-KV260-A53-SSDLite-person-knife-speed-candidate":
        raise RuntimeError("package identity mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != int(manifest.get("file_count", -1)):
        raise RuntimeError("manifest count mismatch")
    expected = {"PACKAGE_MANIFEST.json", "PACKAGE_READY.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError(f"closure mismatch: missing={expected-actual}, extra={actual-expected}")
    if any(path.is_symlink() or "__pycache__" in path.parts or path.suffix == ".pyc" for path in root.rglob("*")):
        raise RuntimeError("symlink/cache forbidden")
    for item in entries:
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"member mismatch: {item['path']}")
    if sum(int(item["bytes"]) for item in entries) != int(manifest["total_bytes"]):
        raise RuntimeError("byte total mismatch")
    ready = json.loads((root / "PACKAGE_READY.json").read_text(encoding="utf-8"))
    if ready.get("status") != "READY" or ready.get("package_manifest_sha256") != args.expected_manifest_sha256:
        raise RuntimeError("PACKAGE_READY mismatch")
    predecessor = json.loads((root / "M249_PREDECESSOR_SUMMARY.json").read_text(encoding="utf-8"))
    if predecessor.get("status") != "PASS" or predecessor.get("board_execution_run") is not False:
        raise RuntimeError("predecessor summary mismatch")
    print(json.dumps({
        "status": "PASS",
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "package_manifest_sha256": args.expected_manifest_sha256,
    }))
    print("M249_BOARD_CANDIDATE_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
