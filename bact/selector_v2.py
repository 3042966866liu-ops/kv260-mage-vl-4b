"""BACT-V2 label-blind discrete cross-modal budget selector.

The selector consumes only frozen deployment geometry and calibration/inference-
time semantic-loss proxies.  It deliberately has no accuracy or held-out-test
input.  Exact T32 logical calls are a hardware identity, not a latency model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable, Mapping, Sequence


ALLOWED_FAMILIES = frozenset(
    {"visual_only", "visual_plus_prompt", "view_visual_prompt_joint"}
)
FORBIDDEN_INPUT_TERMS = (
    "label",
    "ground_truth",
    "heldout",
    "held_out",
    "test_metric",
    "test_accuracy",
    "filename_hint",
)


def _reject_forbidden_fields(value: Any, path: str = "root") -> None:
    """Fail closed if runtime input contains outcome or filename-hint fields."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            if any(term in key for term in FORBIDDEN_INPUT_TERMS):
                raise ValueError(f"forbidden selector input field at {path}.{raw_key}")
            _reject_forbidden_fields(child, f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


@dataclass(frozen=True)
class T32CostIdentity:
    token_granularity: int = 32
    language_calls_per_batch: int = 154
    fixed_calls: int = 8

    def __post_init__(self) -> None:
        if self.token_granularity <= 0 or self.language_calls_per_batch <= 0:
            raise ValueError("T32 cost coefficients must be positive")
        if self.fixed_calls < 0:
            raise ValueError("fixed_calls must be non-negative")

    def batches(self, total_tokens: int) -> int:
        if total_tokens <= 0:
            raise ValueError("total_tokens must be positive")
        return math.ceil(total_tokens / self.token_granularity)

    def logical_calls(self, total_tokens: int) -> int:
        return self.language_calls_per_batch * self.batches(total_tokens) + self.fixed_calls


@dataclass(frozen=True)
class ProxyWeights:
    visual_importance: float
    view_coverage: float
    prompt_deletion: float

    def __post_init__(self) -> None:
        values = (self.visual_importance, self.view_coverage, self.prompt_deletion)
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValueError("proxy weights must be finite and non-negative")
        if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("proxy weights must sum to one")


@dataclass(frozen=True)
class ProxyComponents:
    visual_importance_loss: float
    view_coverage_loss: float
    prompt_deletion_cost: float

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("proxy components must be finite values in [0, 1]")

    def weighted_loss(self, weights: ProxyWeights) -> float:
        return (
            weights.visual_importance * self.visual_importance_loss
            + weights.view_coverage * self.view_coverage_loss
            + weights.prompt_deletion * self.prompt_deletion_cost
        )


@dataclass(frozen=True)
class BACTCandidateV2:
    candidate_id: str
    adjustment_family: str
    view_indices: tuple[int, ...]
    visual_tokens_per_view: tuple[int, ...]
    prompt_id: str
    text_tokens: int
    proxy: ProxyComponents
    target_band: str

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.prompt_id:
            raise ValueError("candidate_id and prompt_id must be non-empty")
        if self.adjustment_family not in ALLOWED_FAMILIES:
            raise ValueError(f"unsupported adjustment family: {self.adjustment_family}")
        if not self.view_indices or len(self.view_indices) != len(self.visual_tokens_per_view):
            raise ValueError("view indices and per-view visual budgets must be non-empty and aligned")
        if len(set(self.view_indices)) != len(self.view_indices):
            raise ValueError("view indices must be unique")
        if any(index < 0 for index in self.view_indices):
            raise ValueError("view indices must be non-negative")
        if any(tokens <= 0 for tokens in self.visual_tokens_per_view):
            raise ValueError("per-view visual-token budgets must be positive")
        if self.text_tokens < 0 or self.total_tokens <= 0:
            raise ValueError("text/total token count is invalid")
        if self.target_band not in {"B4", "B5", "B6"}:
            raise ValueError("target_band must be B4, B5 or B6")

    @property
    def visual_tokens(self) -> int:
        return sum(self.visual_tokens_per_view)

    @property
    def total_tokens(self) -> int:
        return self.visual_tokens + self.text_tokens


@dataclass(frozen=True)
class BACTSelectionV2:
    candidate: BACTCandidateV2
    semantic_loss_proxy: float
    batches: int
    logical_calls: int
    selection_key: tuple[float | int, ...]
    selection_reason: str

    def to_dict(self) -> dict[str, Any]:
        candidate = asdict(self.candidate)
        candidate["view_indices"] = list(self.candidate.view_indices)
        candidate["visual_tokens_per_view"] = list(self.candidate.visual_tokens_per_view)
        candidate["visual_tokens"] = self.candidate.visual_tokens
        candidate["total_tokens"] = self.candidate.total_tokens
        return {
            "candidate": candidate,
            "semantic_loss_proxy": self.semantic_loss_proxy,
            "batches": self.batches,
            "logical_calls": self.logical_calls,
            "selection_key": list(self.selection_key),
            "selection_reason": self.selection_reason,
        }


def candidate_from_mapping(raw: Mapping[str, Any]) -> BACTCandidateV2:
    """Construct one candidate from a strict, outcome-free runtime record."""

    _reject_forbidden_fields(raw)
    allowed = {
        "candidate_id",
        "adjustment_family",
        "view_indices",
        "visual_tokens_per_view",
        "prompt_id",
        "text_tokens",
        "proxy",
        "target_band",
    }
    unknown = set(raw) - allowed
    missing = allowed - set(raw)
    if unknown or missing:
        raise ValueError(f"candidate schema mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}")
    proxy_raw = raw["proxy"]
    if not isinstance(proxy_raw, Mapping):
        raise ValueError("proxy must be an object")
    proxy_allowed = {"visual_importance_loss", "view_coverage_loss", "prompt_deletion_cost"}
    if set(proxy_raw) != proxy_allowed:
        raise ValueError("proxy component schema mismatch")
    return BACTCandidateV2(
        candidate_id=str(raw["candidate_id"]),
        adjustment_family=str(raw["adjustment_family"]),
        view_indices=tuple(int(value) for value in raw["view_indices"]),
        visual_tokens_per_view=tuple(int(value) for value in raw["visual_tokens_per_view"]),
        prompt_id=str(raw["prompt_id"]),
        text_tokens=int(raw["text_tokens"]),
        proxy=ProxyComponents(**{key: float(proxy_raw[key]) for key in proxy_allowed}),
        target_band=str(raw["target_band"]),
    )


def validate_candidate_space(
    candidates: Sequence[BACTCandidateV2], band_ranges: Mapping[str, Sequence[int]]
) -> None:
    if not candidates:
        raise ValueError("candidate space must not be empty")
    identifiers = [candidate.candidate_id for candidate in candidates]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("candidate_id values must be unique")
    for band in ("B4", "B5", "B6"):
        bounds = tuple(int(value) for value in band_ranges[band])
        if len(bounds) != 2 or bounds[0] > bounds[1]:
            raise ValueError(f"invalid bounds for {band}")
        members = [candidate for candidate in candidates if candidate.target_band == band]
        families = {candidate.adjustment_family for candidate in members}
        if families != ALLOWED_FAMILIES:
            raise ValueError(f"{band} must contain exactly the three required adjustment families")
        for candidate in members:
            if not bounds[0] <= candidate.total_tokens <= bounds[1]:
                raise ValueError(f"{candidate.candidate_id} falls outside {band}")


def select_bact_v2(
    candidates: Iterable[BACTCandidateV2],
    proxy_weights: ProxyWeights,
    maximum_semantic_loss_proxy: float,
    cost: T32CostIdentity = T32CostIdentity(),
) -> BACTSelectionV2:
    """Select lexicographically by (batches, D, -N) under D <= delta."""

    if not math.isfinite(maximum_semantic_loss_proxy) or maximum_semantic_loss_proxy < 0.0:
        raise ValueError("maximum_semantic_loss_proxy must be finite and non-negative")
    values = list(candidates)
    if not values:
        raise ValueError("candidate space must not be empty")
    ids = [candidate.candidate_id for candidate in values]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique")

    scored = [
        (candidate, candidate.proxy.weighted_loss(proxy_weights))
        for candidate in values
    ]
    feasible = [(candidate, loss) for candidate, loss in scored if loss <= maximum_semantic_loss_proxy]
    if not feasible:
        raise ValueError("no candidate satisfies the frozen semantic-loss proxy limit")
    candidate, loss = min(
        feasible,
        key=lambda item: (
            cost.batches(item[0].total_tokens),
            item[1],
            -item[0].total_tokens,
            item[0].candidate_id,
        ),
    )
    key = (cost.batches(candidate.total_tokens), loss, -candidate.total_tokens)
    return BACTSelectionV2(
        candidate=candidate,
        semantic_loss_proxy=loss,
        batches=cost.batches(candidate.total_tokens),
        logical_calls=cost.logical_calls(candidate.total_tokens),
        selection_key=key,
        selection_reason=(
            "Feasible under the frozen calibration/inference-time proxy limit; selected by "
            "lexicographic (T32 batches, semantic-loss proxy, negative retained tokens)."
        ),
    )


def audit_all_candidates(
    candidates: Iterable[BACTCandidateV2], proxy_weights: ProxyWeights, cost: T32CostIdentity
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        records.append(
            {
                "candidate_id": candidate.candidate_id,
                "adjustment_family": candidate.adjustment_family,
                "view_indices": list(candidate.view_indices),
                "visual_tokens_per_view": list(candidate.visual_tokens_per_view),
                "prompt_id": candidate.prompt_id,
                "text_tokens": candidate.text_tokens,
                "visual_tokens": candidate.visual_tokens,
                "total_tokens": candidate.total_tokens,
                "target_band": candidate.target_band,
                "proxy_components": asdict(candidate.proxy),
                "semantic_loss_proxy": candidate.proxy.weighted_loss(proxy_weights),
                "batches": cost.batches(candidate.total_tokens),
                "logical_calls": cost.logical_calls(candidate.total_tokens),
            }
        )
    return records
