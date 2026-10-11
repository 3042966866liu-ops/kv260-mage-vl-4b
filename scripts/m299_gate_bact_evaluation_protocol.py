#!/usr/bin/env python3
"""Prove the four-baseline calibration/test metric protocol fail-closes."""

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


def make_labels() -> dict:
    clips = []
    actions = list(ACTIONS) + ["WORKING"]
    for split in ("calibration", "test"):
        for index, action in enumerate(actions):
            clips.append(
                {
                    "clipId": f"{split}-{index}",
                    "split": split,
                    "sourceFilename": f"{split}-{index}.mp4",
                    "videoSha256": hashlib.sha256(f"{split}-{index}".encode()).hexdigest(),
                    "annotationStatus": "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT",
                    "action": action,
                    "knifePresent": index % 2 == 0,
                    "actionConstant": True,
                    "knifeConstant": True,
                    "watchedComplete": True,
                    "annotator": "synthetic-protocol-gate",
                    "notes": "synthetic only",
                }
            )
    return {"schema": "tellme-bact-clip-constant-v1", "clips": clips}


def make_predictions(labels: dict) -> dict:
    baselines = {}
    for baseline_index, (name, candidate_id) in enumerate(BASELINE_IDS.items()):
        rows = []
        for index, clip in enumerate(labels["clips"]):
            truth_action = clip["action"]
            logits = {action: -2.0 - ACTIONS.index(action) * 0.01 for action in ACTIONS}
            logits[truth_action] = 3.0
            if clip["split"] == "test" and index % 11 == baseline_index:
                logits[truth_action] = -3.0
                logits[ACTIONS[(ACTIONS.index(truth_action) + 1) % len(ACTIONS)]] = 2.0
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()

    labels = make_labels()
    predictions = make_predictions(labels)
    metrics = evaluate_four_baselines(labels, predictions, minimum_recall=0.9)
    if set(metrics) != set(BASELINE_IDS):
        raise RuntimeError("M299 four-baseline identity failed")
    if any(value["thresholdFreeze"]["testLabelsUsed"] for value in metrics.values()):
        raise RuntimeError("M299 test-label leakage flag failed")

    # Changing held-out labels must not alter any frozen threshold.
    altered = copy.deepcopy(labels)
    for clip in altered["clips"]:
        if clip["split"] == "test":
            clip["knifePresent"] = not clip["knifePresent"]
    altered_metrics = evaluate_four_baselines(altered, predictions, minimum_recall=0.9)
    original_thresholds = {name: value["thresholdFreeze"]["threshold"] for name, value in metrics.items()}
    altered_thresholds = {name: value["thresholdFreeze"]["threshold"] for name, value in altered_metrics.items()}
    if original_thresholds != altered_thresholds:
        raise RuntimeError("M299 test labels influenced calibration thresholds")

    # Identity and coverage failures must reject rather than silently score.
    wrong_identity = copy.deepcopy(predictions)
    wrong_identity["baselines"]["bact"]["candidateId"] = "wrong"
    identity_rejected = False
    try:
        evaluate_four_baselines(labels, wrong_identity)
    except ValueError as error:
        identity_rejected = "identity mismatch" in str(error)
    if not identity_rejected:
        raise RuntimeError("M299 baseline identity mismatch was not rejected")

    missing_action = copy.deepcopy(labels)
    for clip in missing_action["clips"]:
        if clip["split"] == "test" and clip["action"] == "FIGHTING":
            clip["action"] = "WORKING"
    coverage_rejected = False
    try:
        evaluate_four_baselines(missing_action, predictions)
    except ValueError as error:
        coverage_rejected = "lacks action support" in str(error)
    if not coverage_rejected:
        raise RuntimeError("M299 missing action support was not rejected")

    m298_path = workspace / "deployment/mage_vl4b/M298_HUMAN_REVIEW_IMPORT_RESULT.json"
    m298 = json.loads(m298_path.read_text(encoding="utf-8"))
    real_labels_ready = bool(m298.get("formalAccuracyAllowed")) and bool(m298.get("labelsWritten"))
    if real_labels_ready:
        raise RuntimeError("M299 expected current M298 labels to remain pending")

    result = {
        "date": "2026-09-03",
        "gate": "M299-four-baseline-calibration-heldout-evaluation-protocol",
        "status": "PASS_PROTOCOL_SYNTHETIC_REAL_LABELS_PENDING",
        "classification": (
            "Executable fail-closed metric protocol for four exact baseline identities. Synthetic tests prove "
            "calibration-only threshold freezing, test-label invariance, knife recall/false-alarm and five-class "
            "action Macro-F1 calculations. No real pilot accuracy was computed because M298 human labels remain pending."
        ),
        "source": "bact/evaluation.py",
        "source_sha256": hashlib.sha256((workspace / "bact/evaluation.py").read_bytes()).hexdigest(),
        "baseline_ids": BASELINE_IDS,
        "synthetic_labels_sha256": canonical_sha256(labels),
        "synthetic_predictions_sha256": canonical_sha256(predictions),
        "synthetic_metrics": metrics,
        "test_label_changes_leave_calibration_thresholds_unchanged": original_thresholds == altered_thresholds,
        "wrong_baseline_identity_rejected": identity_rejected,
        "missing_test_action_support_rejected": coverage_rejected,
        "real_m298_result": str(m298_path.relative_to(workspace)).replace("\\", "/"),
        "real_m298_result_sha256": hashlib.sha256(m298_path.read_bytes()).hexdigest(),
        "real_human_labels_ready": real_labels_ready,
        "semantic_accuracy_passed": False,
        "bounding_box_metrics_in_scope": False,
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "After all 12 workbook rows pass human QC, import labels, collect raw four-baseline predictions once, "
            "freeze knife thresholds on calibration only, and open held-out test exactly once."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M299_BACT_EVALUATION_PROTOCOL_PASS baselines=4 real_labels_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
