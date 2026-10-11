#!/usr/bin/env python3
"""Compact selected modules from the verified full four-port layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from copy import deepcopy
from pathlib import Path


ALIGNMENT = 4096
HIGH_POOL_BYTES = 1_744_830_464
LOW_CMA_BYTES = 800 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def align(value: int) -> int:
    return (value + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT


def copy_exact(source, destination, offset: int, count: int) -> None:
    source.seek(offset)
    remaining = count
    while remaining:
        chunk = source.read(min(8 << 20, remaining))
        if not chunk:
            raise RuntimeError("M89Y_SOURCE_TRUNCATED")
        destination.write(chunk)
        remaining -= len(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--selection", choices=("language", "lm-head", "vision"), default="language")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    manifest_path = args.source / "SIXPORT_LAYOUT_MANIFEST.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError("M89Y_SOURCE_FORMAT_FAIL")
    if int(manifest["parameters"]["shard_count"]) != 4:
        raise RuntimeError("M89Y_SOURCE_SHARD_COUNT_FAIL")
    source_files = []
    for item in manifest["files"]:
        path = args.source / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M89Y_SOURCE_FILE_IDENTITY_FAIL path={path}")
        source_files.append(path.open("rb"))
    if args.selection == "language":
        modules = [deepcopy(item) for item in manifest["modules"]
                   if ".language_model.layers." in item["module"]]
        expected_modules, pool_bytes = 252, HIGH_POOL_BYTES
        build_id, pattern = "M89-Y-LANGUAGE-ONLY-FOURPORT-20260831", "\\.language_model\\.layers\\."
    elif args.selection == "lm-head":
        modules = [deepcopy(item) for item in manifest["modules"]
                   if item["module"] == "lm_head"]
        expected_modules, pool_bytes = 1, LOW_CMA_BYTES
        build_id, pattern = "M89-Z-LMHEAD-ONLY-FOURPORT-20260831", "^lm_head$"
    else:
        modules = [deepcopy(item) for item in manifest["modules"]
                   if item["module"].startswith("model.visual.")]
        expected_modules, pool_bytes = 98, LOW_CMA_BYTES
        build_id, pattern = "M90-VISION-W4-FOURPORT-20260831", "^model\\.visual\\."
    if len(modules) != expected_modules:
        raise RuntimeError(f"M89Y_MODULE_COUNT_FAIL selection={args.selection} count={len(modules)}")

    temp = args.output.parent / f".{args.output.name}.tmp-{uuid.uuid4().hex}"
    temp.mkdir(parents=True)
    destinations = [(temp / f"weights{index}.bin").open("wb") for index in range(4)]
    copied_bytes = 0
    try:
        for module in modules:
            for tile in module["tiles"]:
                positions = [handle.tell() for handle in destinations]
                target = align(max(positions))
                for handle in destinations:
                    handle.write(bytes(target - handle.tell()))
                new_offsets = []
                count = int(tile["record_bytes_per_shard"])
                for shard in range(4):
                    new_offsets.append(destinations[shard].tell())
                    copy_exact(source_files[shard], destinations[shard],
                               int(tile["shard_offsets"][shard]), count)
                    copied_bytes += count
                if len(set(new_offsets)) != 1:
                    raise RuntimeError("M89Y_OFFSET_LOCKSTEP_FAIL")
                tile["shard_offsets"] = new_offsets
        for handle in destinations:
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
        destinations = []
        for handle in source_files:
            handle.close()
        source_files = []

        files = []
        for index in range(4):
            path = temp / f"weights{index}.bin"
            files.append({"path": path.name, "bytes": path.stat().st_size,
                          "sha256": sha256(path)})
        total = sum(int(item["bytes"]) for item in files)
        if total > pool_bytes:
            raise RuntimeError(f"M89Y_POOL_OVERFLOW selection={args.selection} bytes={total}")
        compact = {
            "format": manifest["format"],
            "build_id": build_id,
            "classification": "exact byte-slice compaction of verified M89-P; no requantization",
            "source": {
                "layout_manifest": manifest_path.as_posix(),
                "layout_manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "m56_manifest_sha256": manifest["source"]["manifest_sha256"],
                "m56_blob_sha256": manifest["source"]["blob_sha256"],
            },
            "parameters": manifest["parameters"],
            "selection_pattern": pattern,
            "module_count": len(modules),
            "files": files,
            "modules": modules,
            "verification": {
                "status": "PASS_EXACT_TILE_BYTE_COPY",
                "requantized": False,
                "copied_payload_bytes_across_shards": copied_bytes,
                "file_hashes_verified": True,
                "pool_bytes": pool_bytes,
                "mapped_bytes": total,
                "headroom_bytes": pool_bytes - total,
            },
        }
        (temp / "SIXPORT_LAYOUT_MANIFEST.json").write_text(
            json.dumps(compact, indent=2) + "\n", encoding="utf-8"
        )
        temp.rename(args.output)
    except Exception:
        for handle in destinations:
            if not handle.closed:
                handle.close()
        for handle in source_files:
            if not handle.closed:
                handle.close()
        shutil.rmtree(temp, ignore_errors=True)
        raise

    output_manifest = args.output / "SIXPORT_LAYOUT_MANIFEST.json"
    status_by_selection = {
        "language": "PASS_LANGUAGE_ONLY_FOURPORT_COMPACTION",
        "lm-head": "PASS_LMHEAD_ONLY_FOURPORT_COMPACTION",
        "vision": "PASS_VISION_ONLY_FOURPORT_COMPACTION",
    }
    build_by_selection = {"language": "M89-Y", "lm-head": "M89-Z", "vision": "M90-V"}
    marker_by_selection = {
        "language": "M89Y_LANGUAGE_ONLY_FOURPORT_COMPACTION_PASS",
        "lm-head": "M89Z_LMHEAD_ONLY_FOURPORT_COMPACTION_PASS",
        "vision": "M90_VISION_ONLY_FOURPORT_COMPACTION_PASS",
    }
    result = {
        "date": "2026-08-31",
        "build": build_by_selection[args.selection],
        "status": status_by_selection[args.selection],
        "source_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "output_manifest": output_manifest.as_posix(),
        "output_manifest_sha256": sha256(output_manifest),
        "module_count": expected_modules,
        "selection": args.selection,
        "mapped_bytes": total,
        "pool_bytes": pool_bytes,
        "headroom_bytes": pool_bytes - total,
        "requantized": False,
        "files": files,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(marker_by_selection[args.selection])
    print(json.dumps({"mapped_bytes": total, "headroom_bytes": pool_bytes - total}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
