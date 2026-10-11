#!/usr/bin/env python3
"""Prove M296 source closure while keeping pending labels fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.dataset import validate_target_scene_manifest


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    manifest_path = workspace / "data/bact_target_scene/M296_TARGET_SCENE_MANIFEST_DRAFT.json"
    intake_path = workspace / "deployment/mage_vl4b/M296_TARGET_SCENE_INTAKE_RESULT.json"
    output_path = workspace / "deployment/mage_vl4b/M296_TARGET_SCENE_SOURCE_CLOSURE_RESULT.json"
    if output_path.exists():
        raise RuntimeError(f"refuse to overwrite M296 source closure: {output_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    summary = validate_target_scene_manifest(manifest, formal=False)
    expected_splits = {"train": 0, "calibration": 6, "test": 6}
    if summary["split_clip_counts"] != expected_splits:
        raise RuntimeError(f"M296 split closure mismatch: {summary['split_clip_counts']}")
    if len(summary["pending_annotation_clip_ids"]) != 12:
        raise RuntimeError("M296 pending clip count mismatch")
    if intake["duplicate_filename_groups"] or intake["unique_source_video_count"] != 12:
        raise RuntimeError("M296 source dedup closure mismatch")
    rejected = False
    rejection = None
    try:
        validate_target_scene_manifest(manifest, formal=True)
    except ValueError as error:
        rejection = str(error)
        rejected = "incomplete human annotations" in rejection
    if not rejected:
        raise RuntimeError("M296 pending labels did not fail closed")
    result = {
        "date": "2026-09-03",
        "gate": "M296-target-scene-source-count-and-pending-label-closure",
        "status": "PASS_SOURCE_COUNT_READY_LABELS_FAIL_CLOSED",
        "classification": "Twelve unique AI-generated pilot source videos and split isolation only; all labels remain pending human verification, so no semantic accuracy or real-world validity claim is allowed.",
        "manifest": str(manifest_path.relative_to(workspace)).replace("\\", "/"),
        "manifest_sha256": sha256(manifest_path),
        "intake_result": str(intake_path.relative_to(workspace)).replace("\\", "/"),
        "intake_result_sha256": sha256(intake_path),
        "unique_source_video_count": 12,
        "split_clip_counts": summary["split_clip_counts"],
        "sampled_frame_count": intake["sampled_frame_count"],
        "duplicate_source_groups": intake["duplicate_filename_groups"],
        "pending_human_clip_count": len(summary["pending_annotation_clip_ids"]),
        "formal_manifest_rejected": rejected,
        "formal_rejection": rejection,
        "semantic_accuracy_passed": False,
        "real_world_external_validity_claimed": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Human-review the 300 sampled frames, promote clips only after HUMAN_VERIFIED_COMPLETE, then freeze thresholds using calibration only before a single held-out test run.",
    }
    partial = output_path.with_name(output_path.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, output_path)
    print("M296_TARGET_SCENE_SOURCE_CLOSURE_PASS unique=12 calibration=6 test=6 pending_human=12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
