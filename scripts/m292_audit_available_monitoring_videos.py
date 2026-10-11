#!/usr/bin/env python3
"""Read-only inventory and SHA-256 de-duplication of candidate monitoring videos."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        raise RuntimeError("input directory does not exist")
    files = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    records = [
        {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    groups: dict[str, list[str]] = {}
    for record in records:
        groups.setdefault(record["sha256"], []).append(record["filename"])
    duplicate_groups = [names for names in groups.values() if len(names) > 1]
    unique_sources = len(groups)
    result = {
        "date": "2026-09-02",
        "gate": "M292-read-only-local-monitoring-video-inventory",
        "status": "PASS_INVENTORY_DATASET_INSUFFICIENT" if unique_sources < 12 else "PASS_INVENTORY_MINIMUM_SOURCE_COUNT_AVAILABLE",
        "classification": (
            "Read-only filename/size/SHA-256 inventory. Duplicate files are one source video; no labels, "
            "split assignment, model run, accuracy or board evidence are inferred."
        ),
        "input_directory_name": input_dir.name,
        "file_count": len(records),
        "unique_source_video_count": unique_sources,
        "records": records,
        "duplicate_filename_groups": duplicate_groups,
        "minimum_one_week_pilot_source_count": 12,
        "additional_unique_sources_needed": max(0, 12 - unique_sources),
        "human_annotation_complete": False,
        "semantic_accuracy_passed": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Add source-distinct workplace monitoring clips covering knife positives/negatives and all five "
            "actions; rerun inventory before extraction or human annotation."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(
        f"M292_VIDEO_INVENTORY_PASS files={len(records)} unique={unique_sources} "
        f"additional_needed={result['additional_unique_sources_needed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
