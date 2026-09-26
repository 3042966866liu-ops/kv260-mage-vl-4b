"""Counterbalanced hardware-boundary schedules and latency summaries."""

from __future__ import annotations

from collections import defaultdict
import math
import statistics


BOUNDARY_TRIPLETS = ((127, 128, 129), (159, 160, 161), (191, 192, 193))


def batches(tokens: int, granularity: int = 32) -> int:
    if tokens <= 0 or granularity <= 0:
        raise ValueError("tokens and granularity must be positive")
    return math.ceil(tokens / granularity)


def calls(tokens: int) -> int:
    return 154 * batches(tokens) + 8


def counterbalanced_schedule(repetitions: int = 3) -> list[dict]:
    if repetitions != 3:
        raise ValueError("the frozen pilot schedule requires exactly three repetitions")
    records = []
    for repetition in range(repetitions):
        boundary_order = BOUNDARY_TRIPLETS[repetition:] + BOUNDARY_TRIPLETS[:repetition]
        for triplet in boundary_order:
            probe_order = triplet[repetition:] + triplet[:repetition]
            for position, tokens in enumerate(probe_order):
                records.append({
                    "measurement_index": len(records),
                    "repetition": repetition,
                    "boundary": triplet[1],
                    "position_within_triplet": position,
                    "prompt_tokens": tokens,
                    "t32_batches": batches(tokens),
                    "expected_logical_fpga_calls": calls(tokens),
                })
    return records


def summarize_latency(records: list[dict]) -> dict:
    if len(records) != 27:
        raise ValueError("complete pilot latency summary requires all 27 measurements")
    by_tokens: dict[int, list[float]] = defaultdict(list)
    for record in records:
        if not record.get("finite", False):
            raise ValueError("non-finite hardware output")
        tokens = int(record["prompt_tokens"])
        if int(record["observed_logical_fpga_calls"]) != calls(tokens):
            raise ValueError("logical FPGA call identity mismatch")
        value = float(record["prefill_ms"])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("invalid prefill timing")
        by_tokens[tokens].append(value)
    if set(by_tokens) != {value for triplet in BOUNDARY_TRIPLETS for value in triplet}:
        raise ValueError("boundary token closure mismatch")
    if any(len(values) != 3 for values in by_tokens.values()):
        raise ValueError("each token count requires exactly three measurements")

    token_summary = {}
    for tokens, values in sorted(by_tokens.items()):
        median = statistics.median(values)
        mad = statistics.median(abs(value - median) for value in values)
        token_summary[str(tokens)] = {"values_ms": values, "median_ms": median, "mad_ms": mad}

    boundaries = {}
    for low, edge, high in BOUNDARY_TRIPLETS:
        plateau = token_summary[str(edge)]["median_ms"] - token_summary[str(low)]["median_ms"]
        step = token_summary[str(high)]["median_ms"] - (
            token_summary[str(low)]["median_ms"] + token_summary[str(edge)]["median_ms"]
        ) / 2.0
        noise_floor = max(token_summary[str(low)]["mad_ms"], token_summary[str(edge)]["mad_ms"])
        boundaries[str(edge)] = {
            "same_batch_plateau_delta_ms": plateau,
            "cross_boundary_step_delta_ms": step,
            "same_batch_mad_noise_floor_ms": noise_floor,
            "step_exceeds_same_batch_mad": step > noise_floor,
            "causal_speed_claim_allowed": False,
        }
    return {
        "token_summary": token_summary,
        "boundary_summary": boundaries,
        "latency_distribution_measured": True,
        "sample_count_per_token": 3,
        "causal_speed_claim_allowed": False,
        "note": "Three repeats are a pilot distribution, not a powered causal performance study.",
    }
