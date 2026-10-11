#!/usr/bin/env python3
"""Receive, verify and atomically stage the complete M136 package over UART."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import termios
from pathlib import Path


EOF_MARKER = "__M136_M120_PACKAGE_EOF__"
TOP = "m120_text4b_board_candidate"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package(root: Path, expected_manifest: str) -> dict:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != expected_manifest:
        raise RuntimeError("package manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in manifest["files"])}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != expected:
        raise RuntimeError("package closure mismatch")
    for item in manifest["files"]:
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"package file mismatch: {item['path']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    if sha256(Path(__file__)) != args.self_sha256:
        raise RuntimeError("stager self hash mismatch")
    output = args.output.resolve()
    home = Path("/home/ubuntu").resolve()
    if home not in output.parents or output.name != TOP:
        raise RuntimeError(f"unsafe output path: {output}")
    if output.exists() or Path(str(output) + ".staging").exists():
        raise RuntimeError("output/staging already exists")

    attributes = termios.tcgetattr(sys.stdin.fileno())
    quiet = attributes.copy()
    quiet[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, quiet)
    encoded: list[str] = []
    print("M136_M120_UART_STAGER_READY", flush=True)
    try:
        while True:
            line = sys.stdin.readline()
            if line == "":
                raise RuntimeError("UART closed before archive EOF")
            text = line.strip()
            if text == EOF_MARKER:
                break
            encoded.append(text)
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, attributes)
    payload = base64.b64decode("".join(encoded), validate=True)
    if hashlib.sha256(payload).hexdigest() != args.archive_sha256:
        raise RuntimeError("UART archive hash mismatch")

    staging = Path(str(output) + ".staging")
    archive_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="m136_m120_", suffix=".tar.gz", delete=False) as handle:
            handle.write(payload)
            archive_path = Path(handle.name)
        staging.mkdir(parents=True)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                parts = Path(member.name).parts
                if not member.isfile() or not parts or parts[0] != TOP or ".." in parts:
                    raise RuntimeError(f"unsafe archive member: {member.name}")
                target = (staging / Path(*parts[1:])).resolve()
                if staging.resolve() not in target.parents:
                    raise RuntimeError(f"archive escape: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"archive member unreadable: {member.name}")
                with target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                os.chmod(target, member.mode & 0o777)
        manifest = verify_package(staging, args.package_manifest_sha256)
        os.replace(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    finally:
        if archive_path is not None and archive_path.exists():
            archive_path.unlink()
    print(json.dumps({
        "status": "PASS", "output": str(output), "files": len(manifest["files"]),
        "package_manifest_sha256": args.package_manifest_sha256,
    }), flush=True)
    print("M136_M120_UART_STAGE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

