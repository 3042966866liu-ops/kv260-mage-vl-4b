#!/usr/bin/env python3
"""Run the label-gated BACT held-out evaluation exactly once.

The evaluator is deliberately separate from prediction collection.  It opens
the held-out labels only after both the human-review import and the label-blind
prediction collection have been hash verified.  A seal is written before test
labels are evaluated so an interrupted or changed run fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.evaluation import BASELINE_IDS
from bact.robustness import CONDITIONS, evaluate_semantic_robustness


EXPECTED_M307_STATUS = "PASS_RAW_PREDICTIONS_LABEL_BLIND"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def resolve_workspace_path(workspace: Path, value: str, field: str) -> Path:
    candidate = (workspace / value).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as error:
        raise ValueError(f"{field} escapes workspace") from error
    return candidate


def require_file_hash(path: Path, expected: object, field: str) -> str:
    if not path.is_file():
        raise ValueError(f"{field} file is missing: {path}")
    observed = file_sha256(path)
    if observed != str(expected):
        raise ValueError(f"{field} SHA-256 mismatch")
    return observed


def build_identity(
    *,
    m304_result_path: Path,
    m304_result: dict,
    labels_path: Path,
    m307_result_path: Path,
    m307_result: dict,
    predictions_path: Path,
    evaluator_path: Path,
    minimum_recall: float,
) -> dict:
    return {
        "m304ResultSha256": file_sha256(m304_result_path),
        "labelsSha256": file_sha256(labels_path),
        "m307ResultSha256": file_sha256(m307_result_path),
        "predictionsSha256": file_sha256(predictions_path),
        "predictionGeometrySha256": str(m307_result["geometrySha256"]),
        "evaluatorSha256": file_sha256(evaluator_path),
        "minimumRecallConstraint": minimum_recall,
        "baselineIds": dict(BASELINE_IDS),
        "conditions": list(CONDITIONS),
        "m304WorkbookSha256": str(m304_result["workbookSha256"]),
    }


def verify_ready_inputs(
    workspace: Path,
    m304_result_path: Path,
    labels_path: Path,
    m307_result_path: Path,
    predictions_path: Path,
) -> tuple[dict, dict, dict, dict]:
    m304 = read_json(m304_result_path)
    if not (
        m304.get("labelsWritten") is True
        and m304.get("formalAccuracyAllowed") is True
        and m304.get("semanticRobustnessAllowed") is True
        and int(m304.get("qcPassCount", -1)) == 12
        and int(m304.get("pendingCount", -1)) == 0
    ):
        raise ValueError("M304 12/12 human review is not ready")
    recorded_labels = resolve_workspace_path(workspace, str(m304.get("labels", "")), "M304 labels")
    if recorded_labels != labels_path:
        raise ValueError("M304 labels path identity mismatch")
    require_file_hash(labels_path, m304.get("labelsSha256"), "M304 labels")

    m307 = read_json(m307_result_path)
    if not (
        m307.get("status") == EXPECTED_M307_STATUS
        and m307.get("allFinite") is True
        and m307.get("filenameHintsRead") is False
        and m307.get("humanLabelsRead") is False
        and m307.get("heldOutLabelsRead") is False
        and int(m307.get("clipCount", -1)) == 12
        and int(m307.get("baselineCount", -1)) == 4
        and int(m307.get("completedPredictionRows", -1)) == 48
        and int(m307.get("modelForwardCount", -1)) == 96
    ):
        raise ValueError("M307 label-blind prediction gate is not exact and complete")
    recorded_predictions = resolve_workspace_path(
        workspace, str(m307.get("predictions", "")), "M307 predictions"
    )
    if recorded_predictions != predictions_path:
        raise ValueError("M307 predictions path identity mismatch")
    require_file_hash(predictions_path, m307.get("predictionsSha256"), "M307 predictions")

    return m304, read_json(labels_path), m307, read_json(predictions_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--m304-result", default="deployment/mage_vl4b/M304_HUMAN_REVIEW_IMPORT_RESULT.json"
    )
    parser.add_argument("--labels", default="data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json")
    parser.add_argument(
        "--m307-result",
        default="deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json",
    )
    parser.add_argument(
        "--predictions", default="data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json"
    )
    parser.add_argument(
        "--result", default="deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_RESULT.json"
    )
    parser.add_argument(
        "--seal", default="deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_SEAL.json"
    )
    parser.add_argument("--minimum-recall", type=float, default=0.9)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not (0.0 <= args.minimum_recall <= 1.0):
        raise ValueError("minimum recall must be in [0,1]")
    m304_result_path = resolve_workspace_path(workspace, args.m304_result, "M304 result")
    labels_path = resolve_workspace_path(workspace, args.labels, "labels")
    m307_result_path = resolve_workspace_path(workspace, args.m307_result, "M307 result")
    predictions_path = resolve_workspace_path(workspace, args.predictions, "predictions")
    result_path = resolve_workspace_path(workspace, args.result, "result")
    seal_path = resolve_workspace_path(workspace, args.seal, "seal")

    m304, labels, m307, predictions = verify_ready_inputs(
        workspace, m304_result_path, labels_path, m307_result_path, predictions_path
    )
    identity = build_identity(
        m304_result_path=m304_result_path,
        m304_result=m304,
        labels_path=labels_path,
        m307_result_path=m307_result_path,
        m307_result=m307,
        predictions_path=predictions_path,
        evaluator_path=Path(__file__).resolve(),
        minimum_recall=args.minimum_recall,
    )

    if seal_path.exists():
        seal = read_json(seal_path)
        if seal.get("identity") != identity:
            raise RuntimeError("M308 seal exists for different immutable inputs")
        if seal.get("status") != "COMPLETE" or not result_path.is_file():
            raise RuntimeError("M308 held-out test was opened but not atomically completed")
        if file_sha256(result_path) != seal.get("resultSha256"):
            raise RuntimeError("M308 sealed result hash mismatch")
        print(
            "M308_BACT_HELDOUT_EVALUATION_ALREADY_SEALED "
            f"result_sha256={seal['resultSha256']}"
        )
        return 0
    if result_path.exists():
        raise RuntimeError("M308 unsealed result exists; refusing to overwrite")

    opened_seal = {
        "date": "2026-09-03",
        "gate": "M308-one-shot-held-out-evaluation-seal",
        "status": "OPENED",
        "identity": identity,
        "testLabelsOpened": True,
        "result": str(result_path.relative_to(workspace)).replace("\\", "/"),
    }
    atomic_json(seal_path, opened_seal)

    metrics = evaluate_semantic_robustness(
        labels, predictions, minimum_recall=args.minimum_recall
    )
    result = {
        "date": "2026-09-03",
        "gate": "M308-one-shot-bact-held-out-evaluation",
        "status": "PASS_PILOT_HELDOUT_EVALUATION_SEALED",
        "classification": (
            "One-shot held-out pilot evaluation over 12 source-unique AI-generated clips. Knife thresholds "
            "were selected from calibration only; held-out knife/action and condition-slice metrics were "
            "opened once. This is pilot semantic evidence, not real-factory external validity or real-time proof."
        ),
        "identity": identity,
        "m304Result": str(m304_result_path.relative_to(workspace)).replace("\\", "/"),
        "labels": str(labels_path.relative_to(workspace)).replace("\\", "/"),
        "m307Result": str(m307_result_path.relative_to(workspace)).replace("\\", "/"),
        "predictions": str(predictions_path.relative_to(workspace)).replace("\\", "/"),
        "metrics": metrics,
        "calibrationOnlyThresholdSelection": True,
        "heldOutTestOpenedExactlyOnce": True,
        "filenameHintsUsedAsGroundTruth": False,
        "formalPilotAccuracyAllowed": True,
        "semanticRobustnessPilotAllowed": True,
        "realWorldExternalValidityClaimAllowed": False,
        "boardExecutionRun": False,
        "activeM254M256Changed": False,
        "bootDtbCmaPartitionsChanged": False,
        "stableRollbackPreserved": True,
    }
    atomic_json(result_path, result)
    completed_seal = dict(opened_seal)
    completed_seal["status"] = "COMPLETE"
    completed_seal["resultSha256"] = file_sha256(result_path)
    atomic_json(seal_path, completed_seal)
    print(
        "M308_BACT_HELDOUT_EVALUATION_PASS "
        f"baselines=4 result_sha256={completed_seal['resultSha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
