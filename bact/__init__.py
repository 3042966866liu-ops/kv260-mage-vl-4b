"""Boundary-Aligned Cross-modal Token Budgeting (BACT)."""

from .selector import (
    AcceleratorCostModel,
    Candidate,
    QualityConstraint,
    Selection,
    select_four_baselines,
)
from .calibration import ThresholdSelection, calibrate_binary_threshold
from .dataset import validate_target_scene_manifest
from .selector_v2 import (
    BACTCandidateV2,
    BACTSelectionV2,
    ProxyComponents,
    ProxyWeights,
    T32CostIdentity,
    candidate_from_mapping,
    select_bact_v2,
)

__all__ = [
    "AcceleratorCostModel",
    "Candidate",
    "QualityConstraint",
    "Selection",
    "select_four_baselines",
    "ThresholdSelection",
    "calibrate_binary_threshold",
    "validate_target_scene_manifest",
    "BACTCandidateV2",
    "BACTSelectionV2",
    "ProxyComponents",
    "ProxyWeights",
    "T32CostIdentity",
    "candidate_from_mapping",
    "select_bact_v2",
]
