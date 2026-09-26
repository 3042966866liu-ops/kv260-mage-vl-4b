#!/usr/bin/env python3
"""Fail-closed hash and source-closure verifier for an M259 delta package."""

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
    if observed_manifest != args.expected_manifest_sha256.lower():
        raise RuntimeError(
            f"M259 manifest hash mismatch {observed_manifest}/"
            f"{args.expected_manifest_sha256.lower()}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_paths = {item["path"] for item in manifest["files"]}
    observed_paths = {
        str(path.relative_to(candidate)).replace("\\", "/")
        for path in candidate.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    if observed_paths != expected_paths:
        raise RuntimeError(
            f"M259 path closure mismatch missing={sorted(expected_paths-observed_paths)} "
            f"extra={sorted(observed_paths-expected_paths)}"
        )
    total = 0
    for item in manifest["files"]:
        path = candidate / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M259 file identity mismatch: {item['path']}")
        total += path.stat().st_size
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if total != int(manifest["total_bytes"]):
        raise RuntimeError("M259 package byte count mismatch")
    banned = [
        str(path.relative_to(candidate)) for path in candidate.rglob("*")
        if path.name == "__pycache__" or path.suffix == ".pyc"
    ]
    if banned:
        raise RuntimeError(f"M259 banned cache files: {banned}")
    result = json.loads(
        (candidate / "M259_PREVISION_KEYFRAME_OFFLINE_RESULT.json")
        .read_text(encoding="utf-8")
    )
    if (
        result.get("status") != "PASS_OFFLINE_FINITE_SEMANTIC_AND_BOARD_PENDING"
        or result.get("runtime_import_closure_pass") is not True
        or result.get("active_board_service_changed") is not False
    ):
        raise RuntimeError("M259 offline evidence contract mismatch")
    print(
        "M259_PACKAGE_VERIFY_PASS "
        f"files={len(expected_paths)} bytes={total} manifest_sha256={observed_manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
