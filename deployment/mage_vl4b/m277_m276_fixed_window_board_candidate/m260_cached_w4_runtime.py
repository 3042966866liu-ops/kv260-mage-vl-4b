#!/usr/bin/env python3
"""Exact packed-code cache for repeated M259 visual review windows."""

from __future__ import annotations

import time

import numpy as np

import m222_vectorized_w4_runtime as _m222v
import ps_vision_runtime as _base
from m259_variable_vision_runtime import M259VariableFramePSVisionRuntime


GROUP_SIZE = 64
ROW_BLOCK = 8
RECORD_BYTES = 272


class M260CachedCodeFourPortW4Store(_m222v.M222VectorizedFourPortW4Store):
    """Cache exact codes/scales/qmin, never a lower-precision weight tensor."""

    def __init__(self, root):
        super().__init__(root)
        self._components = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_bytes = 0
        self.cache_reconstruct_ms = 0.0

    @staticmethod
    def _restore(codes, scales, qmins, rows, columns):
        restored = (codes.astype(np.int16) + qmins[..., None]).astype(np.float32)
        restored *= scales[..., None]
        return restored.reshape(rows, -1)[:, :columns]

    def decode(self, name: str) -> np.ndarray:
        started = time.perf_counter()
        entry = self.entries[name]
        rows, columns = map(int, entry["shape"])
        cached = self._components.get(name)
        if cached is not None:
            codes, scales, qmins = cached
            result = self._restore(codes, scales, qmins, rows, columns)
            elapsed = (time.perf_counter() - started) * 1000.0
            self.cache_hits += 1
            self.cache_reconstruct_ms += elapsed
            self.decode_calls += 1
            self.decode_ms += elapsed
            self.decoded_elements += int(result.size)
            return result

        groups = int(entry["input_groups"])
        if groups * GROUP_SIZE < columns:
            raise RuntimeError(f"M260 invalid input group geometry: {name}")
        codes = np.zeros((rows, groups, GROUP_SIZE), dtype=np.uint8)
        scales = np.zeros((rows, groups), dtype=np.float32)
        qmins = np.full((rows, groups), -8, dtype=np.int8)

        for tile in entry["tiles"]:
            row_start = int(tile["row_start"])
            valid_end = min(rows, row_start + int(tile["valid_rows"]))
            rows_per_shard = int(tile["rows_per_shard"])
            if rows_per_shard % ROW_BLOCK:
                raise RuntimeError(f"M260 rows-per-shard alignment mismatch: {name}")
            blocks = rows_per_shard // ROW_BLOCK
            expected = groups * blocks * RECORD_BYTES
            if int(tile["record_bytes_per_shard"]) != expected:
                raise RuntimeError(f"M260 record geometry mismatch: {name}")
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
                    (groups, blocks, ROW_BLOCK, GROUP_SIZE), dtype=np.uint8
                )
                unpacked[..., 0::2] = packed & np.uint8(0x0F)
                unpacked[..., 1::2] = packed >> np.uint8(4)
                row_codes = unpacked.transpose(1, 2, 0, 3).reshape(
                    rows_per_shard, groups, GROUP_SIZE
                )
                row_tags = tagged.transpose(1, 2, 0).reshape(rows_per_shard, groups)
                shard_base = row_start + shard * rows_per_shard
                take = max(
                    0,
                    min(valid_end, rows, shard_base + rows_per_shard) - shard_base,
                )
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
                ).astype(np.int8)

        self._components[name] = (codes, scales, qmins)
        added = codes.nbytes + scales.nbytes + qmins.nbytes
        self.cache_bytes += int(added)
        self.cache_misses += 1
        result = self._restore(codes, scales, qmins, rows, columns)
        elapsed = (time.perf_counter() - started) * 1000.0
        self.decode_calls += 1
        self.decode_ms += elapsed
        self.decoded_elements += int(result.size)
        return result

    def evidence(self) -> dict:
        value = super().evidence()
        value.update({
            "decoder": "M260-exact-packed-code-cache-v1",
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_entries": len(self._components),
            "cache_bytes": self.cache_bytes,
            "cache_reconstruct_ms": self.cache_reconstruct_ms,
            "cache_precision": "uint8 codes + FP32 scales + int8 qmin",
        })
        return value

    def close(self):
        self._components.clear()
        self.cache_bytes = 0
        super().close()


class M260CachedVariableFramePSVisionRuntime(M259VariableFramePSVisionRuntime):
    """M259 math with process-local exact component caching across windows."""

    def __init__(self, *args, **kwargs):
        original = _m222v.M222VectorizedFourPortW4Store
        _m222v.M222VectorizedFourPortW4Store = M260CachedCodeFourPortW4Store
        try:
            super().__init__(*args, **kwargs)
        finally:
            _m222v.M222VectorizedFourPortW4Store = original

    def decoder_evidence(self) -> dict:
        return self.store.evidence()
