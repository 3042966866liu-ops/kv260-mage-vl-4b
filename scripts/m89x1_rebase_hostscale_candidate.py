#!/usr/bin/env python3
"""Rebase the locally verified HS64 files onto the exact remote M89-X1 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def index(manifest: dict) -> dict[str, dict]:
    return {item["path"]: item for item in manifest["files"]}


def verify(root: Path, manifest: dict) -> None:
    expected = {"PACKAGE_MANIFEST.json"}
    for item in manifest["files"]:
        expected.add(item["path"])
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"candidate file identity mismatch: {item['path']}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError(f"candidate closure mismatch extra={sorted(actual-expected)} missing={sorted(expected-actual)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-manifest", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    remote_path = args.remote_manifest.resolve()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    remote_sha = sha256(remote_path)
    if remote_sha != "c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50":
        raise RuntimeError(f"unexpected remote manifest identity: {remote_sha}")
    remote = load(remote_path)
    local = load(source / "PACKAGE_MANIFEST.json")
    verify(source, local)
    remote_files, local_files = index(remote), index(local)
    removed = sorted(set(remote_files) - set(local_files))
    if removed:
        raise RuntimeError(f"hostscale candidate removes baseline files: {removed}")
    unchanged = sorted(set(remote_files) & set(local_files))
    changed = sorted(path for path in unchanged if remote_files[path]["sha256"] != local_files[path]["sha256"])
    for path in unchanged:
        if path not in changed and remote_files[path] != local_files[path]:
            raise RuntimeError(f"unchanged manifest entry differs: {path}")
    shutil.copytree(source, output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest_path = output / "PACKAGE_MANIFEST.json"
    manifest = load(manifest_path)
    manifest["baseline_manifest_sha256"] = remote_sha
    manifest["status"] = "PASS_OFFLINE_BOARD_ANCHORED_CANDIDATE_PACKAGE"
    manifest["marker"] = "M89X1_HOST_SCALE64_BOARD_ANCHORED_PACKAGE_PASS"
    manifest["remote_baseline_audit"] = {
        "manifest_sha256": remote_sha,
        "declared_file_count": len(remote_files),
        "listed_files_verified_on_board": True,
        "stable_baseline_modified": False,
        "runtime_cache_extras_excluded_from_new_candidate": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify(output, manifest)
    result = {
        "gate": "M89-X1-HS64-board-anchored-package",
        "status": "PASS",
        "remote_baseline_manifest_sha256": remote_sha,
        "candidate_manifest_sha256": sha256(manifest_path),
        "changed_against_remote": changed,
        "added_against_remote": sorted(set(local_files) - set(remote_files)),
        "file_count": len(manifest["files"]),
        "total_bytes": sum(int(item["bytes"]) for item in manifest["files"]),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
