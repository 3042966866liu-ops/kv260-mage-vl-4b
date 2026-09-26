"""Semantic robustness analysis for the BACT four-baseline pilot.

This module extends the frozen calibration/held-out protocol in
``bact.evaluation``.  It never infers labels or conditions from filenames and
does not turn small condition slices into unsupported aggregate claims.
"""

from __future__ import annotations

import math

from .dataset import ACTIONS
from .evaluation import (
    BASELINE_IDS,
    _argmax_action,
    action_macro_f1,
    evaluate_four_baselines,
    freeze_knife_threshold,
    index_predictions,
    index_verified_labels,
    knife_metrics,
)


CONDITIONS = ("lowLight", "occlusion", "smallKnife")


def validate_conditions(labels_by_id: dict[str, dict]) -> None:
    """Require explicit human booleans for every robustness condition."""

    for clip_id, clip in labels_by_id.items():
        conditions = clip.get("conditions")
        if not isinstance(conditions, dict) or set(conditions) != set(CONDITIONS):
            raise ValueError(f"condition fields must be exact and complete: {clip_id}")
        for condition in CONDITIONS:
            if type(conditions[condition]) is not bool:
                raise ValueError(f"condition must be human-confirmed boolean: {clip_id}/{condition}")
        if conditions["smallKnife"] and not clip["knifePresent"]:
            raise ValueError(f"smallKnife=true requires knifePresent=true: {clip_id}")


def calibration_threshold_sensitivity(
    labels_by_id: dict[str, dict],
    predictions_by_id: dict[str, dict],
    *,
    minimum_recall: float,
) -> dict:
    """Run leave-one-calibration-clip-out threshold sensitivity.

    A fold that loses knife class support is reported unavailable instead of
    inventing a threshold.  Held-out test labels are never consulted.
    """

    calibration_ids = sorted(
        clip_id for clip_id, clip in labels_by_id.items() if clip["split"] == "calibration"
    )
    folds = []
    thresholds = []
    for excluded in calibration_ids:
        subset = {clip_id: clip for clip_id, clip in labels_by_id.items() if clip_id != excluded}
        try:
            freeze = freeze_knife_threshold(
                subset, predictions_by_id, minimum_recall=minimum_recall
            )
        except ValueError as error:
            folds.append(
                {
                    "excludedCalibrationClipId": excluded,
                    "status": "UNAVAILABLE",
                    "reason": str(error),
                    "testLabelsUsed": False,
                }
            )
            continue
        threshold = float(freeze["threshold"])
        if not math.isfinite(threshold):
            raise ValueError("non-finite leave-one-calibration-clip-out threshold")
        thresholds.append(threshold)
        folds.append(
            {
                "excludedCalibrationClipId": excluded,
                "status": "MEASURED",
                "threshold": threshold,
                "calibrationMetrics": freeze["calibrationMetrics"],
                "testLabelsUsed": False,
            }
        )
    return {
        "method": "leave-one-calibration-clip-out",
        "folds": folds,
        "measuredFoldCount": len(thresholds),
        "unavailableFoldCount": len(folds) - len(thresholds),
        "thresholdMinimum": min(thresholds) if thresholds else None,
        "thresholdMaximum": max(thresholds) if thresholds else None,
        "thresholdRange": max(thresholds) - min(thresholds) if thresholds else None,
        "testLabelsUsed": False,
    }


