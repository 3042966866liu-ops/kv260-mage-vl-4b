#!/usr/bin/env python3
"""M222 vectorized decoder for the accepted M207 visual W4 runtime.

This changes only how one immutable four-port W4 record is unpacked.  The
layout, FP16 scale interpretation, qmin flag, FP32 reconstruction, GEMM dtype
and M198/M207 precision boundaries remain unchanged.
"""

from __future__ import annotations

import time

import numpy as np

import ps_vision_runtime as _base
from m207_ps_vision_runtime import M207PSVisionRuntime


GROUP_SIZE = 64
ROW_BLOCK = 8
RECORD_BYTES = 272


class M222VectorizedFourPortW4Store(_base.FourPortW4Store):
    """Decode complete shard records with NumPy views instead of Python lanes."""

    def __init__(self, root):
        super().__init__(root)
        self.decode_calls = 0
        self.decode_ms = 0.0
        self.decoded_elements = 0

    def decode(self, name: str) -> np.ndarray:
        started = time.perf_counter()
        entry = self.entries[name]
        rows, columns = map(int, entry["shape"])
        groups = int(entry["input_groups"])
        if groups * GROUP_SIZE < columns:
            raise RuntimeError(f"M222 invalid input group geometry: {name}")

        codes = np.zeros((rows, groups, GROUP_SIZE), dtype=np.int16)
        scales = np.zeros((rows, groups), dtype=np.float32)
        qmins = np.full((rows, groups), -8, dtype=np.int16)

        for tile in entry["tiles"]:
            row_start = int(tile["row_start"])
            valid_end = min(rows, row_start + int(tile["valid_rows"]))
            rows_per_shard = int(tile["rows_per_shard"])
            if rows_per_shard % ROW_BLOCK:
                raise RuntimeError(f"M222 rows-per-shard alignment mismatch: {name}")
            blocks = rows_per_shard // ROW_BLOCK
            expected = groups * blocks * RECORD_BYTES
            if int(tile["record_bytes_per_shard"]) != expected:
                raise RuntimeError(f"M222 record geometry mismatch: {name}")

            for shard, mapping in enumerate(self.maps):
                cursor = int(tile["shard_offsets"][shard])
                raw = np.frombuffer(
                    mapping, dtype=np.uint8, count=expected, offset=cursor
                ).reshape(groups, blocks, RECORD_BYTES)

                tagged = raw[:, :, :16].copy().view("<u2").reshape(
                    groups, blocks, ROW_BLOCK
                )
                packed = raw[:, :, 16:].reshape(
                    groups, blocks, ROW_BLOCK, GROUP_SIZE // 2
                )
                unpacked = np.empty(
                    (groups, blocks, ROW_BLOCK, GROUP_SIZE), dtype=np.int16
                )
                unpacked[..., 0::2] = packed & 0x0F
                unpacked[..., 1::2] = packed >> 4

                # File order is [group, row-block, lane].  The output layout
                # is [row, group], so transpose once and assign a whole shard.
                row_codes = unpacked.transpose(1, 2, 0, 3).reshape(
                    rows_per_shard, groups, GROUP_SIZE
                )
                row_tags = tagged.transpose(1, 2, 0).reshape(
                    rows_per_shard, groups
                )
                shard_base = row_start + shard * rows_per_shard
                take = max(0, min(valid_end, rows, shard_base + rows_per_shard) - shard_base)
                if take == 0:
                    continue
                destination = slice(shard_base, shard_base + take)
                selected_tags = row_tags[:take]
                codes[destination] = row_codes[:take]
                scale_bits = np.bitwise_and(selected_tags, np.uint16(0x7FFF))
                scales[destination] = scale_bits.view(np.float16).astype(np.float32)
                qmins[destination] = np.where(
                    np.bitwise_and(selected_tags, np.uint16(0x8000)) != 0,
                    -7,
                    -8,
                ).astype(np.int16)

        restored = (codes + qmins[..., None]).astype(np.float32)
        restored *= scales[..., None]
        result = restored.reshape(rows, groups * GROUP_SIZE)[:, :columns]
        self.decode_calls += 1
        self.decode_ms += (time.perf_counter() - started) * 1000.0
        self.decoded_elements += int(result.size)
        return result

    def evidence(self) -> dict:
        return {
            "decoder": "M222-vectorized-fourport-w4-v1",
            "decode_calls": self.decode_calls,
            "decode_ms": self.decode_ms,
            "decoded_elements": self.decoded_elements,
        }


class M222PSVisionRuntime(M207PSVisionRuntime):
    """Accepted M207 math with only the W4 record decoder replaced."""

    def __init__(self, *args, **kwargs):
        original_store = _base.FourPortW4Store
        _base.FourPortW4Store = M222VectorizedFourPortW4Store
        try:
            super().__init__(*args, **kwargs)
        finally:
            _base.FourPortW4Store = original_store

    def decoder_evidence(self) -> dict:
        return self.store.evidence()

