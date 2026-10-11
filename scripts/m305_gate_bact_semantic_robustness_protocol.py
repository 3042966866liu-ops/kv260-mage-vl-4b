#!/usr/bin/env python3
"""Gate the final BACT semantic/condition robustness protocol offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.dataset import ACTIONS
from bact.evaluation import BASELINE_IDS, canonical_sha256, evaluate_four_baselines
from bact.robustness import CONDITIONS, evaluate_semantic_robustness


def make_labels() -> dict:
    clips = []
    actions = list(ACTIONS) + ["WORKING"]
    condition_rows = [
        {"lowLight": True, "occlusion": False, "smallKnife": False},
        {"lowLight": False, "occlusion": True, "smallKnife": False},
        {"lowLight": False, "occlusion": False, "smallKnife": True},
        {"lowLight": True, "occlusion": True, "smallKnife": False},
        {"lowLight": False, "occlusion": False, "smallKnife": True},
        {"lowLight": False, "occlusion": False, "smallKnife": False},
    ]
    for split in ("calibration", "test"):
        for index, action in enumerate(actions):
            knife = index % 2 == 0
            conditions = dict(condition_rows[index])
            if conditions["smallKnife"]:
                knife = True
            clips.append(
                {
                    "clipId": f"{split}-{index}",
                    "split": split,
                    "sourceFilename": f"misleading-name-{split}-{index}.mp4",
                    "videoSha256": hashlib.sha256(f"{split}-{index}".encode()).hexdigest(),
                    "annotationStatus": "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT",
                    "action": action,
                    "knifePresent": knife,
                    "actionConstant": True,
                    "knifeConstant": True,
                    "watchedComplete": True,
                    "annotator": "synthetic-protocol-gate",
                    "conditions": conditions,
                    "notes": "synthetic contract only",
                }
            )
    return {"schema": "tellme-bact-clip-constant-v1", "clips": clips}


def make_predictions(labels: dict) -> dict:
    baselines = {}
    for baseline_index, (name, candidate_id) in enumerate(BASELINE_IDS.items()):
        rows = []
        for index, clip in enumerate(labels["clips"]):
            logits = {action: -2.0 - ACTIONS.index(action) * 0.01 for action in ACTIONS}
            logits[clip["action"]] = 3.0
            base_score = 2.0 if clip["knifePresent"] else -2.0
            rows.append(
                {
                    "clipId": clip["clipId"],
                    "knifeScore": base_score - baseline_index * 0.1 + (index % 3) * 0.02,
                    "actionLogits": logits,
                }
            )
        baselines[name] = {"candidateId": candidate_id, "predictions": rows}
    return {"schema": "tellme-bact-four-baseline-predictions-v1", "baselines": baselines}


def expect_rejection(labels: dict, predictions: dict, expected: str) -> bool:
    try:
        evaluate_semantic_robustness(labels, predictions)
    except ValueError as error:
        return expected in str(error)
    return False


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()

    labels = make_labels()
    predictions = make_predictions(labels)
    metrics = evaluate_semantic_robustness(labels, predictions, minimum_recall=0.9)
    if metrics["baselineOrder"] != list(BASELINE_IDS):
        raise RuntimeError("M305 exact four-baseline order failed")
    if metrics["conditions"] != list(CONDITIONS):
        raise RuntimeError("M305 condition identity failed")

    original_thresholds = {
        name: value["primary"]["thresholdFreeze"]["threshold"]
        for name, value in metrics["baselines"].items()
    }
    altered = copy.deepcopy(labels)
    for clip in altered["clips"]:
        if clip["split"] == "test":
            clip["knifePresent"] = not clip["knifePresent"]
            if not clip["knifePresent"]:
                clip["conditions"]["smallKnife"] = False
    # Isolate the leakage test from condition-slice coverage: it asks only
    # whether held-out labels can change a calibration-only threshold.
    altered_metrics = evaluate_four_baselines(altered, predictions, minimum_recall=0.9)
    altered_thresholds = {
        name: value["thresholdFreeze"]["threshold"]
        for name, value in altered_metrics.items()
    }
    threshold_invariance = original_thresholds == altered_thresholds
    if not threshold_invariance:
        raise RuntimeError("M305 held-out labels influenced calibration thresholds")

    uncertain = copy.deepcopy(labels)
    uncertain["clips"][0]["conditions"]["lowLight"] = "UNCERTAIN"
    uncertain_rejected = expect_rejection(
        uncertain, predictions, "human-confirmed boolean"
    )
    if not uncertain_rejected:
        raise RuntimeError("M305 uncertain condition was not rejected")

    missing = copy.deepcopy(labels)
    del missing["clips"][0]["conditions"]["occlusion"]
    missing_rejected = expect_rejection(
        missing, predictions, "exact and complete"
    )
    if not missing_rejected:
        raise RuntimeError("M305 missing condition was not rejected")

    wrong_identity = copy.deepcopy(predictions)
    wrong_identity["baselines"]["bact"]["candidateId"] = "wrong"
    identity_rejected = expect_rejection(labels, wrong_identity, "identity mismatch")
    if not identity_rejected:
        raise RuntimeError("M305 baseline identity mismatch was not rejected")

    m304_path = workspace / "deployment/mage_vl4b/M304_HUMAN_REVIEW_IMPORT_RESULT.json"
    m304 = json.loads(m304_path.read_text(encoding="utf-8"))
    real_labels_ready = bool(m304.get("formalAccuracyAllowed")) and bool(
        m304.get("labelsWritten")
    )
    labels_path = workspace / "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json"
    predictions_path = workspace / "data/bact_target_scene/M305_FOUR_BASELINE_PREDICTIONS.json"
    real_evaluation_allowed = real_labels_ready and labels_path.is_file() and predictions_path.is_file()
    if real_evaluation_allowed:
        raise RuntimeError(
            "M305 protocol gate must not open held-out results; use the separate final evaluator"
        )

    result = {
        "date": "2026-09-03",
        "gate": "M305-four-baseline-semantic-robustness-protocol",
        "status": "PASS_PROTOCOL_REAL_LABELS_AND_PREDICTIONS_PENDING",
        "classification": (
            "Executable fail-closed protocol for exact four-baseline calibration-only threshold freezing, "
            "held-out knife recall/false-alarm, five-action Macro-F1, leave-one-calibration-clip-out "
            "threshold sensitivity and explicit low-light/occlusion/small-knife slices. Synthetic values test "
            "the protocol only; no pilot accuracy or real-world validity is claimed."
        ),
        "baselineIds": BASELINE_IDS,
        "conditions": list(CONDITIONS),
        "source": "bact/robustness.py",
        "sourceSha256": hashlib.sha256(
            (workspace / "bact/robustness.py").read_bytes()
        ).hexdigest(),
        "gateSource": "scripts/m305_gate_bact_semantic_robustness_protocol.py",
        "gateSourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "syntheticLabelsSha256": canonical_sha256(labels),
        "syntheticPredictionsSha256": canonical_sha256(predictions),
        "syntheticMetrics": metrics,
        "testLabelChangesLeaveCalibrationThresholdsUnchanged": threshold_invariance,
        "uncertainConditionRejected": uncertain_rejected,
        "missingConditionRejected": missing_rejected,
        "wrongBaselineIdentityRejected": identity_rejected,
        "filenameHintsUsedAsGroundTruth": False,
        "realM304Result": str(m304_path.relative_to(workspace)).replace("\\", "/"),
        "realM304ResultSha256": hashlib.sha256(m304_path.read_bytes()).hexdigest(),
        "realHumanLabelsReady": real_labels_ready,
        "realPredictionsReady": predictions_path.is_file(),
        "formalAccuracyAllowed": False,
        "semanticRobustnessAllowed": False,
        "realWorldExternalValidityClaimAllowed": False,
        "boardExecutionRun": False,
        "activeM254M256Changed": False,
        "bootDtbCmaPartitionsChanged": False,
        "stableRollbackPreserved": True,
        "nextGate": (
            "Complete 12/12 human review and freeze labels; collect raw predictions for all exact four "
            "baselines without reading test labels; then run the separate one-shot held-out evaluator."
        ),
    }
    atomic_json(args.result.resolve(), result)
    print(
        "M305_BACT_SEMANTIC_ROBUSTNESS_PROTOCOL_PASS "
        "baselines=4 conditions=3 real_labels_ready=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
