#!/usr/bin/env python3
"""Hash, sample and prepare a fail-closed human-label draft for BACT videos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import cv2


VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}
SPLIT_PREFIXES = {"cal_": "calibration", "test_": "test_held_out"}
ACTION_HINTS = ("working", "idle", "walking", "falling", "fighting")
SAMPLE_PERIOD_MS = 500
MINIMUM_UNIQUE_BY_SPLIT = {"calibration": 6, "test_held_out": 6}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def infer_split(filename: str) -> str:
    lowered = filename.lower()
    matches = [split for prefix, split in SPLIT_PREFIXES.items() if lowered.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"filename must start with exactly cal_ or test_: {filename}")
    return matches[0]


def filename_hints(filename: str) -> dict:
    lowered = filename.lower()
    action = next((name.upper() for name in ACTION_HINTS if f"_{name}" in lowered), None)
    if "_no_knife" in lowered:
        knife = "NEGATIVE_HINT"
    elif "_knife" in lowered:
        knife = "POSITIVE_HINT"
    else:
        knife = "NO_HINT"
    conditions = [name for name in ("hard", "dark", "occluded", "far", "clutter") if name in lowered]
    return {
        "action_hint_not_ground_truth": action,
        "knife_hint_not_ground_truth": knife,
        "condition_hints_not_ground_truth": conditions,
    }


def probe_video(path: Path) -> dict:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {path.name}")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
        width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
        height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    finally:
        capture.release()
    if not (fps > 0.0 and frame_count > 0 and width > 0 and height > 0):
        raise RuntimeError(f"invalid video metadata: {path.name}")
    duration_ms = int(round(frame_count * 1000.0 / fps))
    if duration_ms <= 0:
        raise RuntimeError(f"invalid video duration: {path.name}")
    return {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_ms": duration_ms,
    }


def clip_id(split: str, filename: str, digest: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", Path(filename).stem.lower()).strip("-")
    return f"{split}-{stem}-{digest[:8]}"


def extract_samples(path: Path, destination: Path, metadata: dict) -> list[dict]:
    destination.mkdir(parents=False)
    timestamps = list(range(0, metadata["duration_ms"], SAMPLE_PERIOD_MS))
    if not timestamps:
        timestamps = [0]
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot reopen video: {path.name}")
    frames = []
    try:
        for sequence, timestamp_ms in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp_ms))
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError(f"sample decode failed: {path.name}@{timestamp_ms}ms")
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            if not ok:
                raise RuntimeError(f"sample encode failed: {path.name}@{timestamp_ms}ms")
            filename = f"frame_{sequence:04d}_{timestamp_ms:06d}ms.jpg"
            frame_path = destination / filename
            frame_path.write_bytes(encoded.tobytes())
            frames.append({
                "sequence": sequence,
                "timestamp_ms": timestamp_ms,
                "sample_path": f"{destination.name}/{filename}",
                "sample_sha256": sha256(frame_path),
                "annotation_status": "PENDING_HUMAN",
                "knife_present": None,
                "people": [],
            })
    finally:
        capture.release()
    return frames


def write_annotation_csv(path: Path, clips: list[dict]) -> None:
    columns = [
        "clip_id", "split", "video_sha256", "source_filename", "sequence", "timestamp_ms",
        "sample_path", "knife_present_TRUE_or_FALSE", "person_present_TRUE_or_FALSE",
        "person_track_id", "bbox_x1_normalized", "bbox_y1_normalized", "bbox_x2_normalized",
        "bbox_y2_normalized", "action_WORKING_IDLE_WALKING_FALLING_FIGHTING",
        "condition_tags", "human_verified_TRUE", "annotator", "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for clip in clips:
            for frame in clip["frames"]:
                writer.writerow({
                    "clip_id": clip["clip_id"],
                    "split": clip["split"],
                    "video_sha256": clip["video_sha256"],
                    "source_filename": clip["source_filename"],
                    "sequence": frame["sequence"],
                    "timestamp_ms": frame["timestamp_ms"],
                    "sample_path": frame["sample_path"],
                })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source-kind", choices=("AI_GENERATED_PILOT", "REAL_CAMERA"), required=True)
    parser.add_argument("--milestone", choices=("M295", "M296"), default="M295")
    parser.add_argument("--date", default="2026-09-02")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    tag = args.milestone
    tag_lower = tag.lower()
    inbox = workspace / "data/bact_target_scene/inbox"
    frame_root = workspace / f"data/bact_target_scene/{tag_lower}_sampled_frames"
    partial_frames = frame_root.with_name(frame_root.name + f".partial-{os.getpid()}")
    manifest_path = workspace / f"data/bact_target_scene/{tag}_TARGET_SCENE_MANIFEST_DRAFT.json"
    csv_path = workspace / f"data/bact_target_scene/{tag}_HUMAN_ANNOTATION_TEMPLATE.csv"
    result_path = workspace / f"deployment/mage_vl4b/{tag}_TARGET_SCENE_INTAKE_RESULT.json"
    for output in (frame_root, manifest_path, csv_path, result_path):
        if output.exists():
            raise RuntimeError(f"refuse to overwrite {tag} output: {output}")
    files = sorted(path for path in inbox.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES)
    if not files:
        raise RuntimeError("M295 inbox has no videos")

    records = []
    for path in files:
        digest = sha256(path)
        split = infer_split(path.name)
        records.append({
            "path": path,
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "split": split,
            "metadata": probe_video(path),
            "hints": filename_hints(path.name),
        })
    groups: dict[str, list[dict]] = {}
    for record in records:
        groups.setdefault(record["sha256"], []).append(record)
    for digest, members in groups.items():
        if len({member["split"] for member in members}) != 1:
            raise RuntimeError(f"source-video split leakage: {digest}")

    partial_frames.mkdir(parents=False)
    clips = []
    try:
        for digest, members in sorted(groups.items(), key=lambda item: item[1][0]["filename"]):
            canonical = members[0]
            identifier = clip_id(canonical["split"], canonical["filename"], digest)
            sampled = extract_samples(canonical["path"], partial_frames / identifier, canonical["metadata"])
            clips.append({
                "clip_id": identifier,
                "split": "test" if canonical["split"] == "test_held_out" else canonical["split"],
                "video_sha256": digest,
                "source_filename": canonical["filename"],
                "duplicate_filenames_same_source": [member["filename"] for member in members[1:]],
                "source_kind": args.source_kind,
                "source_kind_claim_scope": "pilot only" if args.source_kind == "AI_GENERATED_PILOT" else "user-declared real camera",
                "split_assignment": "FILENAME_PREFIX_LOCKED_BEFORE_LABELING",
                "filename_hints_are_ground_truth": False,
                "filename_hints": canonical["hints"],
                "video_metadata": canonical["metadata"],
                "sampling_period_ms": SAMPLE_PERIOD_MS,
                "annotation_status": "PENDING_HUMAN",
                "frames": sampled,
            })
        os.replace(partial_frames, frame_root)
    except Exception:
        if partial_frames.exists():
            shutil.rmtree(partial_frames)
        raise

    # Rewrite staged directory names to the final relative root.
    for clip in clips:
        for frame in clip["frames"]:
            frame["sample_path"] = f"data/bact_target_scene/{tag_lower}_sampled_frames/{clip['clip_id']}/{Path(frame['sample_path']).name}"

    manifest = {
        "schema": "tellme-bact-target-scene-v1",
        "date": args.date,
        "status": "DRAFT_PENDING_HUMAN_ANNOTATION",
        "dataset_scope": args.source_kind,
        "annotation_policy": "Human labels are authoritative; filename hints and model outputs are never ground truth.",
        "sample_period_ms": SAMPLE_PERIOD_MS,
        "clips": clips,
    }
    atomic_json(manifest_path, manifest)
    write_annotation_csv(csv_path, clips)

    unique_by_split = {name: 0 for name in MINIMUM_UNIQUE_BY_SPLIT}
    for members in groups.values():
        unique_by_split[members[0]["split"]] += 1
    missing_by_split = {
        split: max(0, minimum - unique_by_split[split])
        for split, minimum in MINIMUM_UNIQUE_BY_SPLIT.items()
    }
    duplicate_groups = [sorted(member["filename"] for member in members) for members in groups.values() if len(members) > 1]
    frame_files = list(frame_root.rglob("*.jpg"))
    result = {
        "date": args.date,
        "gate": f"{tag}-target-scene-video-intake-and-human-annotation-template",
        "status": "PASS_INTAKE_PILOT_INCOMPLETE" if any(missing_by_split.values()) else "PASS_INTAKE_SOURCE_COUNT_READY_LABELS_PENDING",
        "classification": "Hash-deduplicated intake, fixed-rate frame sampling and blank human-label template only; no filename-derived truth, model accuracy, board or real-time claim.",
        "source_kind": args.source_kind,
        "source_kind_limit": "AI-generated clips support a synthetic pilot, not real-world external validity." if args.source_kind == "AI_GENERATED_PILOT" else None,
        "file_count": len(records),
        "unique_source_video_count": len(groups),
        "unique_source_by_split": unique_by_split,
        "minimum_unique_source_by_split": MINIMUM_UNIQUE_BY_SPLIT,
        "additional_unique_sources_needed_by_split": missing_by_split,
        "duplicate_filename_groups": duplicate_groups,
        "sampled_frame_count": len(frame_files),
        "sampled_frame_bytes": sum(path.stat().st_size for path in frame_files),
        "sample_period_ms": SAMPLE_PERIOD_MS,
        "manifest": str(manifest_path.relative_to(workspace)).replace("\\", "/"),
        "manifest_sha256": sha256(manifest_path),
        "annotation_csv": str(csv_path.relative_to(workspace)).replace("\\", "/"),
        "annotation_csv_sha256": sha256(csv_path),
        "human_annotation_complete": False,
        "formal_accuracy_ready": False,
        "semantic_accuracy_passed": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Add missing source-distinct held-out videos, complete all human frame labels, validate the formal manifest, freeze calibration thresholds, then execute held-out test once."
            if any(missing_by_split.values())
            else "Human-review all sampled frames, validate the completed source-disjoint manifest, freeze calibration thresholds, then execute held-out test once."
        ),
    }
    atomic_json(result_path, result)
    print(
        f"{tag}_TARGET_SCENE_INTAKE_PASS "
        f"files={len(records)} unique={len(groups)} sampled_frames={len(frame_files)} "
        f"missing_calibration={missing_by_split['calibration']} missing_test={missing_by_split['test_held_out']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
