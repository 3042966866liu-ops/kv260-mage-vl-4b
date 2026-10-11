#!/usr/bin/env python3
"""Quantify measured hardware-boundary robustness without semantic overclaim."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics


EXPECTED = {
    "m294": "1a8138f92fc9340b1e5c660f886729cd725280d29877863af54cdd12aef895d1",
    "m297": "74b2205f532ab63caf623c1da5af2dbf0cb7e24214bdc9650a487f794debfbb2",
    "m299": "125c5ad99c7c02f4d5a91ba5b3f550d37ce1f283871cb4039312a1e4d6ea4201",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    paths = {
        "m294": root / "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
        "m297": root / "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
        "m299": root / "deployment/mage_vl4b/M299_BACT_EVALUATION_PROTOCOL_RESULT.json",
    }
    for name, path in paths.items():
        observed = digest(path)
        if observed != EXPECTED[name]:
            raise RuntimeError(f"M302_SOURCE_HASH_FAIL name={name} expected={EXPECTED[name]} observed={observed}")
    m294 = json.loads(paths["m294"].read_text(encoding="utf-8"))
    m297 = json.loads(paths["m297"].read_text(encoding="utf-8"))
    m299 = json.loads(paths["m299"].read_text(encoding="utf-8"))
    if m294["status"] != "PASS_COUNTERBALANCED_PILOT":
        raise RuntimeError("M302_M294_GATE_FAIL")
    if m297["status"] != "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL":
        raise RuntimeError("M302_M297_GATE_FAIL")
    if m299["status"] != "PASS_PROTOCOL_SYNTHETIC_REAL_LABELS_PENDING":
        raise RuntimeError("M302_M299_GATE_FAIL")

    contrasts = m297["boundary_contrasts"]
    if [row["boundary"] for row in contrasts] != [128, 160, 192]:
        raise RuntimeError("M302_BOUNDARY_IDENTITY_FAIL")
    steps = [float(row["cross_boundary_step_ms"]) for row in contrasts]
    plateau = [abs(float(row["same_batch_delta_ms"])) for row in contrasts]
    noise = [float(row["same_batch_mad_noise_floor_ms"]) for row in contrasts]
    mean_step = statistics.mean(steps)
    sd_step = statistics.stdev(steps)
    cv_percent = sd_step / mean_step * 100.0
    maximum_relative_deviation_percent = max(abs(step - mean_step) / mean_step * 100.0 for step in steps)
    exact_call_steps = []
    for boundary in (128, 160, 192):
        lower = m297["token_summary"][str(boundary)]["logical_fpga_calls"]
        upper = m297["token_summary"][str(boundary + 1)]["logical_fpga_calls"]
        exact_call_steps.append(upper - lower)
    if exact_call_steps != [154, 154, 154]:
        raise RuntimeError("M302_LOGICAL_CALL_STEP_FAIL")

    token_mads = {
        token: float(summary["mad_ms"])
        for token, summary in m297["token_summary"].items()
    }
    lobo_rmse = float(m297["leave_one_boundary_out"]["rmse_ms"])
    robustness = {
        "three_boundary_neighbourhoods_all_pass": all(row["step_exceeds_same_batch_mad"] for row in contrasts),
        "exact_logical_call_step_each_boundary": exact_call_steps,
        "latency_step_values_ms": steps,
        "latency_step_mean_ms": mean_step,
        "latency_step_median_ms": statistics.median(steps),
        "latency_step_sample_sd_ms": sd_step,
        "latency_step_cv_percent": cv_percent,
        "maximum_boundary_step_relative_deviation_percent": maximum_relative_deviation_percent,
        "same_batch_absolute_delta_ms": plateau,
        "step_to_same_batch_absolute_delta_ratio": [
            steps[index] / value if value > 0 else None for index, value in enumerate(plateau)
        ],
        "step_to_same_batch_mad_ratio": [steps[index] / value for index, value in enumerate(noise)],
        "token_mad_ms": token_mads,
        "median_token_mad_ms": statistics.median(token_mads.values()),
        "maximum_token_mad_ms": max(token_mads.values()),
        "leave_one_boundary_out_rmse_ms": lobo_rmse,
        "leave_one_boundary_out_rmse_as_step_percent": lobo_rmse / mean_step * 100.0,
    }
    # Pre-registered descriptive guardrails for this pilot only. These are not
    # semantic or powered inferential thresholds.
    pilot_pass = (
        robustness["three_boundary_neighbourhoods_all_pass"]
        and cv_percent < 2.0
        and maximum_relative_deviation_percent < 2.0
        and robustness["leave_one_boundary_out_rmse_as_step_percent"] < 1.0
    )
    if not pilot_pass:
        raise RuntimeError("M302_HARDWARE_STAIRCASE_ROBUSTNESS_PILOT_FAIL")

    result = {
        "date": "2026-09-03",
        "gate": "M302-BACT-hardware-boundary-robustness",
        "status": "PASS_THREE_BOUNDARY_HARDWARE_ROBUSTNESS_PILOT_SEMANTIC_PENDING",
        "classification": (
            "Measured consistency of the T32 logical-call and latency staircase across the 128, 160 and 192 "
            "boundary neighbourhoods in one counterbalanced KV260 session. This is a hardware pilot robustness "
            "result, not semantic/environmental robustness, powered causal inference, power, or real-time evidence."
        ),
        "board_identity": {"build_id": m294["build_id"], "kernel": m294["kernel"]},
        "hardware_robustness": robustness,
        "pilot_guardrails": {
            "all_steps_exceed_same_batch_mad": True,
            "maximum_step_cv_percent": 2.0,
            "maximum_step_relative_deviation_percent": 2.0,
            "maximum_lobo_rmse_as_step_percent": 1.0,
            "passed": pilot_pass,
        },
        "semantic_robustness": {
            "status": "PENDING_HUMAN_LABELS",
            "required_slices": ["low_light", "occlusion", "small_knife", "action_class", "knife_positive_negative"],
            "threshold_sensitivity_protocol_available": bool(
                m299["test_label_changes_leave_calibration_thresholds_unchanged"]
            ),
            "claim_allowed": False,
        },
        "claim_policy": {
            "three_boundary_hardware_staircase_robustness_claim_allowed": True,
            "semantic_robustness_claim_allowed": False,
            "environmental_robustness_claim_allowed": False,
            "powered_causal_speed_claim_allowed": False,
            "real_time_claim_allowed": False,
        },
        "sources": {
            name: {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": digest(path)}
            for name, path in paths.items()
        },
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "After M296 human labels pass, compute threshold, condition-slice and leave-one-clip calibration "
            "sensitivity for all four frozen baselines; do not infer real-world robustness from AI-generated pilot data."
        ),
    }
    result_path = (root / args.result).resolve()
    if not result_path.is_relative_to(root):
        raise RuntimeError("M302_RESULT_PATH_ESCAPE")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    partial = result_path.with_suffix(result_path.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, result_path)
    print(
        "M302_BACT_HARDWARE_ROBUSTNESS_PASS "
        f"boundaries=3 step_cv_percent={cv_percent:.6f} max_step_deviation_percent={maximum_relative_deviation_percent:.6f} "
        f"lobo_rmse_step_percent={robustness['leave_one_boundary_out_rmse_as_step_percent']:.6f} semantic=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