def _slice_metrics(
    clip_ids: list[str],
    labels_by_id: dict[str, dict],
    predictions_by_id: dict[str, dict],
    threshold: float,
) -> dict:
    action_pairs = []
    knife_rows = []
    correct_action = 0
    correct_knife = 0
    action_support = {action: 0 for action in ACTIONS}
    knife_positive = 0
    knife_negative = 0
    for clip_id in clip_ids:
        clip = labels_by_id[clip_id]
        prediction = predictions_by_id[clip_id]
        truth_action = str(clip["action"])
        predicted_action = _argmax_action(prediction["actionLogits"])
        truth_knife = bool(clip["knifePresent"])
        predicted_knife = float(prediction["knifeScore"]) >= threshold
        action_pairs.append((truth_action, predicted_action))
        knife_rows.append((truth_knife, float(prediction["knifeScore"])))
        action_support[truth_action] += 1
        knife_positive += int(truth_knife)
        knife_negative += int(not truth_knife)
        correct_action += int(truth_action == predicted_action)
        correct_knife += int(truth_knife == predicted_knife)

    result = {
        "clipIds": clip_ids,
        "clipCount": len(clip_ids),
        "knifePositiveSupport": knife_positive,
        "knifeNegativeSupport": knife_negative,
        "actionSupport": action_support,
        "knifeAccuracy": correct_knife / len(clip_ids) if clip_ids else None,
        "actionAccuracy": correct_action / len(clip_ids) if clip_ids else None,
        "knifeRecallAndFalseAlarmAvailable": knife_positive > 0 and knife_negative > 0,
        "fiveClassMacroF1Available": all(action_support[action] > 0 for action in ACTIONS),
    }
    if result["knifeRecallAndFalseAlarmAvailable"]:
        result["knife"] = knife_metrics(knife_rows, threshold).__dict__
    else:
        result["knife"] = None
    if result["fiveClassMacroF1Available"]:
        result["actionMacroF1"] = action_macro_f1(action_pairs)
    else:
        result["actionMacroF1"] = None
    return result


def held_out_condition_slices(
    labels_by_id: dict[str, dict],
    predictions_by_id: dict[str, dict],
    threshold: float,
) -> dict:
    """Return descriptive held-out metrics for each condition and complement."""

    test_ids = sorted(
        clip_id for clip_id, clip in labels_by_id.items() if clip["split"] == "test"
    )
    output = {}
    for condition in CONDITIONS:
        positive = [
            clip_id for clip_id in test_ids if labels_by_id[clip_id]["conditions"][condition]
        ]
        negative = [
            clip_id for clip_id in test_ids if not labels_by_id[clip_id]["conditions"][condition]
        ]
        if not positive or not negative:
            raise ValueError(f"held-out condition requires positive and negative slices: {condition}")
        output[condition] = {
            "present": _slice_metrics(
                positive, labels_by_id, predictions_by_id, threshold
            ),
            "absent": _slice_metrics(
                negative, labels_by_id, predictions_by_id, threshold
            ),
        }
    return output


def evaluate_semantic_robustness(
    labels: dict,
    predictions: dict,
    *,
    minimum_recall: float = 0.9,
) -> dict:
    """Evaluate four baselines plus calibration and condition sensitivity."""

    labels_by_id = index_verified_labels(labels)
    validate_conditions(labels_by_id)
    predictions_by_baseline = index_predictions(predictions, labels_by_id)
    primary = evaluate_four_baselines(
        labels, predictions, minimum_recall=minimum_recall
    )
    output = {}
    for baseline, candidate_id in BASELINE_IDS.items():
        threshold = float(primary[baseline]["thresholdFreeze"]["threshold"])
        output[baseline] = {
            "candidateId": candidate_id,
            "primary": primary[baseline],
            "calibrationThresholdSensitivity": calibration_threshold_sensitivity(
                labels_by_id,
                predictions_by_baseline[baseline],
                minimum_recall=minimum_recall,
            ),
            "heldOutConditionSlices": held_out_condition_slices(
                labels_by_id, predictions_by_baseline[baseline], threshold
            ),
        }
    return {
        "baselineOrder": list(BASELINE_IDS),
        "minimumRecallConstraint": minimum_recall,
        "conditions": list(CONDITIONS),
        "baselines": output,
        "filenameHintsUsedAsGroundTruth": False,
        "testLabelsUsedForThresholdSelection": False,
    }
