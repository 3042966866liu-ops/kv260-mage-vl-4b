#!/usr/bin/env python3
"""Audit M312 source provenance, independent labels and split leakage.

The default is an honest readiness report. --require-pass returns nonzero if
any frozen data gate remains unmet. Source files and historical data are read-only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "bact/bact_v2_protocol.json"
PILOT_LABELS = ROOT / "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json"
SOURCE_TYPES = {"controlled_capture", "public_licensed", "ai_generated"}
ACTIONS = {"WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING"}
SPLITS = {"calibration", "test"}
CONDITIONS = ("low_light", "occlusion", "small_knife", "hard_negative", "fast_motion", "partial_person")
SOURCE_FIELDS = {
    "opaque_source_id", "video_path", "video_sha256", "source_type",
    "source_url_or_capture_id", "license_or_consent", "person_or_scene_group",
    "duration_seconds", "planned_split", "first_annotator", "second_annotator", "review_notes",
}
LABEL_FIELDS = {"opaque_source_id", "knife_present", "action", "watched_complete", "annotator", *CONDITIONS}
OPAQUE_ID = re.compile(r"s[0-9a-f]{12}\Z")
BLIND_VIDEOS = ROOT / "data/bact_v2/blind_videos"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"required CSV columns missing: {path}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f"row contains extra unheaded cells: {path}")
    return rows


def boolean(value: object, name: str) -> bool:
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    raise ValueError(f"{name} must be TRUE or FALSE")


def kappa(pairs: list[tuple[object, object]]) -> float | None:
    if not pairs:
        return None
    classes = set(value for pair in pairs for value in pair)
    n = len(pairs)
    observed = sum(left == right for left, right in pairs) / n
    chance = sum(
        sum(left == value for left, _ in pairs) / n
        * sum(right == value for _, right in pairs) / n
        for value in classes
    )
    return (observed - chance) / (1 - chance) if chance < 1 else None


def parse_label(row: dict[str, str], expected_annotator: str | None) -> dict:
    source_id = row["opaque_source_id"].strip()
    annotator = row["annotator"].strip()
    if expected_annotator is not None and annotator != expected_annotator:
        raise ValueError(f"annotator identity mismatch: {source_id}")
    action = row["action"].strip()
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {source_id}/{action}")
    if not annotator or not boolean(row["watched_complete"].strip(), "watched_complete"):
        raise ValueError(f"incomplete human review: {source_id}")
    return {
        "source_id": source_id,
        "annotator": annotator,
        "knife_present": boolean(row["knife_present"].strip(), "knife_present"),
        "action": action,
        "conditions": {name: boolean(row[name].strip(), name) for name in CONDITIONS},
    }


def index_rows(rows: list[dict[str, str]], name: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        key = row["opaque_source_id"].strip()
        if not key or key in indexed:
            raise ValueError(f"duplicate or empty source ID in {name}: {key!r}")
        indexed[key] = row
    return indexed


def probe_video(video: Path, ffprobe: Path, ffmpeg: Path) -> tuple[float, int]:
    metadata = subprocess.run(
        [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries",
         "format=duration:stream=codec_type", "-of", "json", str(video)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    info = json.loads(metadata.stdout)
    if not info.get("streams"):
        raise ValueError("no video stream")
    duration = float(info["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid probed duration")
    decoded = subprocess.run(
        [str(ffmpeg), "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0",
         "-an", "-f", "null", "-", "-progress", "pipe:1"],
        capture_output=True, text=True, timeout=600, check=True,
    )
    frame_counts = re.findall(r"(?m)^frame=(\d+)\s*$", decoded.stdout)
    if not frame_counts or int(frame_counts[-1]) < 1:
        raise ValueError("full decode produced no frames")
    return duration, int(frame_counts[-1])


def verify_sources(rows: list[dict[str, str]], old_hashes: set[str], reasons: list[str],
                   ffprobe: Path | None, ffmpeg: Path | None) -> list[dict]:
    sources = []
    seen_hashes: set[str] = set()
    group_splits: dict[str, str] = {}
    for row in rows:
        source_id = row["opaque_source_id"].strip()
        digest = row["video_sha256"].strip().lower()
        if not OPAQUE_ID.fullmatch(source_id) or not digest.startswith(source_id[1:]) or len(digest) != 64:
            raise ValueError(f"invalid opaque ID / SHA relation: {source_id}")
        if digest in seen_hashes:
            raise ValueError(f"duplicate source video hash: {digest}")
        seen_hashes.add(digest)
        if digest in old_hashes:
            reasons.append(f"old pilot source is forbidden: {source_id}")
        raw_path = Path(row["video_path"].strip())
        video = (ROOT / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()
        if not video.is_file() or hash_file(video) != digest:
            raise ValueError(f"video missing or SHA mismatch: {source_id}")
        if video.stem.lower() != source_id or video.parent != BLIND_VIDEOS.resolve():
            reasons.append(f"blind video must be directly in blind_videos with opaque filename: {source_id}")
        source_type = row["source_type"].strip()
        if source_type not in SOURCE_TYPES:
            reasons.append(f"source type missing or invalid: {source_id}")
        if not row["license_or_consent"].strip() or not row["source_url_or_capture_id"].strip():
            reasons.append(f"rights/provenance evidence missing: {source_id}")
        group = row["person_or_scene_group"].strip()
        split = row["planned_split"].strip()
        if not group or split not in SPLITS:
            reasons.append(f"group or split missing: {source_id}")
        elif group in group_splits and group_splits[group] != split:
            reasons.append(f"person/scene group crosses splits: {group}")
        else:
            group_splits[group] = split
        try:
            duration = float(row["duration_seconds"].strip())
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError
        except ValueError:
            reasons.append(f"duration missing or invalid: {source_id}")
            duration = None
        decoded_frames = None
        if ffprobe is None or ffmpeg is None:
            reasons.append(f"full video decode not verified: {source_id}")
        else:
            try:
                actual_duration, decoded_frames = probe_video(video, ffprobe, ffmpeg)
                if duration is not None and abs(actual_duration - duration) > 1.0:
                    reasons.append(f"registered duration differs from probed duration: {source_id}")
            except (ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError, TimeoutError) as error:
                reasons.append(f"video probe/decode failed: {source_id}: {type(error).__name__}")
        sources.append({
            "source_id": source_id, "video_path": str(video), "sha256": digest,
            "source_type": source_type, "source_url_or_capture_id": row["source_url_or_capture_id"].strip(),
            "license_or_consent": row["license_or_consent"].strip(),
            "group": group, "split": split, "duration_seconds": duration,
            "decoded_frame_count": decoded_frames,
            "first_annotator": row["first_annotator"].strip(),
            "second_annotator": row["second_annotator"].strip(),
        })
    return sources


def evaluate(register: Path, primary_path: Path, secondary_path: Path, adjudication_path: Path,
             ffprobe: Path | None = None, ffmpeg: Path | None = None) -> tuple[dict, dict | None, dict | None]:
    protocol = read_json(PROTOCOL)
    if protocol["schema"] != "tellme-bact-v2-preregistered-protocol-v1":
        raise ValueError("M312 protocol drift")
    pilot = read_json(PILOT_LABELS)
    old = {row["videoSha256"].lower() for row in pilot["clips"]}
    if len(old) != 12:
        raise ValueError("old pilot identity drift")
    register_rows = read_csv(register, SOURCE_FIELDS)
    first_rows = read_csv(primary_path, LABEL_FIELDS)
    second_rows = read_csv(secondary_path, LABEL_FIELDS)
    adjudication_rows = read_csv(adjudication_path, LABEL_FIELDS)
    reasons: list[str] = []
    sources = verify_sources(register_rows, old, reasons, ffprobe, ffmpeg)
    primary = index_rows(first_rows, "primary")
    secondary = index_rows(second_rows, "secondary")
    adjudication = index_rows(adjudication_rows, "adjudication")
    source_by_id = {source["source_id"]: source for source in sources}
    if len(source_by_id) != len(sources):
        raise ValueError("duplicate opaque source IDs")
    if set(primary) - set(source_by_id) or set(secondary) - set(source_by_id) or set(adjudication) - set(source_by_id):
        raise ValueError("annotation references unknown source ID")
    for source_id in set(secondary) - set(primary):
        reasons.append(f"second annotation lacks first annotation: {source_id}")
    for source_id in sorted(set(source_by_id) - set(primary)):
        reasons.append(f"primary annotation missing: {source_id}")
    parsed_primary = {}
    parsed_secondary = {}
    parsed_adjudication = {}
    for source_id, row in primary.items():
        try:
            parsed_primary[source_id] = parse_label(row, source_by_id[source_id]["first_annotator"])
        except ValueError as error:
            reasons.append(str(error))
    for source_id, row in secondary.items():
        try:
            label = parse_label(row, source_by_id[source_id]["second_annotator"])
            if source_id in parsed_primary and label["annotator"] == parsed_primary[source_id]["annotator"]:
                raise ValueError(f"second annotator is not independent: {source_id}")
            parsed_secondary[source_id] = label
        except ValueError as error:
            reasons.append(str(error))
    for source_id, row in adjudication.items():
        try:
            parsed_adjudication[source_id] = parse_label(row, None)
        except ValueError as error:
            reasons.append(str(error))
    count = len(sources)
    data = protocol["dataset"]
    annotation = protocol["annotation"]
    real_count = sum(source["source_type"] in {"controlled_capture", "public_licensed"} for source in sources)
    ai_count = sum(source["source_type"] == "ai_generated" for source in sources)
    if count < data["minimumIndependentSourceVideos"]:
        reasons.append(f"independent sources {count} < {data['minimumIndependentSourceVideos']}")
    if real_count < data["minimumControlledOrLicensedRealPublicVideos"]:
        reasons.append(f"real/licensed sources {real_count} < {data['minimumControlledOrLicensedRealPublicVideos']}")
    if ai_count > data["maximumAiGeneratedVideos"]:
        reasons.append(f"AI sources {ai_count} > {data['maximumAiGeneratedVideos']}")
    needed_second = math.ceil(count * annotation["minimumIndependentSecondAnnotatorFraction"])
    if len(parsed_secondary) < needed_second:
        reasons.append(f"independent second annotations {len(parsed_secondary)} < {needed_second}")
    common = sorted(set(parsed_primary) & set(parsed_secondary))
    knife_kappa = kappa([(parsed_primary[key]["knife_present"], parsed_secondary[key]["knife_present"]) for key in common])
    action_kappa = kappa([(parsed_primary[key]["action"], parsed_secondary[key]["action"]) for key in common])
    if knife_kappa is None or knife_kappa < annotation["minimumCohenKappaKnife"]:
        reasons.append("knife Cohen kappa missing or below 0.80")
    if action_kappa is None or action_kappa < annotation["minimumCohenKappaAction"]:
        reasons.append("action Cohen kappa missing or below 0.80")
    for key in common:
        left, right = parsed_primary[key], parsed_secondary[key]
        if (left["knife_present"] != right["knife_present"] or left["action"] != right["action"]) and key not in parsed_adjudication:
            reasons.append(f"disagreement lacks preserved adjudication: {key}")
    final_labels = {}
    for key, label in parsed_primary.items():
        if key in parsed_secondary and (label["knife_present"] != parsed_secondary[key]["knife_present"] or label["action"] != parsed_secondary[key]["action"]):
            if key not in parsed_adjudication:
                continue
            final_labels[key] = parsed_adjudication[key]
        else:
            final_labels[key] = label
    for split in SPLITS:
        rows = [final_labels[source["source_id"]] for source in sources if source["split"] == split and source["source_id"] in final_labels]
        if not any(row["knife_present"] for row in rows) or not any(not row["knife_present"] for row in rows):
            reasons.append(f"{split} lacks both knife classes")
        if not all(any(row["action"] == action for row in rows) for action in ACTIONS):
            reasons.append(f"{split} lacks one or more action classes")
    split_count = {split: sum(source["split"] == split for source in sources) for split in SPLITS}
    if count and not 0.20 <= split_count["calibration"] / count <= 0.45:
        reasons.append("calibration fraction outside frozen approximately-one-third range")
    report = {
        "schema": "tellme-bact-v2-formal-dataset-gate-v1",
        "status": "PASS_DATA_AND_ANNOTATION_GATE" if not reasons else "PENDING_DATA_OR_ANNOTATION",
        "protocol_sha256": hash_file(PROTOCOL),
        "source_register_sha256": hash_file(register),
        "primary_labels_sha256": hash_file(primary_path),
        "secondary_labels_sha256": hash_file(secondary_path),
        "adjudication_sha256": hash_file(adjudication_path),
        "source_count": count, "real_or_licensed_count": real_count, "ai_count": ai_count,
        "primary_complete_count": len(parsed_primary),
        "independent_second_count": len(parsed_secondary),
        "knife_kappa": knife_kappa, "action_kappa": action_kappa,
        "split_source_counts": split_count,
        "reasons": sorted(set(reasons)),
        "old_pilot_allowed_in_new_test": False,
        "video_decode_verified_count": sum(source["decoded_frame_count"] is not None for source in sources),
        "ffprobe_sha256": hash_file(ffprobe) if ffprobe else None,
        "ffmpeg_sha256": hash_file(ffmpeg) if ffmpeg else None,
        "blind_prediction_started": False,
        "held_out_opened": False,
        "board_runs": 0,
    }
    if reasons:
        return report, None, None
    label_manifest = {
        "schema": "tellme-bact-v2-frozen-human-labels-v1",
        "protocol_sha256": report["protocol_sha256"],
        "sources": [
            {**source, "primary": parsed_primary[source["source_id"]],
             "secondary": parsed_secondary.get(source["source_id"]),
             "adjudication": parsed_adjudication.get(source["source_id"]),
             "final": final_labels[source["source_id"]]}
            for source in sources
        ],
    }
    blind = {
        "schema": "tellme-bact-v2-blind-input-manifest-v1",
        "protocol_sha256": report["protocol_sha256"],
        "sources": [
            {"source_id": source["source_id"], "video_path": source["video_path"], "sha256": source["sha256"]}
            for source in sources
        ],
    }
    return report, label_manifest, blind


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--secondary", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, help="Exact local ffprobe executable for media metadata")
    parser.add_argument("--ffmpeg", type=Path, help="Exact local ffmpeg executable for complete video decode")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite an audit: {args.output_dir}")
    if (args.ffprobe is None) != (args.ffmpeg is None):
        parser.error("--ffprobe and --ffmpeg must be supplied together")
    if args.ffprobe is not None and (not args.ffprobe.is_file() or not args.ffmpeg.is_file()):
        parser.error("ffprobe/ffmpeg executable missing")
    report, labels, blind = evaluate(args.register, args.primary, args.secondary, args.adjudication,
                                     args.ffprobe, args.ffmpeg)
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "DATA_GATE_RESULT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if labels is not None and blind is not None:
        (args.output_dir / "FROZEN_HUMAN_LABELS.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (args.output_dir / "BLIND_INPUT_MANIFEST.json").write_text(json.dumps(blind, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M322_BACT_V2_DATA_GATE_{report['status']} sources={report['source_count']} real={report['real_or_licensed_count']} first={report['primary_complete_count']} second={report['independent_second_count']} reasons={len(report['reasons'])}")
    return 0 if report["status"] == "PASS_DATA_AND_ANNOTATION_GATE" or not args.require_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
