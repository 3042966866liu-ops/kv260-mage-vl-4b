#!/usr/bin/env python3
"""Fit the evidence-scoped BACT staircase cost model from M294R3 board data.

The structural model is exact for the frozen M120 T32 language chain:
    batches(N) = ceil(N / 32)
    logical_calls(N) = 154 * batches(N) + 8

The empirical latency model is descriptive and only valid over the measured
127--193 token range on the same KV260 build/runtime:
    prefill_ms ~= beta0 + beta_batch * batches(N) + beta_token * N

It intentionally does not promote three repeats per token into a powered
causal, accuracy, power, or real-time claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np


EXPECTED_SOURCE_SHA256 = "1a8138f92fc9340b1e5c660f886729cd725280d29877863af54cdd12aef895d1"
EXPECTED_TOKENS = (127, 128, 129, 159, 160, 161, 191, 192, 193)
BOUNDARIES = (128, 160, 192)
CALLS_PER_BATCH = 154
FIXED_CALLS = 8
T32 = 32


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median_absolute_deviation(values: list[float]) -> float:
    centre = statistics.median(values)
    return statistics.median(abs(value - centre) for value in values)


def fit_ols(tokens: list[int], medians_ms: list[float]) -> dict:
    x = np.asarray([[1.0, math.ceil(n / T32), float(n)] for n in tokens], dtype=np.float64)
    y = np.asarray(medians_ms, dtype=np.float64)
    coefficients, _, rank, singular_values = np.linalg.lstsq(x, y, rcond=None)
    predicted = x @ coefficients
    residuals = y - predicted
    sse = float(np.sum(residuals**2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    r2 = 1.0 - sse / sst

    # Descriptive coefficient intervals only. Token medians are few and not
    # independent enough to support a powered causal interpretation.
    dof = len(tokens) - x.shape[1]
    sigma2 = sse / dof
    covariance = sigma2 * np.linalg.inv(x.T @ x)
    standard_errors = np.sqrt(np.diag(covariance))
    t_975_df6 = 2.4469118511449692
    ci95 = [
        [float(value - t_975_df6 * se), float(value + t_975_df6 * se)]
        for value, se in zip(coefficients, standard_errors, strict=True)
    ]
    return {
        "formula": "prefill_ms_hat = beta0_ms + beta_batch_ms * ceil(prompt_tokens/32) + beta_token_ms * prompt_tokens",
        "beta0_ms": float(coefficients[0]),
        "beta_batch_ms": float(coefficients[1]),
        "beta_token_ms": float(coefficients[2]),
        "beta_batch_equivalent_ms_per_logical_call_descriptive_only": float(coefficients[1] / CALLS_PER_BATCH),
        "descriptive_coefficient_ci95": {
            "beta0_ms": ci95[0],
            "beta_batch_ms": ci95[1],
            "beta_token_ms": ci95[2],
        },
        "rank": int(rank),
        "singular_values": [float(v) for v in singular_values],
        "r_squared_on_nine_token_medians": r2,
        "rmse_ms_on_nine_token_medians": rmse,
        "residuals_by_token_ms": {str(n): float(r) for n, r in zip(tokens, residuals, strict=True)},
        "valid_prompt_token_range_inclusive": [min(tokens), max(tokens)],
        "extrapolation_allowed": False,
        "causal_speed_claim_allowed": False,
    }


def leave_one_boundary_out(tokens: list[int], medians_ms: list[float]) -> dict:
    groups = {128: {127, 128, 129}, 160: {159, 160, 161}, 192: {191, 192, 193}}
    rows = []
    all_errors: list[float] = []
    for boundary, held_tokens in groups.items():
        train = [(n, y) for n, y in zip(tokens, medians_ms, strict=True) if n not in held_tokens]
        test = [(n, y) for n, y in zip(tokens, medians_ms, strict=True) if n in held_tokens]
        x_train = np.asarray([[1.0, math.ceil(n / T32), float(n)] for n, _ in train])
        y_train = np.asarray([y for _, y in train])
        beta = np.linalg.lstsq(x_train, y_train, rcond=None)[0]
        errors = []
        for n, observed in test:
            predicted = float(np.asarray([1.0, math.ceil(n / T32), float(n)]) @ beta)
            error = observed - predicted
            errors.append({"prompt_tokens": n, "observed_ms": observed, "predicted_ms": predicted, "error_ms": error})
            all_errors.append(error)
        rows.append({"held_boundary": boundary, "records": errors})
    return {
        "folds": rows,
        "rmse_ms": float(math.sqrt(statistics.mean(error * error for error in all_errors))),
        "mae_ms": float(statistics.mean(abs(error) for error in all_errors)),
        "note": "Leave-one-boundary-out is a descriptive transport check across only three measured boundary neighbourhoods.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
    )
    parser.add_argument(
        "--output",
        default="deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
    )
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    observed_source_sha = sha256(source)
    if observed_source_sha != EXPECTED_SOURCE_SHA256:
        raise SystemExit(
            f"M297_SOURCE_HASH_FAIL expected={EXPECTED_SOURCE_SHA256} observed={observed_source_sha}"
        )
    board = json.loads(source.read_text(encoding="utf-8"))
    records = board["records"]
    if board["status"] != "PASS_COUNTERBALANCED_PILOT" or len(records) != 27:
        raise SystemExit("M297_SOURCE_GATE_FAIL expected M294R3 PASS_COUNTERBALANCED_PILOT with 27 records")
    if any(not row["pass"] or not row["finite"] for row in records):
        raise SystemExit("M297_RECORD_VALIDITY_FAIL")
    if any(row["expected_logical_fpga_calls"] != row["observed_logical_fpga_calls"] for row in records):
        raise SystemExit("M297_CALL_IDENTITY_FAIL")

    token_values: dict[int, list[float]] = {n: [] for n in EXPECTED_TOKENS}
    for row in records:
        n = int(row["prompt_tokens"])
        if n not in token_values:
            raise SystemExit(f"M297_UNEXPECTED_TOKEN_FAIL token={n}")
        expected_batches = math.ceil(n / T32)
        expected_calls = CALLS_PER_BATCH * expected_batches + FIXED_CALLS
        if row["t32_batches"] != expected_batches or row["observed_logical_fpga_calls"] != expected_calls:
            raise SystemExit(f"M297_STRUCTURAL_IDENTITY_FAIL token={n}")
        token_values[n].append(float(row["prefill_ms"]))
    if any(len(values) != 3 for values in token_values.values()):
        raise SystemExit("M297_REPEAT_COUNT_FAIL")

    tokens = list(EXPECTED_TOKENS)
    medians = [statistics.median(token_values[n]) for n in tokens]
    token_summary = {
        str(n): {
            "t32_batches": math.ceil(n / T32),
            "logical_fpga_calls": CALLS_PER_BATCH * math.ceil(n / T32) + FIXED_CALLS,
            "values_ms": token_values[n],
            "median_ms": statistics.median(token_values[n]),
            "mad_ms": median_absolute_deviation(token_values[n]),
        }
        for n in tokens
    }

    boundary_contrasts = []
    for boundary in BOUNDARIES:
        low = statistics.median(token_values[boundary - 1])
        at = statistics.median(token_values[boundary])
        high = statistics.median(token_values[boundary + 1])
        same = at - low
        # Both boundary-1 and boundary use the same T32 batch count. Centre the
        # plateau with their arithmetic mean before contrasting boundary+1.
        # This reproduces the pre-registered M294R3 analysis contract.
        plateau_centre = statistics.mean((low, at))
        step = high - plateau_centre
        source_step = float(board["summary"]["boundary_summary"][str(boundary)]["cross_boundary_step_delta_ms"])
        if not math.isclose(step, source_step, rel_tol=0.0, abs_tol=1e-6):
            raise SystemExit(f"M297_BOUNDARY_CONTRAST_CONTRACT_FAIL boundary={boundary}")
        noise_floor = max(
            median_absolute_deviation(token_values[boundary - 1]),
            median_absolute_deviation(token_values[boundary]),
        )
        boundary_contrasts.append(
            {
                "boundary": boundary,
                "same_batch_delta_ms": same,
                "same_batch_plateau_centre_ms": plateau_centre,
                "cross_boundary_step_ms": step,
                "same_batch_mad_noise_floor_ms": noise_floor,
                "step_to_noise_ratio": step / noise_floor,
                "step_exceeds_same_batch_mad": step > noise_floor,
            }
        )

    steps = [row["cross_boundary_step_ms"] for row in boundary_contrasts]
    step_mean = statistics.mean(steps)
    step_sd = statistics.stdev(steps)
    t_975_df2 = 4.302652729696142
    t_margin = t_975_df2 * step_sd / math.sqrt(len(steps))
    model = fit_ols(tokens, medians)

    candidate_tokens = (127, 128, 129, 144, 151, 159, 160, 161, 170, 191, 192, 193)
    estimates = []
    for n in candidate_tokens:
        batches = math.ceil(n / T32)
        pred = model["beta0_ms"] + model["beta_batch_ms"] * batches + model["beta_token_ms"] * n
        estimates.append(
            {
                "prompt_tokens": n,
                "t32_batches": batches,
                "logical_fpga_calls": CALLS_PER_BATCH * batches + FIXED_CALLS,
                "predicted_prefill_ms_descriptive": pred,
                "inside_measured_range": min(tokens) <= n <= max(tokens),
            }
        )

    result = {
        "date": "2026-09-03",
        "gate": "M297-BACT-T32-staircase-cost-model",
        "status": "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL",
        "classification": (
            "Hash-locked structural and descriptive empirical cost model from one real KV260 M294R3 run. "
            "It proves the T32 logical-call staircase and quantifies a pilot latency step; it is not a powered "
            "causal speed, semantic accuracy, power, resource, Web, or real-time result."
        ),
        "source": str(source).replace("\\", "/"),
        "source_sha256": observed_source_sha,
        "board_identity": {"build_id": board["build_id"], "kernel": board["kernel"]},
        "sample_count": len(records),
        "sample_count_per_token": 3,
        "structural_cost_model": {
            "batch_formula": "B(N)=ceil(N/32)",
            "logical_call_formula": "Calls(N)=154*B(N)+8",
            "t32_granularity": T32,
            "logical_calls_per_batch": CALLS_PER_BATCH,
            "fixed_logical_calls": FIXED_CALLS,
            "identity_passed_for_all_27_records": True,
            "scope": "M120/M89X2 frozen language Prefill chain only; not total system latency or power.",
        },
        "token_summary": token_summary,
        "boundary_contrasts": boundary_contrasts,
        "cross_boundary_step_summary": {
            "values_ms": steps,
            "mean_ms": step_mean,
            "median_ms": statistics.median(steps),
            "sample_standard_deviation_ms": step_sd,
            "descriptive_t_interval_95_ms_not_powered": [step_mean - t_margin, step_mean + t_margin],
        },
        "empirical_latency_model": model,
        "leave_one_boundary_out": leave_one_boundary_out(tokens, medians),
        "candidate_estimates": estimates,
        "claim_policy": {
            "structural_staircase_claim_allowed": True,
            "pilot_latency_step_claim_allowed": True,
            "causal_speed_claim_allowed": False,
            "semantic_accuracy_claim_allowed": False,
            "real_time_claim_allowed": False,
            "reason": "Only three repeats per token from one board session; human-labelled target-scene evaluation is still pending.",
        },
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Complete M296 whole-clip human review, freeze four-baseline calibration thresholds, and run held-out "
            "accuracy once. For a powered causal latency claim, pre-register a larger repeated counterbalanced board run."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(encoded, encoding="utf-8")
    print(
        "M297_BACT_STAIRCASE_COST_MODEL_PASS "
        f"beta_batch_ms={model['beta_batch_ms']:.3f} beta_token_ms={model['beta_token_ms']:.6f} "
        f"r2={model['r_squared_on_nine_token_medians']:.9f} "
        f"boundary_step_median_ms={statistics.median(steps):.3f} causal=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
