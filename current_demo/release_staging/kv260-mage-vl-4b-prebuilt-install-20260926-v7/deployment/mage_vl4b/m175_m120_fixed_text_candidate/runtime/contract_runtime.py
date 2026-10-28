#!/usr/bin/env python3
"""Pure host-side M89-X packet and output contract (no PYNQ dependency)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


TOKENS = 32
GROUP_SIZE = 64
ACTIVATION_RECORD_BYTES = 80


@dataclass(frozen=True)
class RuntimeContract:
    root: Path
    payload: dict

    @classmethod
    def load(cls, path: Path, expected_status: str) -> "RuntimeContract":
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != expected_status:
            raise RuntimeError(f"contract status mismatch: {payload.get('status')!r}")
        chains = payload.get("chains")
        if not isinstance(chains, list) or not chains:
            raise RuntimeError("contract has no chains")
        for index, chain in enumerate(chains):
            if int(chain["chain_index"]) != index:
                raise RuntimeError("chain order mismatch")
            if int(chain["descriptor_count"]) != len(chain["descriptors"]):
                raise RuntimeError("descriptor count mismatch")
            if int(chain["descriptor_count"]) > 10:
                raise RuntimeError("descriptor count exceeds hardware bound")
        return cls(path.parent, payload)

    @property
    def chains(self) -> list[dict]:
        return self.payload["chains"]


def quantize_t32(values: np.ndarray, groups: int,
                 activation_scale_shift: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(values, dtype=np.float32)
    if x.ndim != 2 or x.shape[0] > TOKENS or x.shape[1] != groups * GROUP_SIZE:
        raise ValueError(f"expected [1..{TOKENS}, {groups * GROUP_SIZE}] activation")
    padded = np.zeros((TOKENS, groups, GROUP_SIZE), dtype=np.float32)
    padded[: x.shape[0]] = x.reshape(x.shape[0], groups, GROUP_SIZE)
    maximum = np.max(np.abs(padded), axis=2)
    scale = (maximum / np.float32(127.0)).astype("<f2")
    safe = np.where(maximum == 0.0, np.float16(1.0), scale).astype("<f2")
    codes = np.clip(np.rint(padded / safe.astype(np.float32)[..., None]), -127, 127).astype(np.int8)
    if not isinstance(activation_scale_shift, int) or not 0 <= activation_scale_shift <= 10:
        raise ValueError("activation_scale_shift must be an integer in [0, 10]")
    transmitted_scale = np.ldexp(safe.astype(np.float32), activation_scale_shift).astype("<f2")
    if not np.isfinite(transmitted_scale).all() or np.any((safe != 0) & (transmitted_scale == 0)):
        raise OverflowError("power-of-two activation scale is outside FP16 range")
    records = np.zeros((groups, TOKENS, ACTIVATION_RECORD_BYTES), dtype=np.uint8)
    records[:, :, :64] = codes.transpose(1, 0, 2).view(np.uint8)
    records[:, :, 64:66] = transmitted_scale.T[..., None].view(np.uint8).reshape(groups, TOKENS, 2)
    return records, codes, transmitted_scale


def pack_chain_input(chain: dict, values: np.ndarray,
                     descriptor_offset_base_words: int = 0,
                     activation_scale_shift: int = 0) -> bytes:
    groups = int(chain["groups"])
    records, _, _ = quantize_t32(values, groups, activation_scale_shift)
    descriptors = bytearray()
    for descriptor in chain["descriptors"]:
        raw = int(descriptor["encoded_u64"], 16)
        offset = raw & 0xFFFFFFFF
        if offset < descriptor_offset_base_words:
            raise RuntimeError("descriptor offset is below staged window base")
        raw = (raw & ~0xFFFFFFFF) | (offset - descriptor_offset_base_words)
        descriptors.extend(raw.to_bytes(8, "little"))
        descriptors.extend(bytes(8))
    payload = bytes(descriptors) + records.tobytes()
    if len(payload) != int(chain["input_bytes"]):
        raise RuntimeError(f"input packet size mismatch: {len(payload)} != {chain['input_bytes']}")
    return payload


def _half_values(raw: memoryview) -> np.ndarray:
    words = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8)
    packed = np.empty((words.shape[0], 2), dtype="<u2")
    packed[:, 0] = words[:, :2].copy().view("<u2").reshape(-1)
    packed[:, 1] = words[:, 4:6].copy().view("<u2").reshape(-1)
    return packed.view("<f2").reshape(words.shape[0], 2).astype(np.float32)


def parse_chain_output(chain: dict, payload: bytes | bytearray | memoryview,
                       output_scale_shift: int = 0) -> dict[str, np.ndarray]:
    if not isinstance(output_scale_shift, int) or not 0 <= output_scale_shift <= 10:
        raise ValueError("output_scale_shift must be an integer in [0, 10]")
    raw = memoryview(payload)
    if len(raw) != int(chain["output_bytes"]):
        raise RuntimeError(f"output packet size mismatch: {len(raw)} != {chain['output_bytes']}")
    result: dict[str, np.ndarray] = {}
    cursor = 0
    for descriptor in chain["descriptors"]:
        size = int(descriptor["output_bytes"])
        values = _half_values(raw[cursor:cursor + size])
        cursor += size
        rows = int(descriptor["rows_per_shard"])
        blocks = rows // 8
        # Hardware order: block, token, shard, pair; each word holds two rows.
        values = values.reshape(blocks, TOKENS, 4, 4, 2)
        assembled = values.transpose(1, 2, 0, 3, 4).reshape(TOKENS, 4 * rows)
        if output_scale_shift:
            assembled = np.ldexp(assembled, -output_scale_shift).astype(np.float32)
        valid = int(descriptor["valid_rows"])
        name = descriptor.get("module", "lm_head")
        start = int(descriptor["row_start"])
        stop = start + valid
        if name not in result:
            result[name] = np.full((TOKENS, stop), np.nan, dtype=np.float32)
        elif result[name].shape[1] < stop:
            grown = np.full((TOKENS, stop), np.nan, dtype=np.float32)
            grown[:, : result[name].shape[1]] = result[name]
            result[name] = grown
        result[name][:, start:stop] = assembled[:, :valid]
    if cursor != len(raw):
        raise RuntimeError("output cursor mismatch")
    return result


def merge_outputs(target: dict[str, np.ndarray], update: dict[str, np.ndarray]) -> None:
    for name, value in update.items():
        if name not in target:
            target[name] = value.copy()
            continue
        if target[name].shape[0] != value.shape[0]:
            raise RuntimeError("token dimension mismatch")
        width = max(target[name].shape[1], value.shape[1])
        merged = np.full((TOKENS, width), np.nan, dtype=np.float32)
        merged[:, : target[name].shape[1]] = target[name]
        incoming = np.isfinite(value)
        prior = np.isfinite(merged[:, : value.shape[1]])
        if np.any(incoming & prior):
            raise RuntimeError(f"overlapping output rows for {name}")
        merged[:, : value.shape[1]][incoming] = value[incoming]
        target[name] = merged


def require_complete(outputs: dict[str, np.ndarray], widths: dict[str, int]) -> None:
    for name, width in widths.items():
        if name not in outputs or outputs[name].shape != (TOKENS, int(width)):
            raise RuntimeError(f"incomplete output shape for {name}")
        if not np.isfinite(outputs[name]).all():
            raise RuntimeError(f"unfilled output rows for {name}")
