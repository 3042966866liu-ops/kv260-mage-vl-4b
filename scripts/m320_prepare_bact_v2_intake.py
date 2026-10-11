#!/usr/bin/env python3
"""Inventory new BACT-V2 source videos without using filenames as labels.

This is an acquisition preflight, not the M312 formal dataset or a quality gate.
It never opens held-out labels and never modifies source videos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PILOT_LABELS = ROOT / "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json"
PROTOCOL = ROOT / "bact/bact_v2_protocol.json"
SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
RUN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{2,63}\Z")
REGISTER_FIELDS = (
    "opaque_source_id", "video_path", "video_sha256", "source_type",
    "source_url_or_capture_id", "license_or_consent", "person_or_scene_group",
    "duration_seconds", "planned_split", "first_annotator", "second_annotator", "review_notes",
)
LABEL_FIELDS = (
    "opaque_source_id", "knife_present", "action", "watched_complete", "annotator",
    "low_light", "occlusion", "small_knife", "hard_negative", "fast_motion", "partial_person",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def pilot_hashes() -> set[str]:
    labels = load_json(PILOT_LABELS)
    if labels.get("schema") != "tellme-bact-clip-constant-v1":
        raise ValueError("historical pilot label schema changed")
    result = {str(row["videoSha256"]).lower() for row in labels["clips"]}
    if len(result) != 12 or any(len(value) != 64 for value in result):
        raise ValueError("historical pilot hash closure is not 12 unique sources")
    return result


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def inventory(source_dir: Path, old: set[str]) -> tuple[list[dict], list[dict]]:
    if source_dir.exists() and not source_dir.is_dir():
        raise ValueError("source-dir exists but is not a directory")
    files = sorted(
        (path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in SUFFIXES),
        key=lambda path: path.name.lower(),
    ) if source_dir.exists() else []
    by_digest: dict[str, list[dict]] = {}
    for path in files:
        if path.stat().st_size <= 0:
            raise ValueError(f"zero-byte video: {path}")
        digest = sha256(path)
        by_digest.setdefault(digest, []).append({
            "path": display_path(path), "bytes": path.stat().st_size,
            "sha256": digest,
        })
    unique = []
    register = []
    for digest, members in sorted(by_digest.items()):
        opaque_id = f"s{digest[:12]}"
        excluded = digest in old
        unique.append({
            "opaque_source_id": opaque_id,
            "video_sha256": digest,
            "video_path": members[0]["path"],
            "bytes": members[0]["bytes"],
            "duplicate_paths": [member["path"] for member in members[1:]],
            "excluded_historical_pilot": excluded,
        })
        if not excluded:
            register.append({
                "opaque_source_id": opaque_id,
                "video_path": members[0]["path"],
                "video_sha256": digest,
                "source_type": "", "source_url_or_capture_id": "",
                "license_or_consent": "", "person_or_scene_group": "",
                "duration_seconds": "", "planned_split": "", "first_annotator": "",
                "second_annotator": "", "review_notes": "",
            })
    return unique, register


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/bact_v2/inbox")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    args = parser.parse_args()
    if not RUN_ID.fullmatch(args.run_id):
        raise ValueError("run-id must be 3-64 lowercase ASCII letters, numbers, _ or -")
    workspace = args.workspace.resolve()
    if workspace != ROOT:
        raise ValueError("workspace must be the source tree containing this script")
    source_dir = args.source_dir.resolve()
    output_dir = ROOT / "data/bact_v2/intake" / args.run_id
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite an intake audit: {output_dir}")
    protocol = load_json(PROTOCOL)
    if protocol.get("schema") != "tellme-bact-v2-preregistered-protocol-v1":
        raise ValueError("M312 protocol identity changed")
    old = pilot_hashes()
    unique, register = inventory(source_dir, old)
    minimum = int(protocol["dataset"]["minimumIndependentSourceVideos"])
    minimum_real = int(protocol["dataset"]["minimumControlledOrLicensedRealPublicVideos"])
    summary = {
        "schema": "tellme-bact-v2-source-intake-audit-v1",
        "status": "INTAKE_REVIEW_REQUIRED" if register else "NO_NEW_SOURCES",
        "classification": "Read-only video-hash inventory; source type, license, labels and split remain unverified.",
        "source_dir": display_path(source_dir),
        "protocol_sha256": sha256(PROTOCOL),
        "historical_labels_sha256": sha256(PILOT_LABELS),
        "files_found": sum(1 + len(row["duplicate_paths"]) for row in unique),
        "unique_source_hashes": len(unique),
        "historical_pilot_excluded": sum(row["excluded_historical_pilot"] for row in unique),
        "new_unique_sources_unverified": len(register),
        "minimum_new_sources": minimum,
        "missing_new_sources": max(0, minimum - len(register)),
        "minimum_real_sources": minimum_real,
        "verified_real_sources": 0,
        "first_annotations_verified": 0,
        "independent_second_annotations_verified": 0,
        "formal_dataset_ready": False,
        "blind_predictions_ready": False,
        "held_out_opened": False,
        "board_runs": 0,
        "videos": unique,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "INVENTORY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "SOURCE_REGISTER_TEMPLATE.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTER_FIELDS)
        writer.writeheader()
        writer.writerows(register)
    for name in ("PRIMARY_LABELS_TEMPLATE.csv", "SECONDARY_LABELS_TEMPLATE.csv", "ADJUDICATION_TEMPLATE.csv"):
        with (output_dir / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            if name == "PRIMARY_LABELS_TEMPLATE.csv":
                writer.writerows({"opaque_source_id": row["opaque_source_id"]} for row in register)
    print(
        f"M320_BACT_V2_INTAKE_{summary['status']} "
        f"new_unique={len(register)} old_excluded={summary['historical_pilot_excluded']} "
        f"minimum={minimum} output={display_path(output_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
