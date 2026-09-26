"""Fail-closed validation for real target-monitoring manifests."""

from __future__ import annotations

import math


ACTIONS = ("WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING")
SPLITS = ("train", "calibration", "test")


def _sha256(value: str, field: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field} must be a SHA-256")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{field} must be hexadecimal") from error


def _bbox(value: list[float]) -> None:
    if len(value) != 4 or any(not math.isfinite(float(item)) for item in value):
        raise ValueError("bbox_xyxy must contain four finite values")
    x1, y1, x2, y2 = map(float, value)
    if not (0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0):
        raise ValueError("bbox_xyxy must be normalized and non-empty")


def validate_target_scene_manifest(manifest: dict, *, formal: bool = True) -> dict:
    if manifest.get("schema") != "tellme-bact-target-scene-v1":
        raise ValueError("unsupported target-scene schema")
    clips = manifest.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("manifest must contain clips")

    clip_ids: set[str] = set()
    split_by_source: dict[str, str] = {}
    split_counts = {split: 0 for split in SPLITS}
    action_support = {split: {action: 0 for action in ACTIONS} for split in SPLITS}
    knife_support = {split: {False: 0, True: 0} for split in SPLITS}
    frame_count = 0
    pending = []
    for clip in clips:
        clip_id = str(clip["clip_id"])
        split = str(clip["split"])
        source_hash = str(clip["video_sha256"]).lower()
        _sha256(source_hash, "video_sha256")
        if clip_id in clip_ids:
            raise ValueError(f"duplicate clip_id: {clip_id}")
        clip_ids.add(clip_id)
        if split not in SPLITS:
            raise ValueError(f"unsupported split: {split}")
        if source_hash in split_by_source and split_by_source[source_hash] != split:
            raise ValueError("same source video appears across splits")
        split_by_source[source_hash] = split
        split_counts[split] += 1
        if clip.get("annotation_status") != "HUMAN_VERIFIED_COMPLETE":
            pending.append(clip_id)
            continue
        frames = clip.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ValueError(f"completed clip has no frames: {clip_id}")
        sequences = set()
        previous_timestamp = -1
        for frame in frames:
            sequence = int(frame["sequence"])
            timestamp = int(frame["timestamp_ms"])
            if sequence in sequences or timestamp < 0 or timestamp <= previous_timestamp:
                raise ValueError(f"invalid frame order: {clip_id}")
            sequences.add(sequence)
            previous_timestamp = timestamp
            knife = bool(frame["knife_present"])
            knife_support[split][knife] += 1
            track_ids = set()
            for person in frame.get("people", []):
                track_id = int(person["track_id"])
                if track_id in track_ids:
                    raise ValueError(f"duplicate track_id in frame: {clip_id}/{sequence}")
                track_ids.add(track_id)
                _bbox(person["bbox_xyxy"])
                action = str(person["action"])
                if action not in ACTIONS:
                    raise ValueError(f"unsupported ground-truth action: {action}")
                action_support[split][action] += 1
            frame_count += 1

    if formal and pending:
        raise ValueError("formal manifest contains incomplete human annotations: " + ",".join(sorted(pending)))
    if formal:
        if split_counts["calibration"] == 0 or split_counts["test"] == 0:
            raise ValueError("formal manifest requires calibration and test clips")
        for split in ("calibration", "test"):
            if knife_support[split][True] == 0 or knife_support[split][False] == 0:
                raise ValueError(f"{split} requires knife-positive and knife-negative frames")
            missing_actions = [action for action, count in action_support[split].items() if count == 0]
            if missing_actions:
                raise ValueError(f"{split} lacks action support: {','.join(missing_actions)}")

    return {
        "clip_count": len(clips),
        "frame_count": frame_count,
        "split_clip_counts": split_counts,
        "action_support": action_support,
        "knife_frame_support": {
            split: {"negative": values[False], "positive": values[True]}
            for split, values in knife_support.items()
        },
        "pending_annotation_clip_ids": sorted(pending),
        "formal_ready": formal and not pending,
    }
