#!/usr/bin/env python3
"""Build board golden vectors and audit W4 error against a Qwen checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288


def tensor_map(model_dir: Path) -> dict[str, str]:
    index_path = model_dir / "model.safetensors.index.json"
    if index_path.exists():
        return {
            str(name): str(shard)
            for name, shard in json.loads(index_path.read_text())["weight_map"].items()
        }
    shards = sorted(model_dir.glob("*.safetensors"))
    if len(shards) != 1:
        raise RuntimeError("expected one safetensors file or a shard index")
    with safe_open(shards[0], framework="pt", device="cpu") as source:
        return {str(name): shards[0].name for name in source.keys()}


def decode_group(packet: np.ndarray) -> np.ndarray:
    blocks = int(packet.shape[0])
    outputs = blocks * OUTPUTS_PER_BLOCK
    packed = packet[:, :256].reshape(
        blocks, OUTPUTS_PER_BLOCK, 32
    ).reshape(outputs, 32)
    codes = np.empty((outputs, GROUP_SIZE), dtype=np.uint8)
    codes[:, 0::2] = packed & 0x0F
    codes[:, 1::2] = packed >> 4
    scales = (
        packet[:, 256:272]
        .copy()
        .view("<f2")
        .reshape(outputs)
        .astype(np.float32)
    )
    zeros = (
        packet[:, 272:288]
        .copy()
        .view("<f2")
        .reshape(outputs)
        .astype(np.float32)
    )
    return (codes.astype(np.float32) - zeros[:, None]) * scales[:, None]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260824)
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    mapping = tensor_map(model_dir)
    index = json.loads(args.index.read_text())
    weights = np.memmap(args.weights, dtype=np.uint8, mode="r")
    rng = np.random.default_rng(int(args.seed))
    golden: dict[str, np.ndarray] = {}
    records: list[dict[str, object]] = []

    for ordinal, item in enumerate(index["linears"]):
        name = str(item["name"])
        groups = int(item["input_groups"])
        blocks = int(item["output_blocks"])
        outputs = blocks * OUTPUTS_PER_BLOCK
        inputs = groups * GROUP_SIZE
        x = rng.standard_normal(inputs, dtype=np.float32)

        start = int(item["offset"])
        stop = start + int(item["bytes"])
        packet = weights[start:stop].reshape(groups, blocks, PACKET_BYTES)
        w4_output = np.zeros(outputs, dtype=np.float32)
        for group in range(groups):
            matrix = decode_group(packet[group])
            w4_output += matrix @ x[group * GROUP_SIZE : (group + 1) * GROUP_SIZE]

        if name not in mapping:
            raise KeyError(f"checkpoint tensor not found: {name}")
        with safe_open(
            model_dir / mapping[name], framework="pt", device="cpu"
        ) as source:
            matrix = source.get_tensor(name).to(dtype=torch.float32)
        if tuple(matrix.shape) != (outputs, inputs):
            raise ValueError(
                f"{name} source shape {tuple(matrix.shape)} != {(outputs, inputs)}"
            )
        source_output = torch.mv(matrix, torch.from_numpy(x)).numpy()
        del matrix

        error = w4_output - source_output
        source_norm = max(float(np.linalg.norm(source_output)), 1.0e-12)
        denom = max(
            float(np.linalg.norm(w4_output)) * source_norm,
            1.0e-12,
        )
        record = {
            "ordinal": ordinal,
            "name": name,
            "shape": [outputs, inputs],
            "relative_l2": float(np.linalg.norm(error)) / source_norm,
            "cosine": float(np.vdot(w4_output, source_output)) / denom,
            "max_abs": float(np.max(np.abs(error))),
        }
        records.append(record)
        golden[f"x_{ordinal:03d}"] = x
        # The board gate isolates A8/FPGA arithmetic error from W4 model error.
        golden[f"y_{ordinal:03d}"] = w4_output
        print(
            json.dumps(
                {
                    "linear": ordinal + 1,
                    "linears": len(index["linears"]),
                    "name": name,
                    "relative_l2": record["relative_l2"],
                    "cosine": record["cosine"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    relative = np.asarray([float(x["relative_l2"]) for x in records])
    cosine = np.asarray([float(x["cosine"]) for x in records])
    maximum = np.asarray([float(x["max_abs"]) for x in records])
    worst = int(np.argmax(relative))
    report = {
        "format": "tellme-qwen-linear-golden-v1",
        "source_model": str(model_dir),
        "linear_count": len(records),
        "seed": int(args.seed),
        "summary": {
            "median_relative_l2": float(np.median(relative)),
            "p95_relative_l2": float(np.percentile(relative, 95)),
            "worst_relative_l2": float(relative[worst]),
            "worst_relative_l2_linear": records[worst]["name"],
            "minimum_cosine": float(np.min(cosine)),
            "median_cosine": float(np.median(cosine)),
            "p95_max_abs": float(np.percentile(maximum, 95)),
            "worst_max_abs": float(np.max(maximum)),
        },
        "records": records,
    }
    args.golden.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.golden, **golden)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", **report["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
