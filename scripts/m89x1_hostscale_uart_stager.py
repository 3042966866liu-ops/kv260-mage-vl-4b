#!/usr/bin/env python3
"""Receive and atomically stage an HS64 candidate over an authenticated UART."""

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


EOF_MARKER = "__M89X1_HS64_DELTA_EOF__"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_cache_path(path: str) -> bool:
    parts = Path(path).parts
    return "__pycache__" in parts or path.endswith(".pyc")


def verify_package(root: Path, expected_manifest_sha: str, *, allow_cache_extras: bool = False) -> dict:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != expected_manifest_sha:
        raise RuntimeError("package manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {"PACKAGE_MANIFEST.json"}
    for item in manifest["files"]:
        relative = item["path"]
        expected.add(relative)
        path = root / relative
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"package file identity mismatch: {relative}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    extra = actual - expected
    non_cache_extra = {path for path in extra if not is_cache_path(path)}
    if expected - actual or non_cache_extra or (extra and not allow_cache_extras):
        raise RuntimeError(
            f"package closure mismatch extra={sorted(extra)} "
            f"missing={sorted(expected-actual)}"
        )
    if not allow_cache_extras and any(
        "__pycache__" in path.parts or path.suffix == ".pyc" for path in root.rglob("*")
    ):
        raise RuntimeError("forbidden Python cache in package")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("--baseline-manifest-sha256", required=True)
    parser.add_argument("--candidate-manifest-sha256", required=True)
    parser.add_argument("--delta-sha256", required=True)
    args = parser.parse_args()
    if sha256(Path(__file__)) != args.self_sha256:
        raise RuntimeError("stager self hash mismatch")
    baseline, output = args.baseline.resolve(), args.output.resolve()
    home = Path("/home/ubuntu").resolve()
    for path in (baseline, output):
        if home not in (path, *path.parents):
            raise RuntimeError(f"path outside /home/ubuntu: {path}")
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    # The retained baseline has runtime-generated Python caches after previous
    # board gates. Verify every declared byte, tolerate only those cache extras,
    # and exclude them while copying into the immutable new candidate.
    verify_package(baseline, args.baseline_manifest_sha256, allow_cache_extras=True)

    attributes = termios.tcgetattr(sys.stdin.fileno())
    quiet = attributes.copy()
    quiet[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, quiet)
    print("M89X1_HS64_UART_STAGER_READY", flush=True)
    encoded = []
    try:
        while True:
            line = sys.stdin.readline()
            if line == "":
                raise RuntimeError("UART closed before delta EOF")
            text = line.strip()
            if text == EOF_MARKER:
                break
            encoded.append(text)
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, attributes)
    delta = base64.b64decode("".join(encoded), validate=True)
    if hashlib.sha256(delta).hexdigest() != args.delta_sha256:
        raise RuntimeError("UART delta hash mismatch")

    temporary = Path(str(output) + ".staging")
    if temporary.exists():
        raise RuntimeError(f"staging path already exists: {temporary}")
    shutil.copytree(baseline, temporary, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    archive_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="m89x1_hs64_", suffix=".tar.gz", delete=False) as handle:
            handle.write(delta)
            archive_path = Path(handle.name)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                target = (temporary / member.name).resolve()
                if temporary.resolve() not in target.parents:
                    raise RuntimeError(f"unsafe archive path: {member.name}")
                if not member.isfile():
                    raise RuntimeError(f"non-file archive member: {member.name}")
            # Python 3.10 on the board predates tarfile's filter= argument.
            # Path traversal and member type were already rejected above.
            archive.extractall(temporary, members=members)
        manifest = verify_package(temporary, args.candidate_manifest_sha256)
        os.replace(temporary, output)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    finally:
        if archive_path is not None and archive_path.exists():
            archive_path.unlink()
    print(json.dumps({"status": "PASS", "output": str(output),
                      "files": len(manifest["files"]),
                      "candidate_manifest_sha256": args.candidate_manifest_sha256}), flush=True)
    print("M89X1_HS64_UART_STAGE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
