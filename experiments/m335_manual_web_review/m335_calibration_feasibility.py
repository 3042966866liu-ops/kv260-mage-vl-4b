#!/usr/bin/env python3
"""Merge full-frame calibration scans; never tune on the held-out test clips."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
SAFE_THRESHOLD = 0.20
ALARM_THRESHOLD = 0.80


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--scans", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    by_video = {clip["sourceFilename"]: clip for clip in labels["clips"] if clip["split"] == "calibration"}
    if len(by_video) != 6 or any(clip["annotationStatus"] != "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT"
                                 for clip in by_video.values()):
        raise RuntimeError("expected exactly six human-verified calibration clips")
    scans = {}
    identities = []
    for path in args.scans:
        scan = json.loads(path.read_text(encoding="utf-8"))
        if scan["checkpoint_sha256"] != CHECKPOINT_SHA or scan["unchanged_alarm_threshold"] != ALARM_THRESHOLD:
            raise RuntimeError(f"detector identity or policy changed: {path}")
        identities.append({"path": str(path), "sha256": digest(path)})
        for video in scan["videos"]:
            name = video["video"]
            if name not in by_video or name in scans:
                raise RuntimeError(f"unexpected or duplicate calibration clip: {name}")
            if video["sha256"] != by_video[name]["videoSha256"]:
                raise RuntimeError(f"human-label/video hash mismatch: {name}")
            if video["frames"] != len(video["samples"]):
                raise RuntimeError(f"not a complete frame scan: {name}")
            if [row["frame_index"] for row in video["samples"]] != list(range(video["frames"])):
                raise RuntimeError(f"nonconsecutive scan: {name}")
            scans[name] = video
    if set(scans) != set(by_video):
        raise RuntimeError(f"missing calibration clips: {sorted(set(by_video) - set(scans))}")
    rows = []
    for name, clip in sorted(by_video.items()):
        video = scans[name]
        score = video["max_knife_score"]
        rows.append({"video": name, "video_sha256": clip["videoSha256"],
                     "knife_present_human": bool(clip["knifePresent"]),
                     "frames": video["frames"], "raw_max_knife_score": score,
                     "runtime_max_knife_score": 0.0 if score is None or score < 0.05 else score,
                     "original_policy_alarm_count": video["sampled_alarm_count"]})
    positives = [row for row in rows if row["knife_present_human"]]
    negatives = [row for row in rows if not row["knife_present_human"]]
    no_feasible = any(row["runtime_max_knife_score"] <= SAFE_THRESHOLD for row in positives)
    result = {
        "gate": "M335-fast-knife-calibration-feasibility",
        "status": "NO_FEASIBLE_ALARM_ONLY_THRESHOLD" if no_feasible else "CALIBRATION_FEASIBLE_RANGE_NOT_YET_VALIDATED",
        "scope": "Six human-labeled AI-generated calibration clips, OpenCV approximate browser crop; no board or held-out test run",
        "checkpoint_sha256": CHECKPOINT_SHA,
        "labels_sha256": digest(args.labels), "scan_inputs": identities,
        "current_safe_threshold": SAFE_THRESHOLD, "current_alarm_threshold": ALARM_THRESHOLD,
        "policy_requires_safe_below_alarm": True,
        "positive_clips": len(positives), "negative_clips": len(negatives),
        "total_frames": sum(row["frames"] for row in rows),
        "rows": rows,
        "held_out_test_clips_scanned": False,
        "thresholds_modified": False,
        "candidate_promoted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps({"status": result["status"], "positive_clips": len(positives),
                      "negative_clips": len(negatives), "total_frames": result["total_frames"]}))


if __name__ == "__main__":
    main()
