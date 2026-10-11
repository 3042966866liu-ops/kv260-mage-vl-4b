#!/usr/bin/env python3
"""Evaluate grouped activation quantization against all 196 deployed W4 linears."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
WEIGHT_BYTES = 288


def activation_delta(values: np.ndarray, bits: int) -> np.ndarray:
    baseline = np.asarray(values, dtype="<f2").astype(np.float32)
    maximum = float(np.max(np.abs(baseline)))
    if maximum == 0.0:
        return np.zeros_like(baseline)
    qmax = (1 << (bits - 1)) - 1
    scale = np.float32(maximum / qmax)
    quantized = np.clip(np.rint(baseline / scale), -qmax, qmax).astype(np.int32)
    restored = quantized.astype(np.float32) * scale
    return restored - baseline


def quantize_activation(values: np.ndarray, bits: int) -> np.ndarray:
    """Return the values seen by the W4 kernel after symmetric quantization."""
    baseline = np.asarray(values, dtype="<f2").astype(np.float32)
    maximum = float(np.max(np.abs(baseline)))
    if maximum == 0.0:
        return np.zeros_like(baseline)
    qmax = (1 << (bits - 1)) - 1
    scale = np.float32(maximum / qmax)
    quantized = np.clip(np.rint(baseline / scale), -qmax, qmax).astype(np.int32)
    return quantized.astype(np.float32) * scale


def decode_group(packet: np.ndarray) -> np.ndarray:
    blocks = packet.shape[0]
    outputs = blocks * OUTPUTS_PER_BLOCK
    packed = packet[:, :256].reshape(blocks, OUTPUTS_PER_BLOCK, 32).reshape(outputs, 32)
    codes = np.empty((outputs, GROUP_SIZE), dtype=np.uint8)
    codes[:, 0::2] = packed & 0x0F
    codes[:, 1::2] = packed >> 4
    scales = packet[:, 256:272].copy().view("<f2").reshape(outputs).astype(np.float32)
    zeros = packet[:, 272:288].copy().view("<f2").reshape(outputs).astype(np.float32)
    return (codes.astype(np.float32) - zeros[:, None]) * scales[:, None]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bits", type=int, nargs="+", default=[8, 10, 12])
    parser.add_argument(
        "--evaluate-fp16-accum",
        action="store_true",
        help="also round the running output accumulator to FP16 after every group",
    )
    args = parser.parse_args()

    bits = tuple(sorted(set(int(value) for value in args.bits)))
    if any(value < 2 or value > 16 for value in bits):
        raise ValueError("activation bits must be in [2, 16]")
    index = json.loads(args.index.read_text())
    weights = np.memmap(args.weights, dtype=np.uint8, mode="r")
    golden = np.load(args.golden)
    records: dict[int, list[dict[str, float | int | str]]] = {value: [] for value in bits}
    fp16_accum_records: list[dict[str, float | int | str]] = []

    for ordinal, item in enumerate(index["linears"]):
        groups = int(item["input_groups"])
        blocks = int(item["output_blocks"])
        start = int(item["offset"])
        stop = start + int(item["bytes"])
        packet = weights[start:stop].reshape(groups, blocks, WEIGHT_BYTES)
        x = np.asarray(golden[f"x_{ordinal:03d}"], dtype=np.float32).reshape(groups, GROUP_SIZE)
        reference = np.asarray(golden[f"y_{ordinal:03d}"], dtype=np.float32)
        errors = np.zeros((reference.size, len(bits)), dtype=np.float32)
        fp16_accum = np.zeros(reference.size, dtype=np.float32)
        fp32_a8_accum = np.zeros(reference.size, dtype=np.float32)
        for group in range(groups):
            matrix = decode_group(packet[group])
            deltas = np.stack(
                [activation_delta(x[group], value) for value in bits], axis=1
            )
            errors += matrix @ deltas
            if args.evaluate_fp16_accum:
                restored_a8 = quantize_activation(x[group], 8)
                contribution = matrix @ restored_a8
                fp32_a8_accum += contribution
                fp16_accum = (fp16_accum + contribution).astype(np.float16).astype(np.float32)
        reference_norm = max(float(np.linalg.norm(reference)), 1.0e-12)
        for column, value in enumerate(bits):
            error = errors[:, column]
            candidate = reference + error
            denom = max(
                float(np.linalg.norm(candidate)) * reference_norm,
                1.0e-12,
            )
            records[value].append(
                {
                    "ordinal": ordinal,
                    "name": item["name"],
                    "relative_l2": float(np.linalg.norm(error)) / reference_norm,
                    "max_abs": float(np.max(np.abs(error))),
                    "cosine": float(np.dot(candidate, reference)) / denom,
                }
            )
        if args.evaluate_fp16_accum:
            fp16_error = fp16_accum - reference
            fp16_penalty = fp16_accum - fp32_a8_accum
            fp16_denom = max(float(np.linalg.norm(fp16_accum)) * reference_norm, 1.0e-12)
            fp16_accum_records.append(
                {
                    "ordinal": ordinal,
                    "name": item["name"],
                    "relative_l2": float(np.linalg.norm(fp16_error)) / reference_norm,
                    "accumulator_penalty_relative_l2":
                        float(np.linalg.norm(fp16_penalty)) / reference_norm,
                    "max_abs": float(np.max(np.abs(fp16_error))),
                    "cosine": float(np.dot(fp16_accum, reference)) / fp16_denom,
                }
            )
        print(json.dumps({"linear": ordinal + 1, "linears": len(index["linears"])}))

    summary = {}
    for value in bits:
        relative = np.array([item["relative_l2"] for item in records[value]], dtype=np.float64)
        cosine = np.array([item["cosine"] for item in records[value]], dtype=np.float64)
        maximum = np.array([item["max_abs"] for item in records[value]], dtype=np.float64)
        worst_index = int(np.argmax(relative))
        summary[str(value)] = {
            "median_relative_l2": float(np.median(relative)),
            "p95_relative_l2": float(np.percentile(relative, 95)),
            "worst_relative_l2": float(relative[worst_index]),
            "worst_relative_l2_linear": records[value][worst_index]["name"],
            "minimum_cosine": float(np.min(cosine)),
            "p95_max_abs": float(np.percentile(maximum, 95)),
            "worst_max_abs": float(np.max(maximum)),
        }
    result = {
        "format": "tellme-prefill-activation-quant-eval-v1",
        "linear_count": len(index["linears"]),
        "group_size": GROUP_SIZE,
        "summary": summary,
        "records": {str(value): records[value] for value in bits},
    }
    if args.evaluate_fp16_accum:
        relative = np.array(
            [item["relative_l2"] for item in fp16_accum_records], dtype=np.float64
        )
        penalty = np.array(
            [item["accumulator_penalty_relative_l2"] for item in fp16_accum_records],
            dtype=np.float64,
        )
        cosine = np.array([item["cosine"] for item in fp16_accum_records], dtype=np.float64)
        maximum = np.array([item["max_abs"] for item in fp16_accum_records], dtype=np.float64)
        worst_index = int(np.argmax(relative))
        result["fp16_accum_a8"] = {
            "summary": {
                "median_relative_l2": float(np.median(relative)),
                "p95_relative_l2": float(np.percentile(relative, 95)),
                "worst_relative_l2": float(relative[worst_index]),
                "worst_relative_l2_linear": fp16_accum_records[worst_index]["name"],
                "median_accumulator_penalty_relative_l2": float(np.median(penalty)),
                "p95_accumulator_penalty_relative_l2": float(np.percentile(penalty, 95)),
                "worst_accumulator_penalty_relative_l2": float(np.max(penalty)),
                "minimum_cosine": float(np.min(cosine)),
                "p95_max_abs": float(np.percentile(maximum, 95)),
                "worst_max_abs": float(np.max(maximum)),
            },
            "records": fp16_accum_records,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"linear_count": result["linear_count"], "summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
