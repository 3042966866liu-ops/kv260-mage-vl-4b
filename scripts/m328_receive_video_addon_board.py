#!/usr/bin/env python3
"""Receive only the hash-locked M328 video add-on by temporary peer Ethernet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import tarfile


DEST = Path("/home/ubuntu/tellme_release_video_addon_20260926_v3")
PARTIAL = Path("/home/ubuntu/tellme_release_video_addon_20260926_v3.partial")
RELEASE = Path("/home/ubuntu/tellme_release_install_20260926")
TEMP_ADDRESS = "192.168.0.2/24"
PEER = "192.168.0.10"
PORT = 49328
WHITELIST = {
    "PACKAGE_MANIFEST.json", "run_fixed_video.py",
    "fixtures/frame_00_0068_rgb448.npy", "fixtures/frame_01_0102_rgb448.npy",
    "fixtures/frame_02_0137_rgb448.npy", "fixtures/frame_03_0171_rgb448.npy",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class HashingReader:
    def __init__(self, source):
        self.source = source
        self.hash = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        chunk = self.source.read(size)
        self.hash.update(chunk)
        self.count += len(chunk)
        return chunk


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--archive-bytes", type=int, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    if (os.geteuid() != 0 or subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0
            or DEST.exists() or PARTIAL.exists()):
        raise RuntimeError("root/same-terminal sudo/clean add-on destination required")
    if (not RELEASE.is_dir() or
            digest(RELEASE / "INSTALL_PACKAGE_MANIFEST.json") !=
            "fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e"):
        raise RuntimeError("independent v7 base install identity mismatch")
    before = subprocess.check_output(["ip", "-4", "-o", "addr", "show", "dev", "eth0"], text=True)
    if "192.168.0.2/" in before:
        raise RuntimeError("temporary board address preexists")
    added = False
    try:
        subprocess.run(["ip", "addr", "add", TEMP_ADDRESS, "dev", "eth0"], check=True)
        added = True
        PARTIAL.mkdir()
        with socket.create_connection((PEER, PORT), timeout=30) as conn:
            conn.settimeout(120)
            with conn.makefile("rb") as stream:
                reader = HashingReader(stream)
                with tarfile.open(mode="r|", fileobj=reader) as archive:
                    seen = set()
                    for member in archive:
                        rel = PurePosixPath(member.name)
                        if (not member.isfile() or member.name not in WHITELIST or
                                rel.is_absolute() or ".." in rel.parts or member.name in seen or
                                member.size > 3_000_000):
                            raise RuntimeError(f"unsafe or duplicate add-on member: {member.name}")
                        seen.add(member.name)
                        target = PARTIAL.joinpath(*rel.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = archive.extractfile(member)
                        if source is None:
                            raise RuntimeError(f"member data missing: {member.name}")
                        with source, target.open("xb") as output:
                            while True:
                                chunk = source.read(4 << 20)
                                if not chunk:
                                    break
                                output.write(chunk)
                        if target.stat().st_size != member.size:
                            raise RuntimeError(f"member size mismatch: {member.name}")
                while reader.read(4 << 20):
                    pass
        if seen != WHITELIST or reader.count != args.archive_bytes or reader.hash.hexdigest() != args.archive_sha256:
            raise RuntimeError("add-on archive identity or whitelist mismatch")
        manifest_path = PARTIAL / "PACKAGE_MANIFEST.json"
        if digest(manifest_path) != args.manifest_sha256:
            raise RuntimeError("add-on manifest identity mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema") != "tellme-m328-release-fixed-video-addon-v1" or
                manifest.get("build_id") != "0x4D395832" or
                manifest.get("file_count") != 5 or
                len(manifest.get("files", [])) != 5):
            raise RuntimeError("add-on manifest schema/count mismatch")
        for item in manifest["files"]:
            path = PARTIAL / item["path"]
            if item["path"] not in seen or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
                raise RuntimeError(f"add-on payload mismatch: {item['path']}")
        PARTIAL.rename(DEST)
        print(json.dumps({"status": "PASS_ADDON_INSTALLED_NOT_YET_EXECUTED", "root": str(DEST),
                          "archive_sha256": args.archive_sha256, "manifest_sha256": args.manifest_sha256,
                          "file_count": 5, "payload_bytes": manifest["payload_bytes"]}), flush=True)
        print("M328_VIDEO_ADDON_INSTALL_PASS", flush=True)
    finally:
        if added:
            subprocess.run(["ip", "addr", "del", TEMP_ADDRESS, "dev", "eth0"], check=True)


if __name__ == "__main__":
    main()
