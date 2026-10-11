#!/usr/bin/env python3
"""Validate target-scene schema and prove incomplete labels fail closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.dataset import ACTIONS, validate_target_scene_manifest


def frame(sequence: int, action: str, knife: bool) -> dict:
    return {
        "sequence": sequence,
        "timestamp_ms": 500 + sequence * 500,
        "knife_present": knife,
        "people": [{"track_id": 1, "bbox_xyxy": [0.1, 0.1, 0.6, 0.9], "action": action}],
    }


def complete_clip(clip_id: str, split: str, fill: str) -> dict:
    frames = [frame(index, action, index % 2 == 0) for index, action in enumerate(ACTIONS)]
    return {
        "clip_id": clip_id,
        "split": split,
        "video_sha256": fill * 64,
        "annotation_status": "HUMAN_VERIFIED_COMPLETE",
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    draft_path = workspace / "data/bact_target_scene/M291_TARGET_SCENE_MANIFEST_DRAFT.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))

    draft_summary = validate_target_scene_manifest(draft, formal=False)
    draft_rejected = False
    try:
        validate_target_scene_manifest(draft, formal=True)
    except ValueError as error:
        draft_rejected = "incomplete human annotations" in str(error)
    if not draft_rejected:
        raise RuntimeError("M291 incomplete real draft did not fail closed")

    synthetic = {
        "schema": "tellme-bact-target-scene-v1",
        "clips": [
            complete_clip("cal-01", "calibration", "a"),
            complete_clip("test-01", "test", "b"),
        ],
    }
    synthetic_summary = validate_target_scene_manifest(synthetic, formal=True)

    leaked = json.loads(json.dumps(synthetic))
    leaked["clips"][1]["video_sha256"] = leaked["clips"][0]["video_sha256"]
    leakage_rejected = False
    try:
        validate_target_scene_manifest(leaked, formal=True)
    except ValueError as error:
        leakage_rejected = "across splits" in str(error)
    if not leakage_rejected:
        raise RuntimeError("M291 source-video split leakage was not rejected")

    result = {
        "date": "2026-09-02",
        "gate": "M291-target-scene-manifest-schema-and-intake",
        "status": "PASS_SCHEMA_REAL_DRAFT_NOT_FORMAL",
        "classification": (
            "Schema and fail-closed checks passed; the one registered real motorcycle source remains "
            "PENDING_HUMAN and is not a formal target-scene dataset or accuracy result."
        ),
        "real_draft": str(draft_path.relative_to(workspace)).replace("\\", "/"),
        "real_draft_sha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
        "real_draft_summary": draft_summary,
        "real_draft_formal_rejected": draft_rejected,
        "synthetic_complete_schema_summary": synthetic_summary,
        "source_video_split_leakage_rejected": leakage_rejected,
        "required_actions": list(ACTIONS),
        "semantic_accuracy_passed": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Collect and human-annotate source-disjoint workplace monitoring clips until calibration and test "
            "both cover knife positive/negative and all five actions; then freeze thresholds/configuration."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M291_TARGET_SCENE_MANIFEST_GATE_PASS real_draft_formal_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
