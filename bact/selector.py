"""Reproducible BACT cost model and four-baseline selector.

The module deliberately separates exact hardware geometry from empirical
latency.  ``logical_calls`` is an identity for the current M238/M241 runtime;
it is never presented as total latency or power.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AcceleratorCostModel:
    token_granularity: int = 32
    language_families_per_batch: int = 154
    fixed_calls: int = 8
    alpha_ms_per_batch: float | None = None
    beta_ms: float | None = None
    gamma_ms_per_token: float | None = None

    def __post_init__(self) -> None:
        if self.token_granularity <= 0:
            raise ValueError("token_granularity must be positive")
        if self.language_families_per_batch <= 0 or self.fixed_calls < 0:
            raise ValueError("call coefficients are invalid")

    def batches(self, total_tokens: int) -> int:
        if total_tokens <= 0:
            raise ValueError("total_tokens must be positive")
        return math.ceil(total_tokens / self.token_granularity)

    def logical_calls(self, total_tokens: int) -> int:
        return self.language_families_per_batch * self.batches(total_tokens) + self.fixed_calls

    def estimated_language_ms(self, total_tokens: int) -> float | None:
        coefficients = (self.alpha_ms_per_batch, self.beta_ms, self.gamma_ms_per_token)
        if any(value is None for value in coefficients):
            return None
        return (
            float(self.alpha_ms_per_batch) * self.batches(total_tokens)
            + float(self.beta_ms)
            + float(self.gamma_ms_per_token) * total_tokens
        )


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    visual_tokens: int
    text_tokens: int
    semantic_loss: float
    knife_recall: float
    knife_false_alarm_rate: float
    action_macro_f1: float
    memory_bytes: int
    view_count: int
    pruning_ratio: float

    def __post_init__(self) -> None:
        if self.visual_tokens < 0 or self.text_tokens < 0:
            raise ValueError("token counts must be non-negative")
        if self.total_tokens <= 0:
            raise ValueError("candidate must contain at least one token")
        if self.semantic_loss < 0.0 or self.memory_bytes < 0:
            raise ValueError("semantic_loss and memory_bytes must be non-negative")
        for name in ("knife_recall", "knife_false_alarm_rate", "action_macro_f1", "pruning_ratio"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")

    @property
    def total_tokens(self) -> int:
        return self.visual_tokens + self.text_tokens


@dataclass(frozen=True)
class QualityConstraint:
    minimum_knife_recall: float
    maximum_knife_false_alarm_rate: float
    minimum_action_macro_f1: float
    maximum_memory_bytes: int

    def accepts(self, candidate: Candidate) -> bool:
        return (
            candidate.knife_recall >= self.minimum_knife_recall
            and candidate.knife_false_alarm_rate <= self.maximum_knife_false_alarm_rate
            and candidate.action_macro_f1 >= self.minimum_action_macro_f1
            and candidate.memory_bytes <= self.maximum_memory_bytes
        )


@dataclass(frozen=True)
class Selection:
    baseline: str
    candidate: Candidate
    batches: int
    logical_calls: int
    selection_key: tuple
    reason: str

    def to_dict(self) -> dict:
        result = asdict(self)
        result["candidate"]["total_tokens"] = self.candidate.total_tokens
        result["selection_key"] = list(self.selection_key)
        return result


def _eligible(candidates: Iterable[Candidate], constraint: QualityConstraint) -> list[Candidate]:
    values = [candidate for candidate in candidates if constraint.accepts(candidate)]
    if not values:
        raise ValueError("no candidate satisfies the frozen quality/resource constraint")
    ids = [candidate.candidate_id for candidate in values]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique")
    return values


def _selection(name: str, candidate: Candidate, model: AcceleratorCostModel, key: tuple, reason: str) -> Selection:
    return Selection(
        baseline=name,
        candidate=candidate,
        batches=model.batches(candidate.total_tokens),
        logical_calls=model.logical_calls(candidate.total_tokens),
        selection_key=key,
        reason=reason,
    )


def select_four_baselines(
    candidates: Iterable[Candidate],
    constraint: QualityConstraint,
    model: AcceleratorCostModel,
    *,
    fixed_high_quality_id: str,
    fixed_ratio_candidate_id: str,
    fixed_pruning_ratio: float,
) -> Mapping[str, Selection]:
    """Select four frozen baselines without using test-set measurements.

    Thresholds, semantic losses and quality metrics must be frozen from train or
    calibration data before this function is used for a held-out test run.
    """

    all_candidates = list(candidates)
    eligible = _eligible(all_candidates, constraint)
    by_id = {candidate.candidate_id: candidate for candidate in all_candidates}
    if fixed_high_quality_id not in by_id:
        raise ValueError("fixed_high_quality_id is absent")
    if fixed_ratio_candidate_id not in by_id:
        raise ValueError("fixed_ratio_candidate_id is absent")
    high = by_id[fixed_high_quality_id]
    fixed_ratio = by_id[fixed_ratio_candidate_id]
    if not constraint.accepts(high):
        raise ValueError("the frozen high-quality baseline fails the quality/resource constraint")
    if not constraint.accepts(fixed_ratio):
        raise ValueError("the frozen fixed-ratio baseline fails the quality/resource constraint")
    if not 0.0 <= fixed_pruning_ratio <= 1.0:
        raise ValueError("fixed_pruning_ratio must be in [0, 1]")
    if not math.isclose(fixed_ratio.pruning_ratio, fixed_pruning_ratio, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("fixed-ratio candidate does not match the frozen pruning ratio")

    count_key = lambda item: (
        item.total_tokens,
        item.semantic_loss,
        item.memory_bytes,
        item.candidate_id,
    )
    token_count = min(eligible, key=count_key)

    # BACT: eliminate complete hardware batches first; inside one cost plateau,
    # minimize semantic loss, then retain more cross-modal information.
    bact_key = lambda item: (
        model.batches(item.total_tokens),
        item.semantic_loss,
        -item.total_tokens,
        item.memory_bytes,
        item.candidate_id,
    )
    bact = min(eligible, key=bact_key)

    return {
        "fixed_high_quality": _selection(
            "fixed_high_quality",
            high,
            model,
            (fixed_high_quality_id,),
            "Frozen unpruned/high-information reference; no test-time search.",
        ),
        "fixed_ratio_visual_pruning": _selection(
            "fixed_ratio_visual_pruning",
            fixed_ratio,
            model,
            (fixed_ratio_candidate_id, fixed_pruning_ratio),
            "Exact candidate and visual-pruning ratio frozen before evaluation; no boundary-aware reselection.",
        ),
        "token_count_aware": _selection(
            "token_count_aware",
            token_count,
            model,
            count_key(token_count),
            "Minimum total cross-modal token count; hardware batch boundaries are not in the key.",
        ),
        "bact": _selection(
            "bact",
            bact,
            model,
            bact_key(bact),
            "Minimum fixed-granularity batch count, then minimum semantic loss and maximum retained information.",
        ),
    }


def boundary_efficiency(call_reduction: int, semantic_loss_increase: float, epsilon: float = 1e-12) -> float:
    if call_reduction < 0 or semantic_loss_increase < 0.0 or epsilon <= 0.0:
        raise ValueError("boundary-efficiency inputs are invalid")
    return call_reduction / (semantic_loss_increase + epsilon)
