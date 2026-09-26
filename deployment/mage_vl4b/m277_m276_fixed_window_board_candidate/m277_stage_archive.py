#!/usr/bin/env python3
"""Safely expand and hash-check the M277 archive into its fixed board path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    fixed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m277_m276_fixed_window_candidate")
    if args.destination != fixed or args.destination.exists():
        raise RuntimeError("M277 fixed destination mismatch or already exists")
    if sha256(args.archive) != args.archive_sha256:
        raise RuntimeError("M277 archive hash mismatch")
    partial = args.destination.with_name(args.destination.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=False)
    try:
        with tarfile.open(args.archive, "r:*") as archive:
            members = archive.getmembers()
            for member in members:
                pure = PurePosixPath(member.name)
                if member.issym() or member.islnk() or pure.is_absolute() or ".." in pure.parts:
                    raise RuntimeError(f"M277 unsafe archive member {member.name}")
            archive.extractall(partial, filter="data")
        manifest_path = partial / "PACKAGE_MANIFEST.json"
        if sha256(manifest_path) != args.manifest_sha256:
            raise RuntimeError("M277 staged manifest hash mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = sorted(item["path"] for item in manifest["files"])
        observed = sorted(
            path.relative_to(partial).as_posix()
            for path in partial.rglob("*")
            if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
        )
        if observed != expected:
            raise RuntimeError("M277 staged file closure mismatch")
        for item in manifest["files"]:
            path = partial / item["path"]
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M277 staged payload mismatch {item['path']}")
        os.replace(partial, args.destination)
    except Exception:
        if partial.exists():
            shutil.rmtree(partial)
        raise
    print(
        f"M277_STAGE_ARCHIVE_PASS files={manifest['file_count']} "
        f"bytes={manifest['total_bytes']} manifest={args.manifest_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

