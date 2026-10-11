#!/usr/bin/env python3
"""Fail-closed identity gate for a staged M89-X board candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, size: int, expected_hash: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing file: {path}")
    if path.stat().st_size != size:
        raise RuntimeError(f"size mismatch: {path}")
    observed = sha256(path)
    if observed != expected_hash:
        raise RuntimeError(f"hash mismatch: {path}: {observed} != {expected_hash}")


def verify_layout(root: Path, expected_manifest_hash: str, expected_modules: int) -> dict:
    manifest_path = root / "SIXPORT_LAYOUT_MANIFEST.json"
    if sha256(manifest_path) != expected_manifest_hash:
        raise RuntimeError(f"layout manifest hash mismatch: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError(f"unsupported layout format: {root}")
    if int(manifest.get("module_count", -1)) != expected_modules:
        raise RuntimeError(f"module count mismatch: {root}")
    files = manifest.get("files", [])
    if len(files) != 4:
        raise RuntimeError(f"layout must have four shards: {root}")
    for index, item in enumerate(files):
        if item.get("path") != f"weights{index}.bin":
            raise RuntimeError(f"layout shard order mismatch: {root}")
        verify_file(root / item["path"], int(item["bytes"]), item["sha256"])
    return {"manifest_sha256": expected_manifest_hash, "module_count": expected_modules,
            "mapped_bytes": sum(int(item["bytes"]) for item in files)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--language", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    args = parser.parse_args()
    manifest_path = args.candidate / "PACKAGE_MANIFEST.json"
    observed_manifest_hash = sha256(manifest_path)
    if observed_manifest_hash != args.expected_package_manifest_sha256:
        raise RuntimeError("package manifest identity mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_OFFLINE_BOARD_CANDIDATE_PACKAGE":
        raise RuntimeError("candidate status is not PASS")
    if manifest.get("deployed") is not False or manifest.get("board_state_changed") is not False:
        raise RuntimeError("candidate manifest already claims board mutation")
    for item in manifest.get("files", []):
        verify_file(args.candidate / item["path"], int(item["bytes"]), item["sha256"])
    payloads = {item["label"]: item for item in manifest.get("large_payloads", [])}
    language = verify_layout(args.language, payloads["language"]["manifest_sha256"], 252)
    head = verify_layout(args.head, payloads["lm_head"]["manifest_sha256"], 1)
    result = {"status": "PASS", "marker": "M89X_STAGED_BOARD_CANDIDATE_IDENTITY_PASS",
              "package_manifest_sha256": observed_manifest_hash,
              "package_files": len(manifest.get("files", [])),
              "language": language, "lm_head": head}
    print(json.dumps(result, indent=2))
    print(result["marker"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
