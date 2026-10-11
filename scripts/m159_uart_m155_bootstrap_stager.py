#!/usr/bin/env python3
"""Receive, verify and atomically stage the M155 bootstrap over COM3."""

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


EOF_MARKER = "__M159_M155_BOOTSTRAP_EOF__"
TOP = "m155_bootstrap"
M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package(root: Path, expected_manifest: str) -> dict:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != expected_manifest:
        raise RuntimeError("M159 package manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M159-M155-bootstrap-package" or manifest.get("status") != "PASS":
        raise RuntimeError("M159 package status mismatch")
    if manifest.get("candidate_build_id") != "0x4D395832" or manifest.get("m140_formal_result_sha256") != M140_SHA:
        raise RuntimeError("M159 package identity mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != 3:
        raise RuntimeError("M159 package file count mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in entries)}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M159 package closure mismatch")
    for item in entries:
        path = root / item["path"]
        if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M159 package member mismatch: {item['path']}")
    if sha256(root / "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json") != M140_SHA:
        raise RuntimeError("M159 staged M140 identity mismatch")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    if sha256(Path(__file__)) != args.self_sha256:
        raise RuntimeError("M159 stager self hash mismatch")
    output = args.output.resolve()
    allowed_parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
    if output.parent != allowed_parent or output.name != TOP:
        raise RuntimeError(f"unsafe M159 output: {output}")
    staging = output.with_name(output.name + ".staging")
    if output.exists() or staging.exists():
        raise RuntimeError("M159 output/staging already exists")

    attributes = termios.tcgetattr(sys.stdin.fileno())
    quiet = attributes.copy()
    quiet[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, quiet)
    encoded: list[str] = []
    print("M159_M155_BOOTSTRAP_UART_STAGER_READY", flush=True)
    try:
        while True:
            line = sys.stdin.readline()
            if line == "":
                raise RuntimeError("UART closed before M159 archive EOF")
            value = line.strip()
            if value == EOF_MARKER:
                break
            encoded.append(value)
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, attributes)
    payload = base64.b64decode("".join(encoded), validate=True)
    if hashlib.sha256(payload).hexdigest() != args.archive_sha256:
        raise RuntimeError("M159 UART archive hash mismatch")

    archive_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="m159_m155_", suffix=".tar.gz", delete=False) as handle:
            handle.write(payload)
            archive_path = Path(handle.name)
        staging.mkdir(parents=True)
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if not member.isfile() or not parts or parts[0] != TOP or ".." in parts:
                    raise RuntimeError(f"unsafe M159 archive member: {member.name}")
                target = (staging / Path(*parts[1:])).resolve()
                if staging.resolve() not in target.parents:
                    raise RuntimeError(f"M159 archive escape: {member.name}")
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"M159 archive member unreadable: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                os.chmod(target, member.mode & 0o777)
        manifest = verify_package(staging, args.package_manifest_sha256)
        os.replace(staging, output)
    except BaseException:
        if staging.exists() and staging.parent == output.parent:
            shutil.rmtree(staging)
        raise
    finally:
        if archive_path is not None and archive_path.exists():
            archive_path.unlink()
    print(json.dumps({"status": "PASS", "output": str(output), "files": len(manifest["files"]), "package_manifest_sha256": args.package_manifest_sha256}), flush=True)
    print("M159_M155_BOOTSTRAP_UART_STAGE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
