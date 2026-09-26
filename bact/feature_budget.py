"""Offline feature-driven token subset proposals; NOT semantic acceptance.

Runs after vision encoding, hence does not save vision-tower computation.
All indices refer to the original sequence; no model/position/mask is changed.
The feature-distance threshold is an explicit experiment input, not accuracy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FeatureProposal:
    indices: tuple[int, ...]
    visual_tokens: int
    total_tokens: int
    batches: int
    legacy_logical_calls: int
    mean_feature_distance: float
    p95_feature_distance: float
    per_view_counts: tuple[tuple[int, int], ...]


def _inputs(features: np.ndarray, view_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(features)
    ids = np.asarray(view_ids)
    if x.ndim != 2 or not x.shape[0] or not x.shape[1] or x.dtype.kind != "f":
        raise ValueError("features must be a nonempty floating [tokens, channels] array")
    if not np.isfinite(x).all():
        raise ValueError("nonfinite features")
    if ids.shape != (len(x),) or ids.dtype.kind not in "iu" or (ids < 0).any():
        raise ValueError("view_ids must be nonnegative integer IDs aligned to features")
    # FP64 avoids overflow for finite but large FP32 values.
    x = x.astype(np.float64)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms == 0).any():
        raise ValueError("zero/overflow feature norm cannot define cosine coverage")
    return x / norms, ids


def propose_budgets(features: np.ndarray, view_ids: np.ndarray,
                    visual_budgets: list[int], text_tokens: int) -> list[FeatureProposal]:
    """Deterministic farthest-first selection, with >=1 token per view.

    Coverage compares tokens ONLY within their original view. We preserve
    original sequence order in returned indices, and preserve ALL text tokens.
    Similarity is computed in vectors, never a full token-by-token matrix.
    Caller must supply validated view/position metadata; this is not a drop-in
    patch-merger or language-runtime replacement.
    """
    x, ids = _inputs(features, view_ids)
    if type(text_tokens) is not int or text_tokens < 0:
        raise ValueError("text_tokens must be a nonnegative integer")
    views = np.unique(ids)
    if not visual_budgets or any(type(k) is not int or not len(views) <= k <= len(x)
                                 for k in visual_budgets):
        raise ValueError("budgets must fit tokens and preserve every view")
    if len(set(visual_budgets)) != len(visual_budgets):
        raise ValueError("duplicate budgets")
    distance = np.full(len(x), np.inf)
    selected = np.zeros(len(x), dtype=bool)

    def add(index: int) -> None:
        same = np.flatnonzero(ids == ids[index])
        d = np.clip(1.0 - x[same] @ x[index], 0.0, 2.0) / 2.0
        distance[same] = np.minimum(distance[same], d)
        distance[index] = 0.0
        selected[index] = True

    # Deterministic centroid-nearest seed for each view; tie -> original index.
    for view in views:
        group = np.flatnonzero(ids == view)
        center = x[group].mean(axis=0)
        add(int(group[np.argmax(x[group] @ center)]))
    records = {}
    for k in range(len(views), max(visual_budgets) + 1):
        if k > len(views):
            add(int(np.argmax(np.where(selected, -1.0, distance))))
        if k in visual_budgets:
            indices = tuple(int(i) for i in np.flatnonzero(selected))
            n = k + text_tokens
            b = (n + 31) // 32
            records[k] = FeatureProposal(
                indices, k, n, b, 154 * b + 8,
                float(distance.mean()), float(np.quantile(distance, 0.95)),
                tuple((int(v), int(np.count_nonzero(ids[selected] == v))) for v in views),
            )
    return [records[k] for k in visual_budgets]


def choose_proposal(proposals: list[FeatureProposal], maximum_feature_distance: float) -> FeatureProposal:
    """Logical-cost experiment only; explicitly NOT a calibrated quality gate."""
    if not math.isfinite(maximum_feature_distance) or not 0 <= maximum_feature_distance <= 1:
        raise ValueError("explicit finite feature threshold in [0,1] required")
    feasible = [p for p in proposals if p.mean_feature_distance <= maximum_feature_distance]
    if not feasible:
        raise ValueError("no feasible feature proposal")
    return min(feasible, key=lambda p: (p.batches, p.mean_feature_distance, -p.total_tokens, p.indices))


def measure_subset(features: np.ndarray, view_ids: np.ndarray, indices: list[int]) -> dict:
    """Independent same-view cosine coverage of a proposed original-index subset."""
    x, ids = _inputs(features, view_ids)
    if not indices or len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < len(x) for i in indices):
        raise ValueError("invalid subset indices")
    if set(ids[indices]) != set(ids):
        raise ValueError("subset dropped an entire view")
    nearest = np.full(len(x), np.inf)
    for index in indices:
        same = np.flatnonzero(ids == ids[index])
        nearest[same] = np.minimum(nearest[same], np.clip(1 - x[same] @ x[index], 0, 2) / 2)
        nearest[index] = 0
    return {"mean_feature_distance": float(nearest.mean()),
            "p95_feature_distance": float(np.quantile(nearest, .95))}
