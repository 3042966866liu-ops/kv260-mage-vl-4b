#!/usr/bin/env python3
"""Small self-contained independent reference used by the QKV board diagnostic."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def deterministic_input() -> np.ndarray:
    index = np.arange(32 * 2560, dtype=np.float32).reshape(32, 2560)
    return (np.sin(index * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)


def _half(bits: np.ndarray) -> np.ndarray:
    return np.asarray(bits, dtype="<u2").view("<f2")


def _hls_half(values: np.ndarray) -> np.ndarray:
    """Round to FP16 and reproduce the Vitis half flush-to-zero contract."""
    rounded = np.asarray(values, dtype="<f2")
    bits = rounded.view("<u2")
    subnormal = ((bits & np.uint16(0x7C00)) == 0) & ((bits & np.uint16(0x03FF)) != 0)
    flushed = np.where(subnormal, bits & np.uint16(0x8000), bits).astype("<u2")
    return flushed.view("<f2")


def _decode_w2(record: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tags = np.asarray(record[0], dtype=np.uint8).view("<u2")
    lane = np.arange(64, dtype=np.int32)
    byte_index = lane >> 2
    shifts = ((lane & 3) * 2).astype(np.uint8)
    codes = np.empty((8, 64), dtype=np.int16)
    for pair in range(4):
        for within in range(2):
            raw = record[1 + pair * 2 + within]
            codes[2 * pair + within] = ((raw[byte_index] >> shifts) & 0x3).astype(np.int16)
    qmin = np.where((tags & np.uint16(0x8000)) != 0, -1, -2).astype(np.int16)
    return codes + qmin[:, None], _half(tags & np.uint16(0x7fff))


def reference_descriptor(shards: list[Path], descriptor: dict, chain: dict,
                         codes: np.ndarray, activation_scales: np.ndarray,
                         activation_scale_shift: int = 0,
                         hls_flush_subnormals: bool = False) -> np.ndarray:
    if int(descriptor["bits"]) != 2:
        raise RuntimeError("QKV helper accepts only the expected W2 descriptor")
    groups, rows = int(chain["groups"]), int(descriptor["rows_per_shard"])
    blocks, words = rows // 8, 9
    if rows % 8:
        raise RuntimeError("unaligned rows")
    offset, count = int(descriptor["offset_words"]) * 16, groups * blocks * words * 16
    outputs: list[np.ndarray] = []
    for shard in shards:
        with shard.open("rb", buffering=0) as source:
            source.seek(offset)
            raw = source.read(count)
        if len(raw) != count:
            raise RuntimeError(f"short packed-weight read: {shard}")
        records = np.frombuffer(raw, dtype=np.uint8).reshape(groups, blocks, words, 16)
        output = np.zeros((32, rows), dtype=np.float32 if activation_scale_shift else "<f2")
        for block in range(blocks):
            accumulated = np.zeros((32, 8), dtype="<f2")
            for group in range(groups):
                weights, weight_scales = _decode_w2(records[group, block])
                dots = codes[:, group].astype(np.int32) @ weights.T.astype(np.int32)
                if hls_flush_subnormals:
                    mul1 = _hls_half(_hls_half(dots) * _hls_half(activation_scales[:, group, None]))
                    term = _hls_half(mul1 * _hls_half(weight_scales[None, :]))
                    accumulated = _hls_half(accumulated + term)
                else:
                    term = np.float16(np.float16(dots.astype("<f2") * activation_scales[:, group, None]) * weight_scales[None, :])
                    accumulated = np.float16(accumulated + term)
            value = accumulated
            if activation_scale_shift:
                value = np.ldexp(accumulated.astype(np.float32), -activation_scale_shift)
            output[:, block * 8:(block + 1) * 8] = value
        outputs.append(output)
    return np.concatenate(outputs, axis=1)
