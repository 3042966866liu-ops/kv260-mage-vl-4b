#!/usr/bin/env python3
"""Build a hash-closed, uncompressed local KV260 first-install archive.

This is an owner-side packaging tool, not a downloader or a license grant.
It refuses to overwrite an existing destination or archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or not p.parts or any(x in ("", ".", "..") for x in p.parts):
        raise ValueError(f"invalid package path: {value}")
    return p


def add(records: dict[str, dict], rel: str, source: Path, expected_sha: str, expected_bytes: int) -> None:
    safe_relative(rel)
    if rel in records:
        raise ValueError(f"duplicate package path: {rel}")
    if not source.is_file() or source.is_symlink():
        raise FileNotFoundError(f"source absent or symlink: {source}")
    records[rel] = {"source": source, "sha256": expected_sha, "bytes": expected_bytes}


def collect(historical_root: Path) -> dict[str, dict]:
    release = json.loads((ROOT / "manifests/release_files.json").read_text(encoding="utf-8"))
    assets = json.loads((ROOT / "manifests/external_assets.json").read_text(encoding="utf-8"))
    records: dict[str, dict] = {}
    for entry in release["files"]:
        rel = entry["path"]
        add(records, rel, ROOT / rel, entry["sha256"], entry["bytes"])
    for rel in ("manifests/release_files.json", "RELEASE_READINESS.md"):
        path = ROOT / rel
        add(records, rel, path, sha256(path), path.stat().st_size)
    for entry in assets["assets"]:
        dest = entry["destination"]
        if dest.endswith("/"):
            base = ROOT / dest
            add(records, dest + "SIXPORT_LAYOUT_MANIFEST.json",
                base / "SIXPORT_LAYOUT_MANIFEST.json", entry["layout_manifest_sha256"],
                entry["layout_manifest_bytes"])
            for shard in entry["files"]:
                add(records, dest + shard["path"], base / shard["path"],
                    shard["sha256"], shard["bytes"])
        else:
            add(records, dest, historical_root / entry.get("local_source_path", dest),
                entry["sha256"], entry["bytes"])
    return records


def copy_checked(records: dict[str, dict], dest: Path) -> list[dict]:
    output = []
    for rel, spec in sorted(records.items()):
        source = spec["source"]
        if source.stat().st_size != spec["bytes"] or sha256(source) != spec["sha256"]:
            raise ValueError(f"source identity mismatch: {rel}")
        target = dest / safe_relative(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as inp, target.open("xb") as out:
            shutil.copyfileobj(inp, out, length=4 << 20)
        if target.stat().st_size != spec["bytes"] or sha256(target) != spec["sha256"]:
            raise ValueError(f"copied identity mismatch: {rel}")
        output.append({"path": rel, "bytes": spec["bytes"], "sha256": spec["sha256"]})
    return output


def make_tar(dest: Path, archive: Path, entries: list[dict]) -> None:
    with archive.open("xb") as output, tarfile.open(fileobj=output, mode="w") as tar:
        for item in entries + [{"path": "INSTALL_PACKAGE_MANIFEST.json"}]:
            path = dest / item["path"]
            info = tarfile.TarInfo(item["path"])
            info.size = path.stat().st_size
            info.mode = 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with path.open("rb") as source:
                tar.addfile(info, source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-root", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    destination, archive, result = (x.resolve() for x in (args.destination, args.archive, args.result))
    if destination.exists() or archive.exists() or result.exists():
        parser.error("refusing to overwrite an existing output")
    if destination == ROOT or ROOT in destination.parents:
        parser.error("destination must be separate from the source checkout")
    records = collect(args.historical_root.resolve())
    destination.mkdir(parents=True)
    entries = copy_checked(records, destination)
    manifest = {"schema": "kv260-mage-vl-4b-prebuilt-install-v1", "build_id": "0x4D395832",
                "status": "FILES_VERIFIED_NOT_BOARD_TESTED", "file_count": len(entries),
                "total_bytes": sum(x["bytes"] for x in entries), "files": entries}
    manifest_path = destination / "INSTALL_PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    make_tar(destination, archive, entries)
    summary = {"status": "PASS_LOCAL_PACKAGE", "build_id": "0x4D395832", "directory": str(destination),
               "archive": str(archive), "archive_bytes": archive.stat().st_size,
               "archive_sha256": sha256(archive), "manifest_sha256": sha256(manifest_path),
               "file_count": len(entries), "payload_bytes": manifest["total_bytes"],
               "board_install_verified": False, "public_download_url": None}
    result.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
