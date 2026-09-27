#!/usr/bin/env python3
"""Split, verify, and reassemble a hash-locked release asset.

The split command never modifies its input. All outputs are created in a
dedicated directory and existing outputs are refused, rather than overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


CHUNK_BYTES = 8 * 1024 * 1024
DEFAULT_PART_BYTES = 2_000_000_000  # Strictly below GitHub's 2 GiB asset limit.


def split(source: Path, output_dir: Path, part_bytes: int) -> Path:
    if part_bytes <= 0 or part_bytes >= 2 * 1024**3:
        raise ValueError("part size must be positive and strictly below 2 GiB")
    if not source.is_file():
        raise FileNotFoundError(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "RELEASE_PARTS.json"
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    source_hash = hashlib.sha256()
    parts = []
    with source.open("rb") as src:
        index = 1
        while True:
            first = src.read(min(CHUNK_BYTES, part_bytes))
            if not first:
                break
            name = f"{source.name}.part{index:02d}"
            target = output_dir / name
            partial = output_dir / f"{name}.partial"
            if target.exists() or partial.exists():
                raise FileExistsError(target if target.exists() else partial)
            digest = hashlib.sha256()
            count = 0
            with partial.open("xb") as dst:
                chunk = first
                while chunk:
                    dst.write(chunk)
                    digest.update(chunk)
                    source_hash.update(chunk)
                    count += len(chunk)
                    remaining = part_bytes - count
                    chunk = src.read(min(CHUNK_BYTES, remaining)) if remaining else b""
                dst.flush()
                os.fsync(dst.fileno())
            os.replace(partial, target)
            parts.append({"file": name, "bytes": count, "sha256": digest.hexdigest()})
            index += 1
    manifest = {
        "schema": "kv260-release-parts-v1",
        "source_name": source.name,
        "source_bytes": source.stat().st_size,
        "source_sha256": source_hash.hexdigest(),
        "part_bytes_limit": part_bytes,
        "parts": parts,
    }
    if sum(part["bytes"] for part in parts) != manifest["source_bytes"]:
        raise RuntimeError("split byte count does not match source")
    temporary_manifest = output_dir / "RELEASE_PARTS.json.partial"
    with temporary_manifest.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary_manifest, manifest_path)
    return manifest_path


def verify(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "kv260-release-parts-v1":
        raise ValueError("unsupported manifest schema")
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("manifest has no parts")
    seen = set()
    total = 0
    combined = hashlib.sha256()
    for part in parts:
        name = part["file"]
        if name in seen or Path(name).name != name:
            raise ValueError(f"invalid or repeated part name: {name}")
        seen.add(name)
        path = manifest_path.parent / name
        actual_size = path.stat().st_size
        part_digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(CHUNK_BYTES):
                part_digest.update(chunk)
                combined.update(chunk)
        actual_hash = part_digest.hexdigest()
        if actual_size != part["bytes"] or actual_hash != part["sha256"]:
            raise ValueError(f"part mismatch: {name}")
        total += actual_size
    if total != manifest["source_bytes"]:
        raise ValueError("total part size mismatch")
    if combined.hexdigest() != manifest["source_sha256"]:
        raise ValueError("combined SHA-256 mismatch")
    return manifest


def assemble(manifest_path: Path, output: Path) -> None:
    manifest = verify(manifest_path)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise FileExistsError(partial)
    digest = hashlib.sha256()
    try:
        with partial.open("xb") as dst:
            for part in manifest["parts"]:
                with (manifest_path.parent / part["file"]).open("rb") as src:
                    while chunk := src.read(CHUNK_BYTES):
                        dst.write(chunk)
                        digest.update(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if partial.stat().st_size != manifest["source_bytes"]:
            raise ValueError("assembled size mismatch")
        if digest.hexdigest() != manifest["source_sha256"]:
            raise ValueError("assembled SHA-256 mismatch")
        os.replace(partial, output)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    split_parser = commands.add_parser("split")
    split_parser.add_argument("source", type=Path)
    split_parser.add_argument("output_dir", type=Path)
    split_parser.add_argument("--part-bytes", type=int, default=DEFAULT_PART_BYTES)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("manifest", type=Path)
    assemble_parser = commands.add_parser("assemble")
    assemble_parser.add_argument("manifest", type=Path)
    assemble_parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "split":
        result = split(args.source, args.output_dir, args.part_bytes)
        print(result)
    elif args.command == "verify":
        manifest = verify(args.manifest)
        print(f"PASS: {len(manifest['parts'])} parts, {manifest['source_bytes']} bytes")
    else:
        assemble(args.manifest, args.output)
        print(f"PASS: {args.output}")


if __name__ == "__main__":
    main()
