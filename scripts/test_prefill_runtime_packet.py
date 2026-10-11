#!/usr/bin/env python3
"""Validate the exact runtime W4A8 Prefill stream against all model linears."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
WEIGHT_BYTES = 288


def decode_weight_group(packet: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    blocks = packet.shape[0]
    outputs = blocks * OUTPUTS_PER_BLOCK
    packed = packet[:, :256].reshape(blocks, OUTPUTS_PER_BLOCK, 32).reshape(outputs, 32)
    codes = np.empty((outputs, GROUP_SIZE), dtype=np.uint8)
    codes[:, 0::2] = packed & 0x0F
    codes[:, 1::2] = packed >> 4
    scales = packet[:, 256:272].copy().view("<f2").reshape(outputs).astype(np.float32)
    zeros = packet[:, 272:288].copy().view("<f2").reshape(outputs).astype(np.float32)
    return codes, scales, zeros


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.runtime.resolve()))
    from prefill_packet import assemble_prefill_packet, quantize_activation_records

    index = json.loads(args.index.read_text())
    weights = np.memmap(args.weights, dtype=np.uint8, mode="r")
    golden = np.load(args.golden)
    records_out = []
    for ordinal, item in enumerate(index["linears"]):
        groups = int(item["input_groups"])
        blocks = int(item["output_blocks"])
        start = int(item["offset"])
        stop = start + int(item["bytes"])
        weight_packet = weights[start:stop].reshape(groups, blocks, WEIGHT_BYTES)
        x = np.asarray(golden[f"x_{ordinal:03d}"], dtype=np.float32).reshape(1, -1)
        reference = np.asarray(golden[f"y_{ordinal:03d}"], dtype=np.float32)
        activation_records, codes, scales = quantize_activation_records(x)

        parsed_codes = activation_records[:, 0, :64].view(np.int8)
        parsed_scales = (
            activation_records[:, 0, 64:66].copy().view("<f2").reshape(groups)
        )
        parsed_sums = (
            activation_records[:, 0, 66:68].copy().view("<i2").reshape(groups)
        )
        if not np.array_equal(parsed_codes, codes[0]):
            raise AssertionError(f"activation code packing failed for {item['name']}")
        if not np.array_equal(parsed_scales, scales[0]):
            raise AssertionError(f"activation scale packing failed for {item['name']}")
        expected_sums = np.sum(codes[0].astype(np.int16), axis=-1).astype(np.int16)
        if not np.array_equal(parsed_sums, expected_sums):
            raise AssertionError(f"activation sum packing failed for {item['name']}")

        stream = assemble_prefill_packet(activation_records, weight_packet)
        stride = 80 + blocks * WEIGHT_BYTES
        interleaved = stream.reshape(groups, stride)
        if not np.array_equal(interleaved[:, :80], activation_records[:, 0, :]):
            raise AssertionError(f"activation interleave failed for {item['name']}")
        if not np.array_equal(
            interleaved[:, 80:].reshape(groups, blocks, WEIGHT_BYTES), weight_packet
        ):
            raise AssertionError(f"weight interleave failed for {item['name']}")

        accumulator = np.zeros((blocks * OUTPUTS_PER_BLOCK,), dtype=np.float32)
        for group in range(groups):
            weight_codes, weight_scales, weight_zeros = decode_weight_group(
                weight_packet[group]
            )
            dot = weight_codes.astype(np.int32) @ parsed_codes[group].astype(np.int32)
            corrected = dot.astype(np.float32) - weight_zeros * float(parsed_sums[group])
            contribution = corrected * weight_scales * float(parsed_scales[group])
            accumulator = (accumulator + contribution).astype(np.float16).astype(np.float32)

        error = accumulator - reference
        reference_norm = max(float(np.linalg.norm(reference)), 1.0e-12)
        relative_l2 = float(np.linalg.norm(error)) / reference_norm
        denom = max(float(np.linalg.norm(accumulator)) * reference_norm, 1.0e-12)
        cosine = float(np.dot(accumulator, reference)) / denom
        records_out.append(
            {
                "ordinal": ordinal,
                "name": item["name"],
                "relative_l2": relative_l2,
                "cosine": cosine,
                "max_abs": float(np.max(np.abs(error))),
                "stream_bytes": int(stream.size),
            }
        )
        print(json.dumps({"linear": ordinal + 1, "linears": len(index["linears"])}))

    relative = np.asarray([row["relative_l2"] for row in records_out])
    cosine = np.asarray([row["cosine"] for row in records_out])
    worst = int(np.argmax(relative))
    summary = {
        "format": "tellme-prefill-runtime-packet-gate-v1",
        "linear_count": len(records_out),
        "median_relative_l2": float(np.median(relative)),
        "p95_relative_l2": float(np.percentile(relative, 95)),
        "worst_relative_l2": float(relative[worst]),
        "worst_linear": records_out[worst]["name"],
        "minimum_cosine": float(np.min(cosine)),
        "max_stream_bytes": max(row["stream_bytes"] for row in records_out),
        "gate": "PASS"
        if float(np.max(relative)) < 0.012 and float(np.min(cosine)) > 0.9999
        else "FAIL",
        "records": records_out,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}))
    return 0 if summary["gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
