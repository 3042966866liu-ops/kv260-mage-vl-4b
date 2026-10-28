"""Pure candidate ABI; no PYNQ import, allocation, or deployment entry point."""
from __future__ import annotations

import copy
import numpy as np

ABI = "m455-dense-fp16-block-token-shard-pair-v1"
BUILD_ID = 0x4D343535


def dense_contract(original: dict) -> dict:
    """Derive an independent contract; never mutate an accepted runtime table."""
    result = copy.deepcopy(original)
    descriptors = result["descriptors"]
    if result["descriptor_count"] != len(descriptors) or not 1 <= len(descriptors) <= 10:
        raise ValueError("Invalid descriptor count")
    total = 0
    for d in descriptors:
        rows = d["rows_per_shard"]
        if type(rows) is not int or not 8 <= rows <= 512 or rows % 8:
            raise ValueError("Invalid shard rows")
        expected = rows * 4 * 32 * 4
        if d["output_bytes"] != expected:
            raise ValueError("Original output geometry differs")
        d["output_bytes"] = expected // 2
        total += d["output_bytes"]
    if original["output_bytes"] != total * 2:
        raise ValueError("Original output total differs")
    result.update(output_bytes=total, output_abi=ABI, expected_build_id=BUILD_ID)
    return result


def parse_dense_output(chain: dict, payload, output_scale_shift: int = 0) -> dict:
    """FP16 decoding and assembly with the original rounding/shift boundaries."""
    if chain.get("output_abi") != ABI or chain.get("expected_build_id") != BUILD_ID:
        raise ValueError("Dense ABI identity required")
    if type(output_scale_shift) is not int or not 0 <= output_scale_shift <= 10:
        raise ValueError("Invalid output shift")
    raw = memoryview(payload).cast("B")
    if raw.nbytes != chain["output_bytes"]:
        raise ValueError("Dense payload size differs")
    results, cursor = {}, 0
    for d in chain["descriptors"]:
        rows, size = d["rows_per_shard"], d["output_bytes"]
        if size != rows * 4 * 32 * 2:
            raise ValueError("Dense descriptor geometry differs")
        values = np.frombuffer(raw[cursor:cursor + size], dtype="<f2").astype(np.float32)
        cursor += size
        values = values.reshape(rows // 8, 32, 4, 4, 2)
        assembled = values.transpose(1, 2, 0, 3, 4).reshape(32, rows * 4)
        if output_scale_shift:
            assembled = np.ldexp(assembled, -output_scale_shift).astype(np.float32)
        name = d.get("module", "lm_head")
        start, valid = d["row_start"], d["valid_rows"]
        if type(start) is not int or start < 0 or type(valid) is not int or not 1 <= valid <= 4 * rows:
            raise ValueError("Invalid output slice")
        stop = start + valid
        prior = results.get(name)
        if prior is None:
            prior = np.full((32, stop), np.nan, np.float32)
        elif prior.shape[1] < stop:
            grown = np.full((32, stop), np.nan, np.float32)
            grown[:, :prior.shape[1]] = prior
            prior = grown
        prior[:, start:stop] = assembled[:, :valid]
        results[name] = prior
    if cursor != raw.nbytes:
        raise ValueError("Dense cursor differs")
    return results


def compact_reference(original: bytes) -> bytes:
    """Bit extraction oracle only; not a proposed timed runtime conversion."""
    words = np.frombuffer(original, dtype="<u2").reshape(-1, 4)
    if len(words) % 2 or np.any(words[:, (1, 3)]):
        raise ValueError("Original reserved bits or word alignment differ")
    return words[:, (0, 2)].copy().tobytes()
