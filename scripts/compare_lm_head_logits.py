#!/usr/bin/env python3
"""Compare full-vocabulary FP16 and TeLLMe W4-GS64 LM-head logits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aux", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--packed", type=Path, required=True)
    parser.add_argument("--hidden", type=Path)
    parser.add_argument("--random-states", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    index = json.loads(args.index.read_text())
    embedding_item = next(
        item
        for item in index["aux_tensors"]
        if item["name"] == "model.embed_tokens.weight"
    )
    vocab, hidden_size = (int(value) for value in embedding_item["shape"])
    groups = hidden_size // GROUP_SIZE
    blocks = vocab // OUTPUTS_PER_BLOCK
    embedding = np.memmap(
        args.aux,
        dtype="<f2",
        mode="r",
        offset=int(embedding_item["offset"]),
        shape=(vocab, hidden_size),
    )
    packets = np.memmap(
        args.packed,
        dtype=np.uint8,
        mode="r",
        shape=(groups, blocks, PACKET_BYTES),
    )
    if args.hidden:
        states = np.asarray(np.load(args.hidden), dtype=np.float32)
    else:
        rng = np.random.default_rng(args.seed)
        states = rng.standard_normal(
            (int(args.random_states), hidden_size), dtype=np.float32
        )
    if states.ndim != 2 or states.shape[1] != hidden_size:
        raise ValueError(f"hidden states must have shape (N, {hidden_size})")

    exact = np.empty((vocab, states.shape[0]), dtype=np.float32)
    for start in range(0, vocab, 2048):
        stop = min(start + 2048, vocab)
        exact[start:stop] = (
            np.asarray(embedding[start:stop], dtype=np.float32) @ states.T
        )

    quantized = np.zeros_like(exact)
    for group in range(groups):
        packet = packets[group]
        packed_codes = packet[:, :256].reshape(blocks, OUTPUTS_PER_BLOCK, 32).reshape(vocab, 32)
        scales = packet[:, 256:272].copy().view("<f2").reshape(vocab).astype(np.float32)
        zeros = packet[:, 272:288].copy().view("<f2").reshape(vocab).astype(np.float32)
        codes = np.empty((vocab, GROUP_SIZE), dtype=np.uint8)
        codes[:, 0::2] = packed_codes & 0x0F
        codes[:, 1::2] = packed_codes >> 4
        restored = (codes.astype(np.float32) - zeros[:, None]) * scales[:, None]
        start = group * GROUP_SIZE
        quantized += restored @ states[:, start : start + GROUP_SIZE].T

    results = []
    for state in range(states.shape[0]):
        reference = exact[:, state]
        candidate = quantized[:, state]
        reference_top = np.argpartition(reference, -20)[-20:]
        candidate_top = np.argpartition(candidate, -20)[-20:]
        reference_order = reference_top[np.argsort(reference[reference_top])[::-1]]
        candidate_order = candidate_top[np.argsort(candidate[candidate_top])[::-1]]
        candidate_full_order = np.argsort(candidate)[::-1]
        reference_full_order = np.argsort(reference)[::-1]
        error = candidate - reference
        top1 = int(reference_order[0])
        second = int(reference_order[1])
        results.append(
            {
                "state": state,
                "fp16_top1": top1,
                "w4_top1": int(candidate_order[0]),
                "top1_match": bool(top1 == int(candidate_order[0])),
                "fp16_top1_rank_in_w4": int(np.flatnonzero(candidate_full_order == top1)[0]) + 1,
                "w4_top1_rank_in_fp16": int(
                    np.flatnonzero(reference_full_order == int(candidate_order[0]))[0]
                ) + 1,
                "top20_overlap": int(len(set(reference_top.tolist()) & set(candidate_top.tolist()))),
                "fp16_margin": float(reference[top1] - reference[second]),
                "w4_error_at_fp16_top1": float(error[top1]),
                "logit_rmse": float(np.sqrt(np.mean(error * error))),
                "logit_relative_l2": float(
                    np.linalg.norm(error) / np.linalg.norm(reference)
                ),
            }
        )
    summary = {
        "states": len(results),
        "top1_matches": sum(int(item["top1_match"]) for item in results),
        "mean_top20_overlap": float(np.mean([item["top20_overlap"] for item in results])),
        "mean_logit_relative_l2": float(
            np.mean([item["logit_relative_l2"] for item in results])
        ),
        "results": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
