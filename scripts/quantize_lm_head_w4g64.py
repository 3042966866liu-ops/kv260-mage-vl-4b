#!/usr/bin/env python3
"""Stream-quantize a tied FP16 LM head into the TeLLMe W4-GS64 packet layout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


GROUP_SIZE = 64
OUTPUTS_PER_BLOCK = 8
PACKET_BYTES = 288


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantize_group(weights: np.ndarray, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return packed nibbles, FP16 scales and FP16 zero points for one input group."""
    if mode == "asymmetric":
        minimum = weights.min(axis=1)
        maximum = weights.max(axis=1)
        scale = (maximum - minimum) / 15.0
        scale = np.where(scale > 0.0, scale, 1.0)
        zero = np.clip(-minimum / scale, 0.0, 15.0)
    elif mode == "symmetric":
        scale = np.max(np.abs(weights), axis=1) / 7.0
        scale = np.where(scale > 0.0, scale, 1.0)
        zero = np.full(scale.shape, 8.0, dtype=np.float32)
    else:
        raise ValueError(f"unsupported quantization mode: {mode}")

    # Codes are generated against the same FP16 metadata consumed by the PL.
    scale_half = scale.astype("<f2")
    zero_half = zero.astype("<f2")
    scale_hw = scale_half.astype(np.float32)
    zero_hw = zero_half.astype(np.float32)
    codes = np.clip(
        np.rint(weights / scale_hw[:, None] + zero_hw[:, None]), 0, 15
    ).astype(np.uint8)
    packed = codes[:, 0::2] | (codes[:, 1::2] << 4)
    return packed, scale_half, zero_half


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aux", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--mode", choices=("asymmetric", "symmetric"), default="asymmetric")
    parser.add_argument("--max-groups", type=int)
    args = parser.parse_args()

    index = json.loads(args.index.read_text())
    embedding = next(
        item
        for item in index["aux_tensors"]
        if item["name"] == "model.embed_tokens.weight"
    )
    vocab, hidden = (int(value) for value in embedding["shape"])
    if hidden % GROUP_SIZE or vocab % OUTPUTS_PER_BLOCK:
        raise ValueError("current packet layout requires hidden % 64 == 0 and vocab % 8 == 0")
    groups = hidden // GROUP_SIZE
    if args.max_groups is not None:
        groups = min(groups, int(args.max_groups))
    blocks = vocab // OUTPUTS_PER_BLOCK
    source = np.memmap(
        args.aux,
        dtype="<f2",
        mode="r",
        offset=int(embedding["offset"]),
        shape=(vocab, hidden),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    packets = np.memmap(
        args.output,
        dtype=np.uint8,
        mode="w+",
        shape=(groups, blocks, PACKET_BYTES),
    )

    squared_error = 0.0
    squared_weight = 0.0
    maximum_error = 0.0
    for group in range(groups):
        start = group * GROUP_SIZE
        stop = start + GROUP_SIZE
        weights = np.asarray(source[:, start:stop], dtype=np.float32)
        packed, scales, zeros = quantize_group(weights, args.mode)
        packets[group, :, :256] = packed.reshape(blocks, 256)
        packets[group, :, 256:272] = scales.reshape(blocks, OUTPUTS_PER_BLOCK).view(np.uint8).reshape(blocks, 16)
        packets[group, :, 272:288] = zeros.reshape(blocks, OUTPUTS_PER_BLOCK).view(np.uint8).reshape(blocks, 16)

        codes = np.empty((vocab, GROUP_SIZE), dtype=np.uint8)
        codes[:, 0::2] = packed & 0x0F
        codes[:, 1::2] = packed >> 4
        restored = (
            codes.astype(np.float32) - zeros.astype(np.float32)[:, None]
        ) * scales.astype(np.float32)[:, None]
        error = restored - weights
        squared_error += float(np.sum(error * error, dtype=np.float64))
        squared_weight += float(np.sum(weights * weights, dtype=np.float64))
        maximum_error = max(maximum_error, float(np.max(np.abs(error))))
        print(json.dumps({"group": group + 1, "groups": groups, "mode": args.mode}))

    packets.flush()
    element_count = vocab * groups * GROUP_SIZE
    metadata = {
        "format": "tellme-w4-gs64-v1",
        "mode": args.mode,
        "vocab_size": vocab,
        "hidden_size": hidden,
        "input_groups": groups,
        "output_blocks": blocks,
        "packet_bytes": PACKET_BYTES,
        "bytes": args.output.stat().st_size,
        "sha256": sha256(args.output),
        "rmse": (squared_error / element_count) ** 0.5,
        "relative_l2": (squared_error / squared_weight) ** 0.5,
        "max_abs": maximum_error,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
