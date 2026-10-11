#!/usr/bin/env python3
"""Contract tests for the M308 one-shot held-out evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.dataset import ACTIONS
from bact.evaluation import BASELINE_IDS
from bact.robustness import CONDITIONS


EVALUATOR = Path(__file__).with_name("m308_run_one_shot_bact_evaluation.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture() -> tuple[dict, dict]:
    clips = []
    action_rows = list(ACTIONS) + ["WORKING"]
    for split in ("calibration", "test"):
        for index, action in enumerate(action_rows):
            knife = index % 2 == 0
            conditions = {
                "lowLight": index in {0, 3},
                "occlusion": index in {1, 3},
                "smallKnife": index in {2, 4},
            }
            if conditions["smallKnife"]:
                knife = True
            clip_id = f"{split}-{index}"
            clips.append(
                {
                    "clipId": clip_id,
                    "split": split,
                    "sourceFilename": f"not-truth-{clip_id}.mp4",
                    "videoSha256": hashlib.sha256(clip_id.encode()).hexdigest(),
                    "annotationStatus": "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT",
                    "action": action,
                    "knifePresent": knife,
                    "actionConstant": True,
                    "knifeConstant": True,
                    "watchedComplete": True,
                    "annotator": "synthetic-contract",
                    "conditions": conditions,
                }
            )
    labels = {"schema": "tellme-bact-clip-constant-v1", "clips": clips}
    baselines = {}
    for baseline_index, (name, candidate_id) in enumerate(BASELINE_IDS.items()):
        rows = []
        for clip in clips:
            logits = {action: -3.0 for action in ACTIONS}
            logits[clip["action"]] = 3.0 - baseline_index * 0.01
            rows.append(
                {
                    "clipId": clip["clipId"],
                    "knifeScore": (2.0 if clip["knifePresent"] else -2.0) - baseline_index * 0.02,
                    "actionLogits": logits,
                }
            )
        baselines[name] = {"candidateId": candidate_id, "predictions": rows}
    return labels, {"schema": "tellme-bact-four-baseline-predictions-v1", "baselines": baselines}


def run(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVALUATOR), "--workspace", str(workspace)],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="m308-contract-") as directory:
        workspace = Path(directory)
        labels_path = workspace / "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json"
        predictions_path = workspace / "data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json"
        m304_path = workspace / "deployment/mage_vl4b/M304_HUMAN_REVIEW_IMPORT_RESULT.json"
        m307_path = workspace / "deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json"
        result_path = workspace / "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_RESULT.json"
        seal_path = workspace / "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_SEAL.json"
        labels, predictions = fixture()
        write_json(predictions_path, predictions)
        write_json(
            m307_path,
            {
                "status": "PASS_RAW_PREDICTIONS_LABEL_BLIND",
                "allFinite": True,
                "filenameHintsRead": False,
                "humanLabelsRead": False,
                "heldOutLabelsRead": False,
                "clipCount": 12,
                "baselineCount": 4,
                "completedPredictionRows": 48,
                "modelForwardCount": 96,
                "predictions": "data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json",
                "predictionsSha256": sha(predictions_path),
                "geometrySha256": "geometry-contract",
            },
        )
        write_json(
            m304_path,
            {
                "labelsWritten": False,
                "formalAccuracyAllowed": False,
                "semanticRobustnessAllowed": False,
                "qcPassCount": 0,
                "pendingCount": 12,
                "workbookSha256": "workbook-contract",
            },
        )
        blocked = run(workspace)
        if blocked.returncode == 0 or result_path.exists() or seal_path.exists():
            raise RuntimeError("M308 missing labels did not fail before opening held-out test")

        write_json(labels_path, labels)
        write_json(
            m304_path,
            {
                "labelsWritten": True,
                "formalAccuracyAllowed": True,
                "semanticRobustnessAllowed": True,
                "qcPassCount": 12,
                "pendingCount": 0,
                "workbookSha256": "workbook-contract",
                "labels": "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json",
                "labelsSha256": sha(labels_path),
            },
        )
        first = run(workspace)
        if first.returncode != 0:
            raise RuntimeError(first.stdout + first.stderr)
        first_result_sha = sha(result_path)
        first_seal = json.loads(seal_path.read_text(encoding="utf-8"))
        if first_seal.get("status") != "COMPLETE" or first_seal.get("resultSha256") != first_result_sha:
            raise RuntimeError("M308 first run did not complete immutable seal")

        repeated = run(workspace)
        if repeated.returncode != 0 or "ALREADY_SEALED" not in repeated.stdout:
            raise RuntimeError("M308 identical rerun did not verify existing sealed result")
        if sha(result_path) != first_result_sha:
            raise RuntimeError("M308 identical rerun changed result")

        predictions["baselines"]["bact"]["predictions"][0]["knifeScore"] += 0.25
        write_json(predictions_path, predictions)
        changed = run(workspace)
        if changed.returncode == 0 or sha(result_path) != first_result_sha:
            raise RuntimeError("M308 changed input bypassed one-shot seal")

    print(
        "M308_ONE_SHOT_CONTRACT_PASS "
        "missing_labels_blocked=true identical_rerun_verified=true changed_input_rejected=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
