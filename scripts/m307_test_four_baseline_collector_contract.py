#!/usr/bin/env python3
"""Offline negative/positive contract tests for the M307 collector."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


SCRIPT = Path(__file__).with_name("m307_collect_four_baseline_predictions.py")
SPEC = importlib.util.spec_from_file_location("m307_collector", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def make_workspace(root: Path) -> tuple[dict, list[dict]]:
    inbox = root / "data/bact_target_scene/inbox"
    inbox.mkdir(parents=True)
    clips = []
    for index in range(12):
        filename = f"misleading_{index:02d}.mp4"
        payload = f"clip-{index}".encode()
        (inbox / filename).write_bytes(payload)
        clips.append(
            {
                "clip_id": f"clip-{index}",
                "split": "calibration" if index < 6 else "test",
                "source_filename": filename,
                "video_sha256": hashlib.sha256(payload).hexdigest(),
                "filename_hints": {"must_not_be_read": "WRONG_LABEL"},
            }
        )
    manifest = {"schema": "tellme-bact-target-scene-v1", "clips": clips}
    inventory = MODULE.source_inventory(root, manifest)
    return manifest, inventory


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest, inventory = make_workspace(root)
        if len(inventory) != 12 or any("filename_hints" in row for row in inventory):
            raise RuntimeError("M307 source whitelist contract failed")

        geometry = {
            "schema": "tellme-bact-four-baseline-prediction-geometry-v1",
            "status": "PASS_EXACT_GEOMETRY_AND_TASK_TOKEN_CONTRACT",
            "baselineIds": dict(MODULE.BASELINE_IDS),
            "candidates": {},
        }
        for name, candidate_id in MODULE.BASELINE_IDS.items():
            geometry["candidates"][name] = {
                "candidateId": candidate_id,
                "knifePromptTokens": 144,
                "targetPromptTokensPerProbe": 144,
                "actionPromptUsesNeutralPadding": False,
                "boardTimingClaimAllowed": False,
            }
        candidates = MODULE.validate_geometry(geometry)

        completed = {}
        for name, candidate_id in MODULE.BASELINE_IDS.items():
            for row in inventory:
                completed[f"{name}/{row['clipId']}"] = {
                    "candidateId": candidate_id,
                    "knifeScore": 0.25,
                    "actionLogits": {
                        action: float(index)
                        for index, action in enumerate(MODULE.ACTION_NAMES)
                    },
                    "knifePromptTokens": 144,
                    "actionPromptTokens": 144,
                    "knifeForwardMs": 1.0,
                    "actionForwardMs": 1.0,
                    "finite": True,
                }
        predictions = MODULE.assemble_predictions(inventory, candidates, completed)
        if set(predictions["baselines"]) != set(MODULE.BASELINE_IDS):
            raise RuntimeError("M307 assembly baseline contract failed")

        incomplete = copy.deepcopy(completed)
        incomplete.pop(next(iter(incomplete)))
        incomplete_rejected = False
        try:
            MODULE.assemble_predictions(inventory, candidates, incomplete)
        except ValueError as error:
            incomplete_rejected = "incomplete predictions" in str(error)
        if not incomplete_rejected:
            raise RuntimeError("M307 incomplete progress was not rejected")

        duplicate = copy.deepcopy(manifest)
        duplicate["clips"][1]["video_sha256"] = duplicate["clips"][0]["video_sha256"]
        (root / "data/bact_target_scene/inbox" / duplicate["clips"][1]["source_filename"]).write_bytes(
            (root / "data/bact_target_scene/inbox" / duplicate["clips"][0]["source_filename"]).read_bytes()
        )
        duplicate_rejected = False
        try:
            MODULE.source_inventory(root, duplicate)
        except ValueError as error:
            duplicate_rejected = "duplicate source hash" in str(error)
        if not duplicate_rejected:
            raise RuntimeError("M307 duplicate source was not rejected")

        progress_path = root / "progress.json"
        identity = {"run": "one"}
        MODULE.atomic_json(
            progress_path,
            {
                "schema": "tellme-bact-four-baseline-progress-v1",
                "sessionIdentity": identity,
                "completed": {},
            },
        )
        identity_rejected = False
        try:
            MODULE.load_or_initialize_progress(progress_path, {"run": "two"})
        except ValueError as error:
            identity_rejected = "identity mismatch" in str(error)
        if not identity_rejected:
            raise RuntimeError("M307 progress identity mismatch was not rejected")

    print(
        "M307_COLLECTOR_CONTRACT_PASS clips=12 baselines=4 "
        "filename_hints_read=false negative_paths=3"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
