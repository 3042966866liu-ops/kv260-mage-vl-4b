#!/usr/bin/env python3
"""Fail-closed verifier for a clean M260 repeated-window cache package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    manifest_path = candidate / "PACKAGE_MANIFEST.json"
    observed_manifest = sha256(manifest_path)
    expected_manifest = args.expected_manifest_sha256.lower()
    if observed_manifest != expected_manifest:
        raise RuntimeError(
            f"M260 manifest hash mismatch {observed_manifest}/{expected_manifest}"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "tellme-m260-delta-v1":
        raise RuntimeError("M260 package schema mismatch")
    expected_paths = {item["path"] for item in manifest["files"]}
    observed_paths = {
        str(path.relative_to(candidate)).replace("\\", "/")
        for path in candidate.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    if observed_paths != expected_paths:
        raise RuntimeError(
            f"M260 path closure mismatch missing={sorted(expected_paths-observed_paths)} "
            f"extra={sorted(observed_paths-expected_paths)}"
        )

    total = 0
    for item in manifest["files"]:
        path = candidate / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M260 file identity mismatch: {item['path']}")
        total += path.stat().st_size
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if total != int(manifest["total_bytes"]):
        raise RuntimeError("M260 package byte count mismatch")
    banned = [
        str(path.relative_to(candidate))
        for path in candidate.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if banned:
        raise RuntimeError(f"M260 banned cache files: {banned}")

    result = json.loads(
        (candidate / "M260_CACHED_W4_OFFLINE_RESULT.json").read_text(encoding="utf-8")
    )
    if (
        result.get("status") != "PASS_OFFLINE_EXACT_BOARD_MEMORY_AND_SPEED_PENDING"
        or result.get("runtime_import_closure_pass") is not True
        or result.get("warm_output_bit_exact_to_cold") is not True
        or result.get("active_board_service_changed") is not False
    ):
        raise RuntimeError("M260 offline evidence contract mismatch")
    if int(result["warm_evidence"]["cache_hits"]) != 98:
        raise RuntimeError("M260 warm cache-hit contract mismatch")
    if int(result["cold_evidence"]["cache_misses"]) != 98:
        raise RuntimeError("M260 cold cache-miss contract mismatch")

    print(
        "M260_PACKAGE_VERIFY_PASS "
        f"files={len(expected_paths)} bytes={total} "
        f"manifest_sha256={observed_manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
