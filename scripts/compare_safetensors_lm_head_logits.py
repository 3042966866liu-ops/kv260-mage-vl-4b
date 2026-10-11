#!/usr/bin/env python3
"""Audit an explicit safetensors LM head against TeLLMe W4-GS64 packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from safetensors import safe_open


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--tensor-name", default="lm_head.weight")
    parser.add_argument("--packed", type=Path, required=True)
    parser.add_argument("--hidden-output", type=Path, required=True)
    parser.add_argument("--expected-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--random-states", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    model_index = json.loads((model_dir / "model.safetensors.index.json").read_text())
    shard = model_dir / model_index["weight_map"][args.tensor_name]
    with safe_open(shard, framework="pt", device="cpu") as source_file:
        source = source_file.get_slice(args.tensor_name)
        vocab, hidden_size = (int(value) for value in source.get_shape())
        rng = np.random.default_rng(args.seed)
        states = rng.standard_normal(
            (int(args.random_states), hidden_size), dtype=np.float32
        )
        exact = np.empty((vocab, states.shape[0]), dtype=np.float32)
        for start in range(0, vocab, 2048):
            stop = min(start + 2048, vocab)
            exact[start:stop] = source[start:stop].float().numpy() @ states.T

    groups = hidden_size // GROUP_SIZE
    blocks = vocab // OUTPUTS_PER_BLOCK
    packets = np.memmap(
        args.packed,
        dtype=np.uint8,
        mode="r",
        shape=(groups, blocks, PACKET_BYTES),
    )
    quantized = np.zeros_like(exact)
    for group in range(groups):
        packet = packets[group]
        packed_codes = packet[:, :256].reshape(
            blocks, OUTPUTS_PER_BLOCK, 32
        ).reshape(vocab, 32)
        scales = (
            packet[:, 256:272].copy().view("<f2").reshape(vocab).astype(np.float32)
        )
        zeros = (
            packet[:, 272:288].copy().view("<f2").reshape(vocab).astype(np.float32)
        )
        codes = np.empty((vocab, GROUP_SIZE), dtype=np.uint8)
        codes[:, 0::2] = packed_codes & 0x0F
        codes[:, 1::2] = packed_codes >> 4
        restored = (codes.astype(np.float32) - zeros[:, None]) * scales[:, None]
        start = group * GROUP_SIZE
        quantized += restored @ states[:, start : start + GROUP_SIZE].T
        print(json.dumps({"group": group + 1, "groups": groups}), flush=True)

    results = []
    exact_top1 = []
    for state in range(states.shape[0]):
        reference = exact[:, state]
        candidate = quantized[:, state]
        top1 = int(np.argmax(reference))
        order = np.argsort(candidate)[::-1]
        rank = int(np.flatnonzero(order == top1)[0]) + 1
        error = candidate - reference
        exact_top1.append(top1)
        results.append(
            {
                "state": state,
                "fp16_top1": top1,
                "w4_top1": int(order[0]),
                "fp16_top1_rank_in_w4": rank,
                "fp16_top1_in_rescore256": rank <= 256,
                "logit_relative_l2": float(
                    np.linalg.norm(error) / np.linalg.norm(reference)
                ),
            }
        )

    passed = all(item["fp16_top1_in_rescore256"] for item in results)
    report = {
        "status": "PASS" if passed else "FAIL",
        "source_tensor": args.tensor_name,
        "states": len(results),
        "results": results,
    }
    args.hidden_output.parent.mkdir(parents=True, exist_ok=True)
    args.expected_output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.hidden_output, states)
    args.expected_output.write_text(
        json.dumps({"fp16_top1": exact_top1}, indent=2, sort_keys=True) + "\n"
    )
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
