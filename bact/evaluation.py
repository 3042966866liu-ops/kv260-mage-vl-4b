"""Fail-closed calibration and held-out metrics for the BACT pilot.

The evaluation unit is one human-verified constant-action/constant-knife clip
or a sampled window inheriting that clip label. Bounding-box metrics are not
computed by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

from .dataset import ACTIONS


BASELINE_IDS = {
    "fixed_high_quality": "high-284",
    "fixed_ratio_visual_pruning": "ratio-164",
    "token_count_aware": "count-144",
    "bact": "bact-159",
}


@dataclass(frozen=True)
class KnifeMetrics:
    true_positive: int
    false_negative: int
    false_positive: int
    true_negative: int
    recall: float
    false_alarm_rate: float


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_score(value: object, field: str) -> float:
    score = float(value)
    if not math.isfinite(score):
        raise ValueError(f"{field} must be finite")
    return score


def index_verified_labels(labels: dict) -> dict[str, dict]:
    if labels.get("schema") != "tellme-bact-clip-constant-v1":
        raise ValueError("unsupported label schema")
    clips = labels.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("labels must contain clips")
    indexed: dict[str, dict] = {}
    for clip in clips:
        clip_id = str(clip["clipId"])
        if clip_id in indexed:
            raise ValueError(f"duplicate clipId: {clip_id}")
        if clip.get("annotationStatus") != "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT":
            raise ValueError(f"clip is not human verified: {clip_id}")
        if clip.get("action") not in ACTIONS:
            raise ValueError(f"unsupported action: {clip_id}")
        if type(clip.get("knifePresent")) is not bool:  # bool, not truthy integer/string
            raise ValueError(f"knifePresent must be boolean: {clip_id}")
        if clip.get("actionConstant") is not True or clip.get("knifeConstant") is not True:
            raise ValueError(f"clip labels are not constant: {clip_id}")
        if clip.get("watchedComplete") is not True or not str(clip.get("annotator", "")).strip():
            raise ValueError(f"human review is incomplete: {clip_id}")
        if clip.get("split") not in {"calibration", "test"}:
            raise ValueError(f"unsupported split: {clip_id}")
        indexed[clip_id] = clip
    return indexed


def index_predictions(predictions: dict, labels_by_id: dict[str, dict]) -> dict[str, dict[str, dict]]:
    if predictions.get("schema") != "tellme-bact-four-baseline-predictions-v1":
        raise ValueError("unsupported prediction schema")
    baselines = predictions.get("baselines")
    if not isinstance(baselines, dict) or set(baselines) != set(BASELINE_IDS):
        raise ValueError("prediction file must contain exactly four frozen baselines")
    result: dict[str, dict[str, dict]] = {}
    for name, expected_id in BASELINE_IDS.items():
        baseline = baselines[name]
        if baseline.get("candidateId") != expected_id:
            raise ValueError(f"candidate identity mismatch: {name}")
        rows = baseline.get("predictions")
        if not isinstance(rows, list) or len(rows) != len(labels_by_id):
            raise ValueError(f"prediction count mismatch: {name}")
        indexed: dict[str, dict] = {}
        for row in rows:
            clip_id = str(row["clipId"])
            if clip_id in indexed or clip_id not in labels_by_id:
                raise ValueError(f"prediction clip identity failure: {name}/{clip_id}")
            score = _finite_score(row["knifeScore"], f"knifeScore:{name}/{clip_id}")
            logits = row.get("actionLogits")
            if not isinstance(logits, dict) or set(logits) != set(ACTIONS):
                raise ValueError(f"action logits must cover five actions: {name}/{clip_id}")
            clean_logits = {action: _finite_score(logits[action], f"actionLogit:{name}/{clip_id}/{action}") for action in ACTIONS}
            indexed[clip_id] = {"knifeScore": score, "actionLogits": clean_logits}
        if set(indexed) != set(labels_by_id):
            raise ValueError(f"prediction label coverage mismatch: {name}")
        result[name] = indexed
    return result


def knife_metrics(rows: Iterable[tuple[bool, float]], threshold: float) -> KnifeMetrics:
    tp = fn = fp = tn = 0
    for truth, score in rows:
        predicted = score >= threshold
        if truth and predicted:
            tp += 1
        elif truth:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    if tp + fn == 0 or fp + tn == 0:
        raise ValueError("knife metrics require positive and negative ground truth")
    return KnifeMetrics(tp, fn, fp, tn, tp / (tp + fn), fp / (fp + tn))


def threshold_candidates(scores: Iterable[float]) -> list[float]:
    unique = sorted(set(float(score) for score in scores))
    if not unique:
        raise ValueError("no calibration scores")
    scale = max(1.0, max(abs(value) for value in unique))
    epsilon = math.ulp(scale) * 8.0
    candidates = [unique[0] - epsilon]
    candidates.extend((left + right) / 2.0 for left, right in zip(unique, unique[1:]))
    candidates.append(unique[-1] + epsilon)
    return candidates


def freeze_knife_threshold(
    labels_by_id: dict[str, dict],
    predictions_by_id: dict[str, dict],
    *,
    minimum_recall: float = 0.9,
) -> dict:
    if not (0.0 <= minimum_recall <= 1.0):
        raise ValueError("minimum_recall must be in [0,1]")
    calibration_ids = sorted(clip_id for clip_id, clip in labels_by_id.items() if clip["split"] == "calibration")
    rows = [(bool(labels_by_id[clip_id]["knifePresent"]), predictions_by_id[clip_id]["knifeScore"]) for clip_id in calibration_ids]
    feasible = []
    for threshold in threshold_candidates(score for _, score in rows):
        metrics = knife_metrics(rows, threshold)
        if metrics.recall >= minimum_recall:
            feasible.append((metrics.false_alarm_rate, -threshold, -metrics.recall, threshold, metrics))
    if not feasible:
        raise ValueError("no calibration threshold satisfies minimum recall")
    _, _, _, threshold, metrics = min(feasible)
    return {
        "threshold": threshold,
        "minimumRecallConstraint": minimum_recall,
        "calibrationClipIds": calibration_ids,
        "calibrationMetrics": metrics.__dict__,
        "selectionKey": [metrics.false_alarm_rate, -threshold, -metrics.recall],
        "testLabelsUsed": False,
    }


def _argmax_action(logits: dict[str, float]) -> str:
    # Frozen ACTIONS order provides deterministic tie breaking.
    return max(ACTIONS, key=lambda action: (logits[action], -ACTIONS.index(action)))


def action_macro_f1(rows: Iterable[tuple[str, str]]) -> dict:
    pairs = list(rows)
    per_class = {}
    for action in ACTIONS:
        tp = sum(truth == action and predicted == action for truth, predicted in pairs)
        fp = sum(truth != action and predicted == action for truth, predicted in pairs)
        fn = sum(truth == action and predicted != action for truth, predicted in pairs)
        support = sum(truth == action for truth, _ in pairs)
        if support == 0:
            raise ValueError(f"held-out test lacks action support: {action}")
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[action] = {"tp": tp, "fp": fp, "fn": fn, "support": support, "precision": precision, "recall": recall, "f1": f1}
    return {"macroF1": sum(value["f1"] for value in per_class.values()) / len(ACTIONS), "perClass": per_class}


def evaluate_held_out(
    labels_by_id: dict[str, dict],
    predictions_by_id: dict[str, dict],
    threshold_freeze: dict,
) -> dict:
    if threshold_freeze.get("testLabelsUsed") is not False:
        raise ValueError("threshold freeze is not calibration-only")
    test_ids = sorted(clip_id for clip_id, clip in labels_by_id.items() if clip["split"] == "test")
    knife_rows = [(bool(labels_by_id[clip_id]["knifePresent"]), predictions_by_id[clip_id]["knifeScore"]) for clip_id in test_ids]
    knife = knife_metrics(knife_rows, float(threshold_freeze["threshold"]))
    action_rows = [
        (str(labels_by_id[clip_id]["action"]), _argmax_action(predictions_by_id[clip_id]["actionLogits"]))
        for clip_id in test_ids
    ]
    action = action_macro_f1(action_rows)
    return {
        "testClipIds": test_ids,
        "knife": knife.__dict__,
        "action": action,
        "threshold": float(threshold_freeze["threshold"]),
    }


def evaluate_four_baselines(labels: dict, predictions: dict, *, minimum_recall: float = 0.9) -> dict:
    labels_by_id = index_verified_labels(labels)
    predictions_by_baseline = index_predictions(predictions, labels_by_id)
    output = {}
    for baseline in BASELINE_IDS:
        freeze = freeze_knife_threshold(labels_by_id, predictions_by_baseline[baseline], minimum_recall=minimum_recall)
        output[baseline] = {
            "candidateId": BASELINE_IDS[baseline],
            "thresholdFreeze": freeze,
            "heldOutTest": evaluate_held_out(labels_by_id, predictions_by_baseline[baseline], freeze),
        }
    return output


def canonical_sha256(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
