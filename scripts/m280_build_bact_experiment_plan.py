#!/usr/bin/env python3
"""Build the evidence-locked BACT configuration and boundary experiment plan.

This gate does not run a model or touch the board.  It converts the existing
M272/M275 screening results and M277 board result into a reproducible method
definition while keeping unmeasured claims explicitly fail-closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


TILE_GRANULARITY = 32
LANGUAGE_FAMILIES_PER_BATCH = 154
LM_HEAD_CALLS = 8

EXPECTED_SHA256 = {
    "m272": "46aa16a636c5008ad65e51caad73da4d55f0da15cf4cc266ed53f59d8183d4f9",
    "m275": "234bba1a9b2796a2a231efd539427d39435715bda69a4f401b87f9273defb5bd",
    "m277": "fd276f069258bd5cf28ef094d55ff1db919faab961cf6b092c1993a25b75e6a3",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locked(path: Path, key: str) -> dict[str, Any]:
    observed = sha256(path)
    expected = EXPECTED_SHA256[key]
    if observed != expected:
        raise RuntimeError(
            f"M280 predecessor hash mismatch {key}: expected={expected} observed={observed}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def batches(tokens: int) -> int:
    if tokens <= 0:
        raise ValueError("token count must be positive")
    return math.ceil(tokens / TILE_GRANULARITY)


def calls(tokens: int) -> int:
    return LANGUAGE_FAMILIES_PER_BATCH * batches(tokens) + LM_HEAD_CALLS


def normalize_candidate(source: str, candidate: dict[str, Any]) -> dict[str, Any]:
    tokens = int(candidate["prompt_tokens"])
    observed_batches = int(candidate["t32_batches"])
    observed_calls = int(candidate["logical_calls"])
    expected_batches = batches(tokens)
    expected_calls = calls(tokens)
    if observed_batches != expected_batches or observed_calls != expected_calls:
        raise RuntimeError(
            f"M280 cost identity mismatch {source}/{candidate['name']}: "
            f"observed={observed_batches}/{observed_calls} "
            f"expected={expected_batches}/{expected_calls}"
        )
    return {
        "id": f"{source}:{candidate['name']}",
        "source": source,
        "name": candidate["name"],
        "prompt": candidate["prompt"],
        "view_count": int(candidate.get("view_count", 2)),
        "visual_tokens": int(candidate["visual_tokens"]),
        "total_prompt_tokens": tokens,
        "t32_batches": observed_batches,
        "logical_fpga_calls": observed_calls,
        "small_regression_pass": bool(candidate["suite_pass"]),
        "screen_minimum_absolute_two_token_margin": float(
            candidate["minimum_absolute_margin"]
        ),
        "calibrated_accuracy": False,
    }


def choose_token_count_aware(eligible: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        eligible,
        key=lambda item: (
            item["total_prompt_tokens"],
            -item["screen_minimum_absolute_two_token_margin"],
            item["id"],
        ),
    )


def choose_boundary_aware(eligible: list[dict[str, Any]]) -> dict[str, Any]:
    """Lexicographic screen: batches, quality surrogate, then information kept."""
    return min(
        eligible,
        key=lambda item: (
            item["t32_batches"],
            -item["screen_minimum_absolute_two_token_margin"],
            -item["total_prompt_tokens"],
            item["id"],
        ),
    )


def boundary_probe(tokens: int) -> dict[str, int]:
    return {
        "total_prompt_tokens": tokens,
        "t32_batches": batches(tokens),
        "expected_logical_fpga_calls": calls(tokens),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    paths = {
        "m272": root / "M272_GPU_VIEW_COUNT_SWEEP_RESULT.json",
        "m275": root / "M275_GPU_EXACT_PROMPT_SWEEP_RESULT.json",
        "m277": root / "M277_M276_FIXED_WINDOW_BOARD_RESULT_01.json",
    }
    m272 = load_locked(paths["m272"], "m272")
    m275 = load_locked(paths["m275"], "m275")
    m277 = load_locked(paths["m277"], "m277")

    if m272.get("status") != "PASS_SCREEN_HAS_CANDIDATE":
        raise RuntimeError("M280 requires M272 screen PASS")
    if m275.get("status") != "PASS_SCREEN_HAS_SHORT_PROMPT":
        raise RuntimeError("M280 requires M275 screen PASS")
    if m277.get("functional_status") != "PASS":
        raise RuntimeError("M280 requires M277 real-board functional PASS")

    candidates = [
        normalize_candidate("M272", item) for item in m272["candidates"]
    ] + [normalize_candidate("M275", item) for item in m275["candidates"]]
    eligible = [item for item in candidates if item["small_regression_pass"]]
    if not eligible:
        raise RuntimeError("M280 found no eligible screened configuration")

    fixed_high_quality = next(
        item for item in candidates if item["id"] == "M272:four_views_v1_baseline"
    )
    token_count_aware = choose_token_count_aware(eligible)
    boundary_aware = choose_boundary_aware(eligible)

    if token_count_aware["id"] != "M275:plain_minimal":
        raise RuntimeError("M280 token-count baseline identity changed")
    if boundary_aware["id"] != "M275:tagged_short":
        raise RuntimeError("M280 BACT screen identity changed")
    if boundary_aware["t32_batches"] != token_count_aware["t32_batches"]:
        raise RuntimeError("M280 same-batch comparison was not preserved")

    board_identity_pass = (
        int(m277["prompt_tokens"]) == boundary_aware["total_prompt_tokens"]
        and int(m277["visual_tokens"]) == boundary_aware["visual_tokens"]
        and int(m277["events"][-1]["payload"]["proof"]["pl_logical_chain_calls"])
        == boundary_aware["logical_fpga_calls"]
    )
    if not board_identity_pass:
        raise RuntimeError("M280 M277 board identity does not match selected BACT screen")

    probe_tokens = (127, 128, 129, 159, 160, 161, 191, 192, 193)
    probes = [boundary_probe(value) for value in probe_tokens]

    result = {
        "date": "2026-09-02",
        "gate": "M280-BACT-method-and-experiment-plan",
        "status": "PASS_METHOD_PLAN_ONLY",
        "classification": (
            "Evidence-locked method definition, candidate audit and planned boundary "
            "matrix only; not a new model run, calibrated accuracy, comparative board "
            "speedup, power result, Web promotion or real-time PASS."
        ),
        "method": {
            "name": "Boundary-Aligned Cross-modal Token Budgeting",
            "acronym": "BACT",
            "target_hardware_granularity": TILE_GRANULARITY,
            "batch_cost": "ceil((visual_tokens + text_and_template_tokens) / T)",
            "current_runtime_call_identity": "logical_calls = 154 * batches + 8",
            "selection_rule": (
                "Among configurations meeting the quality constraint, minimize hardware "
                "batches; within one batch count minimize semantic loss; then preserve "
                "more information and lower memory."
            ),
            "screening_surrogate_used_now": (
                "4-sample constrained 0/1 correctness plus minimum absolute two-token "
                "logit margin; this is not calibrated target-scene accuracy."
            ),
            "final_quality_constraints_required": [
                "held-out knife recall",
                "held-out knife false-alarm rate",
                "held-out action macro-F1",
            ],
        },
        "predecessors": {
            key: {"path": str(path.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(path)}
            for key, path in paths.items()
        },
        "candidate_count": len(candidates),
        "eligible_screened_candidate_count": len(eligible),
        "candidates": candidates,
        "baselines": {
            "fixed_high_quality": fixed_high_quality,
            "fixed_ratio_visual_pruning": {
                "status": "PLANNED_NOT_MEASURED",
                "requirement": (
                    "Use the same semantic importance order and a frozen pruning ratio; "
                    "do not select its token budget from a T32 boundary."
                ),
            },
            "token_count_aware": token_count_aware,
            "bact_boundary_aware": boundary_aware,
        },
        "same_hardware_cost_screen_observation": {
            "token_count_aware_tokens": token_count_aware["total_prompt_tokens"],
            "bact_tokens": boundary_aware["total_prompt_tokens"],
            "additional_tokens_preserved_by_bact": (
                boundary_aware["total_prompt_tokens"]
                - token_count_aware["total_prompt_tokens"]
            ),
            "both_t32_batches": boundary_aware["t32_batches"],
            "both_logical_fpga_calls": boundary_aware["logical_fpga_calls"],
            "token_count_aware_minimum_margin": token_count_aware[
                "screen_minimum_absolute_two_token_margin"
            ],
            "bact_minimum_margin": boundary_aware[
                "screen_minimum_absolute_two_token_margin"
            ],
            "margin_is_calibrated_accuracy": False,
        },
        "m277_selected_bact_board_observation": {
            "identity_match": board_identity_pass,
            "prompt_tokens": int(m277["prompt_tokens"]),
            "t32_batches": batches(int(m277["prompt_tokens"])),
            "logical_fpga_calls": int(
                m277["events"][-1]["payload"]["proof"]["pl_logical_chain_calls"]
            ),
            "first_token_ms": float(m277["first_token_ms"]),
            "language_prefill_to_first_token_ms": float(
                m277["stage_timing_ms"]["language_prefill_to_first_token"]
            ),
            "comparative_boundary_speedup_measured": False,
        },
        "planned_boundary_probes": probes,
        "required_comparisons": [
            "159 vs 160 vs 161 first, using one frozen visual input and controlled prompt geometry",
            "127 vs 128 vs 129 after the 160 boundary closes",
            "191 vs 192 vs 193 after the 128 boundary closes",
            "164 vs 159 vs 144 with held-out semantic metrics and real board TTFT",
        ],
        "fail_closed_claims": {
            "cost_formula_is_total_latency": False,
            "four_sample_screen_is_accuracy": False,
            "m277_proves_bact_speedup": False,
            "m277_is_real_time": False,
            "hardware_aware_pruning_claimed_as_first": False,
        },
        "active_board_service_changed": False,
        "board_execution_run": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Build M281 controlled 159/160/161 boundary fixtures and prove tokenizer, "
            "hidden-state and expected-call identities offline before any COM3 board run."
        ),
    }

    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, args.result)
    print(
        "M280_BACT_METHOD_PLAN_PASS "
        f"bact={boundary_aware['total_prompt_tokens']}/"
        f"{boundary_aware['t32_batches']}/"
        f"{boundary_aware['logical_fpga_calls']} "
        f"token_count={token_count_aware['total_prompt_tokens']}/"
        f"{token_count_aware['t32_batches']}/"
        f"{token_count_aware['logical_fpga_calls']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
