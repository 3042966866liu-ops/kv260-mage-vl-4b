#!/usr/bin/env python3
"""Deterministic unit/evidence gate for the formal BACT selector."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.selector import AcceleratorCostModel, Candidate, QualityConstraint, select_four_baselines


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate(
    candidate_id: str,
    visual: int,
    text: int,
    loss: float,
    recall: float,
    false_alarm: float,
    macro_f1: float,
    ratio: float,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        visual_tokens=visual,
        text_tokens=text,
        semantic_loss=loss,
        knife_recall=recall,
        knife_false_alarm_rate=false_alarm,
        action_macro_f1=macro_f1,
        memory_bytes=(visual + text) * 5120,
        view_count=max(1, round(visual / 49)),
        pruning_ratio=ratio,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    source = workspace / "bact/selector.py"

    model = AcceleratorCostModel()
    assert [(n, model.batches(n), model.logical_calls(n)) for n in (127, 128, 129)] == [
        (127, 4, 624), (128, 4, 624), (129, 5, 778)
    ]
    assert [(n, model.batches(n), model.logical_calls(n)) for n in (159, 160, 161)] == [
        (159, 5, 778), (160, 5, 778), (161, 6, 932)
    ]
    assert [(n, model.batches(n), model.logical_calls(n)) for n in (191, 192, 193)] == [
        (191, 6, 932), (192, 6, 932), (193, 7, 1086)
    ]
    assert model.estimated_language_ms(159) is None

    constraint = QualityConstraint(0.90, 0.10, 0.75, 2_000_000)
    candidates = [
        candidate("high-284", 196, 88, 0.00, 0.96, 0.04, 0.84, 0.00),
        candidate("ratio-164", 98, 66, 0.08, 0.94, 0.05, 0.81, 0.50),
        candidate("bact-159", 98, 61, 0.05, 0.94, 0.05, 0.82, 0.50),
        candidate("count-144", 98, 46, 0.12, 0.92, 0.07, 0.78, 0.50),
        candidate("reject-127", 80, 47, 0.30, 0.82, 0.18, 0.62, 0.59),
    ]
    selected = select_four_baselines(
        candidates,
        constraint,
        model,
        fixed_high_quality_id="high-284",
        fixed_ratio_candidate_id="ratio-164",
        fixed_pruning_ratio=0.50,
    )
    observed_ids = {key: value.candidate.candidate_id for key, value in selected.items()}
    expected_ids = {
        "fixed_high_quality": "high-284",
        "fixed_ratio_visual_pruning": "ratio-164",
        "token_count_aware": "count-144",
        "bact": "bact-159",
    }
    assert observed_ids == expected_ids, (observed_ids, expected_ids)
    assert selected["bact"].logical_calls == selected["token_count_aware"].logical_calls == 778
    assert selected["bact"].candidate.total_tokens - selected["token_count_aware"].candidate.total_tokens == 15
    assert selected["bact"].candidate.semantic_loss < selected["token_count_aware"].candidate.semantic_loss

    result = {
        "date": "2026-09-02",
        "gate": "M288-formal-BACT-selector-and-four-baseline-contract",
        "status": "PASS_ALGORITHM_AND_SYNTHETIC_CONTRACT",
        "classification": (
            "Executable cost model and deterministic four-baseline selection contract on synthetic "
            "calibration metrics. This does not measure target-scene accuracy, board timing, resources, "
            "power, Web behavior or real-time performance."
        ),
        "hardware_geometry": {
            "token_granularity": model.token_granularity,
            "logical_call_identity": "154 * ceil(total_tokens / 32) + 8",
            "latency_coefficients_fitted": False,
            "boundaries": {
                "127_128_129": [[n, model.batches(n), model.logical_calls(n)] for n in (127, 128, 129)],
                "159_160_161": [[n, model.batches(n), model.logical_calls(n)] for n in (159, 160, 161)],
                "191_192_193": [[n, model.batches(n), model.logical_calls(n)] for n in (191, 192, 193)],
            },
        },
        "frozen_quality_constraint": {
            "minimum_knife_recall": constraint.minimum_knife_recall,
            "maximum_knife_false_alarm_rate": constraint.maximum_knife_false_alarm_rate,
            "minimum_action_macro_f1": constraint.minimum_action_macro_f1,
            "maximum_memory_bytes": constraint.maximum_memory_bytes,
        },
        "selected": {key: value.to_dict() for key, value in selected.items()},
        "expected_selected_ids": expected_ids,
        "test_cases": [
            "three exact T32 boundary triplets",
            "unfitted latency returns no estimate",
            "quality/resource infeasible candidate rejected",
            "fixed high-quality and fixed-ratio configurations are frozen by exact ID",
            "BACT preserves 15 more tokens than token-count-aware at equal exact call cost",
        ],
        "source": str(source.relative_to(workspace)).replace("\\", "/"),
        "source_sha256": sha256(source),
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Freeze a real calibration manifest, populate measured semantic loss/quality metrics for every "
            "candidate, select all four baselines before opening the held-out test labels, then evaluate once."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M288_BACT_SELECTOR_PASS " + " ".join(f"{k}={v}" for k, v in observed_ids.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
