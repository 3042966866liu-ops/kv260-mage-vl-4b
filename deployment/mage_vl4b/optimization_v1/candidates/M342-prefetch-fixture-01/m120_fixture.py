#!/usr/bin/env python3
"""Parse M128 real-record fixture and build exact M89X2 packets/references."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


MAGIC = b"M128CSM1"
MAX_WORDS = 17
TOKENS = 32


@dataclass
class Descriptor:
    bits: int
    words: int
    groups: int
    block: int
    shard_records: list[bytes]


@dataclass
class Case:
    ordinal: int
    layer: int
    family: int
    groups: int
    bits: int
    descriptors: list[Descriptor]
    activation: bytes


def load_fixture(path: Path) -> list[Case]:
    data = memoryview(Path(path).read_bytes())
    cursor = 0

    def take(count: int) -> bytes:
        nonlocal cursor
        if cursor + count > len(data):
            raise RuntimeError("fixture truncated")
        value = bytes(data[cursor:cursor + count])
        cursor += count
        return value

    if take(8) != MAGIC:
        raise RuntimeError("fixture magic mismatch")
    chain_count, max_chain, tokens, valid_tokens = struct.unpack("<IIII", take(16))
    if (chain_count, max_chain, tokens, valid_tokens) != (7, 10, 32, 30):
        raise RuntimeError("fixture header mismatch")
    cases: list[Case] = []
    for expected_ordinal in range(chain_count):
        ordinal, layer, family, count, groups, bits = struct.unpack("<IIIIII", take(24))
        if ordinal != expected_ordinal or not (1 <= count <= 10):
            raise RuntimeError("fixture chain header mismatch")
        descriptors: list[Descriptor] = []
        for _ in range(count):
            d_bits, words, d_groups, _reserved, block = struct.unpack("<BBBBI", take(8))
            if d_bits != bits or words != 1 + 4 * bits or d_groups != groups:
                raise RuntimeError("fixture descriptor header mismatch")
            shards = []
            for _shard in range(4):
                shards.append(take(groups * MAX_WORDS * 16))
            descriptors.append(Descriptor(d_bits, words, d_groups, block, shards))
        activation = take(groups * TOKENS * 80)
        cases.append(Case(ordinal, layer, family, groups, bits, descriptors, activation))
    if cursor != len(data):
        raise RuntimeError("fixture trailing bytes")
    return cases


def _scale(bits: np.ndarray) -> np.ndarray:
    return np.asarray(bits, dtype="<u2").view("<f2").astype(np.float32)


def _decode_weights(record: np.ndarray, bits: int) -> tuple[np.ndarray, np.ndarray]:
    tags = np.frombuffer(record[0].tobytes(), dtype="<u2", count=8)
    result = np.empty((8, 64), dtype=np.int16)
    for row in range(8):
        pair, which = divmod(row, 2)
        if bits == 2:
            word = record[1 + pair * 2 + which]
            lane = np.arange(64, dtype=np.int32)
            result[row] = ((word[lane >> 2] >> ((lane & 3) * 2)) & 3).astype(np.int16)
            result[row] += -1 if (int(tags[row]) & 0x8000) else -2
        else:
            lane = np.arange(64, dtype=np.int32)
            low = record[1 + pair * 4 + which * 2]
            high = record[1 + pair * 4 + which * 2 + 1]
            packed = np.concatenate((low, high))
            result[row] = ((packed[lane >> 1] >> ((lane & 1) * 4)) & 15).astype(np.int16)
            result[row] += -7 if (int(tags[row]) & 0x8000) else -8
    return result, _scale(tags & np.uint16(0x7FFF))


def build_case(case: Case, descriptor_count: int) -> dict[str, object]:
    if descriptor_count < 1 or descriptor_count > len(case.descriptors):
        raise ValueError("invalid descriptor_count")
    selected = case.descriptors[:descriptor_count]
    shard_payloads = [bytearray() for _ in range(4)]
    descriptor_words = bytearray()
    expected_words: list[bytes] = []
    activation = np.frombuffer(case.activation, dtype=np.uint8).reshape(case.groups, TOKENS, 80)
    activation_codes = activation[:, :, :64].copy().view(np.int8)
    activation_scales = _scale(activation[:, :, 64:66].copy().view("<u2").reshape(case.groups, TOKENS))
    offset_words = 0
    for descriptor in selected:
        raw = offset_words | (8 << 32) | (case.bits << 42)
        descriptor_words.extend(raw.to_bytes(8, "little"))
        descriptor_words.extend(bytes(8))
        per_shard_expected: list[np.ndarray] = []
        for shard in range(4):
            padded = np.frombuffer(descriptor.shard_records[shard], dtype=np.uint8).reshape(
                case.groups, MAX_WORDS, 16
            )
            compact = padded[:, :descriptor.words].copy()
            shard_payloads[shard].extend(compact.tobytes())
            accumulated = np.zeros((TOKENS, 8), dtype=np.float32)
            for group in range(case.groups):
                weights, weight_scales = _decode_weights(compact[group], case.bits)
                dots = activation_codes[group].astype(np.int32) @ weights.T.astype(np.int32)
                term = (
                    dots.astype(np.float32)
                    * activation_scales[group, :, None]
                    * weight_scales[None, :]
                ).astype(np.float32)
                accumulated = (accumulated + term).astype(np.float32)
            per_shard_expected.append(accumulated.astype("<f2"))
        for token in range(TOKENS):
            for shard in range(4):
                bits16 = per_shard_expected[shard][token].view("<u2")
                for pair in range(4):
                    word = bytearray(8)
                    word[0:2] = int(bits16[2 * pair]).to_bytes(2, "little")
                    word[4:6] = int(bits16[2 * pair + 1]).to_bytes(2, "little")
                    expected_words.append(bytes(word))
        offset_words += case.groups * descriptor.words
    packet = bytes(descriptor_words) + case.activation
    expected = b"".join(expected_words)
    return {
        "weights": [bytes(value) for value in shard_payloads],
        "packet": packet,
        "expected": expected,
        "output_bytes": len(expected),
        "config": case.groups | (case.bits << 8) | (descriptor_count << 16),
        "identity": (
            f"fixture-ordinal{case.ordinal}-layer{case.layer}-family{case.family}-"
            f"bits{case.bits}-groups{case.groups}-descriptors{descriptor_count}"
        ),
    }
