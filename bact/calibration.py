"""Leakage-resistant binary threshold calibration for BACT baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class ThresholdSelection:
    threshold: float
    tp: int
    fn: int
    fp: int
    tn: int
    recall: float | None
    false_alarm_rate: float | None
    precision: float | None
    accuracy: float
    minimum_score_clearance: float
    feasible: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _evaluate(scores: list[float], labels: list[int], threshold: float) -> ThresholdSelection:
    decisions = [1 if score >= threshold else 0 for score in scores]
    tp = sum(label == 1 and decision == 1 for label, decision in zip(labels, decisions))
    fn = sum(label == 1 and decision == 0 for label, decision in zip(labels, decisions))
    fp = sum(label == 0 and decision == 1 for label, decision in zip(labels, decisions))
    tn = sum(label == 0 and decision == 0 for label, decision in zip(labels, decisions))
    recall = _ratio(tp, tp + fn)
    far = _ratio(fp, fp + tn)
    precision = _ratio(tp, tp + fp)
    return ThresholdSelection(
        threshold=threshold,
        tp=tp, fn=fn, fp=fp, tn=tn,
        recall=recall,
        false_alarm_rate=far,
        precision=precision,
        accuracy=(tp + tn) / len(labels),
        minimum_score_clearance=min(abs(score - threshold) for score in scores),
        feasible=False,
    )


def calibrate_binary_threshold(
    records: Iterable[dict],
    *,
    split: str,
    minimum_recall: float,
    maximum_false_alarm_rate: float,
) -> ThresholdSelection:
    """Freeze one threshold from calibration records only.

    Selection is lexicographic: satisfy both constraints, maximize recall,
    minimize false alarms, maximize accuracy and score clearance.  No test
    labels may be supplied to this function.
    """

    if split != "calibration":
        raise ValueError("threshold selection is restricted to the calibration split")
    if not 0.0 <= minimum_recall <= 1.0 or not 0.0 <= maximum_false_alarm_rate <= 1.0:
        raise ValueError("quality constraints must be in [0, 1]")
    values = list(records)
    if not values:
        raise ValueError("calibration records are empty")
    scores = [float(item["score"]) for item in values]
    labels = [int(item["label"]) for item in values]
    if any(not math.isfinite(score) for score in scores):
        raise ValueError("calibration scores must be finite")
    if any(label not in (0, 1) for label in labels):
        raise ValueError("calibration labels must be binary")
    if 0 not in labels or 1 not in labels:
        raise ValueError("calibration requires both negative and positive labels")

    unique = sorted(set(scores))
    span = max(1.0, unique[-1] - unique[0])
    thresholds = [unique[0] - span]
    thresholds.extend((left + right) / 2.0 for left, right in zip(unique, unique[1:]))
    thresholds.append(unique[-1] + span)
    measured = [_evaluate(scores, labels, threshold) for threshold in thresholds]
    feasible = [
        item for item in measured
        if item.recall is not None and item.recall >= minimum_recall
        and item.false_alarm_rate is not None
        and item.false_alarm_rate <= maximum_false_alarm_rate
    ]
    if not feasible:
        raise ValueError("no threshold satisfies the frozen recall/false-alarm constraints")
    selected = min(
        feasible,
        key=lambda item: (
            -float(item.recall),
            float(item.false_alarm_rate),
            -item.accuracy,
            -item.minimum_score_clearance,
            item.threshold,
        ),
    )
    return ThresholdSelection(**{**asdict(selected), "feasible": True})
