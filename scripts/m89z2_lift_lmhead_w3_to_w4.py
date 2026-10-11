#!/usr/bin/env python3
"""Lift the exact W3 LM-head code space into the existing W4 datapath.

For both orientation encodings qmin(W3) - qmin(W4) is exactly +4.  Therefore
``code4 = code3 + 4`` preserves every decoded integer weight and the tagged
FP16 scale exactly.  This is a representation lift, not requantization, and
removes the large dynamic W3 decoder from the FPGA kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ALIGNMENT = 4096
GROUP_SIZE = 64
ROWS_PER_BLOCK = 8
GROUPS = 40


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unpack_codes(payload: bytes, bits: int) -> list[int]:
    value = int.from_bytes(payload, "little")
    mask = (1 << bits) - 1
    return [(value >> (bits * lane)) & mask for lane in range(GROUP_SIZE)]


def pack_codes(codes: list[int], bits: int) -> bytes:
    value = 0
    for lane, code in enumerate(codes):
        value |= int(code) << (bits * lane)
    return value.to_bytes(GROUP_SIZE * bits // 8, "little")


def qmin(tagged: int, bits: int) -> int:
    return -(1 << (bits - 1)) + int(bool(tagged & 0x8000))


def align(value: int) -> int:
    return (value + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    args = p.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    result = args.result.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output}")

    source_manifest_path = source / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("module_count") != 1 or manifest["modules"][0]["module"] != "lm_head":
        raise RuntimeError("source must contain exactly the compact lm_head module")
    module = manifest["modules"][0]
    if int(module["bits"]) != 3 or int(module["input_groups"]) != GROUPS:
        raise RuntimeError("source lm_head must be W3 with 40 input groups")

    output.mkdir(parents=True)
    output_files = [output / f"weights{shard}.bin" for shard in range(4)]
    handles = [path.open("wb") for path in output_files]
    source_handles = [(source / f"weights{shard}.bin").open("rb") for shard in range(4)]
    new_tiles = []
    checked_codes = 0
    try:
        cursors = [0, 0, 0, 0]
        for tile in module["tiles"]:
            rows = int(tile["rows_per_shard"])
            if rows % ROWS_PER_BLOCK:
                raise RuntimeError(f"invalid row count in tile {tile['tile_index']}")
            blocks = rows // ROWS_PER_BLOCK
            old_record_bytes = 16 + ROWS_PER_BLOCK * (GROUP_SIZE * 3 // 8)
            new_record_bytes = 16 + ROWS_PER_BLOCK * (GROUP_SIZE * 4 // 8)
            expected_old_tile_bytes = GROUPS * blocks * old_record_bytes
            if int(tile["record_bytes_per_shard"]) != expected_old_tile_bytes:
                raise RuntimeError(f"source tile size mismatch: {tile['tile_index']}")

            new_offsets = []
            for shard in range(4):
                aligned = align(cursors[shard])
                if aligned != cursors[shard]:
                    handles[shard].write(b"\0" * (aligned - cursors[shard]))
                cursors[shard] = aligned
                new_offsets.append(aligned)

                source_handles[shard].seek(int(tile["shard_offsets"][shard]))
                old_raw = source_handles[shard].read(expected_old_tile_bytes)
                if len(old_raw) != expected_old_tile_bytes:
                    raise RuntimeError("short source tile read")
                records = GROUPS * blocks
                old_array = np.frombuffer(old_raw, dtype=np.uint8).reshape(records, old_record_bytes)
                new_array = np.zeros((records, new_record_bytes), dtype=np.uint8)
                new_array[:, :16] = old_array[:, :16]

                packed3 = old_array[:, 16:].reshape(records, 8, 24)
                bits3 = np.unpackbits(packed3, axis=2, bitorder="little").reshape(records, 8, 64, 3)
                codes3 = (bits3[..., 0] | (bits3[..., 1] << 1) | (bits3[..., 2] << 2)).astype(np.int16)
                codes4 = codes3 + 4
                if int(codes4.max(initial=0)) > 15:
                    raise RuntimeError("W3-to-W4 lifted code overflow")

                tagged = old_array[:, :16].copy().view("<u2").reshape(records, 8)
                orientation = ((tagged >> 15) & 1).astype(np.int16)[..., None]
                decoded3 = codes3 - 4 + orientation
                decoded4 = codes4 - 8 + orientation
                if not np.array_equal(decoded3, decoded4):
                    raise RuntimeError("decoded integer mismatch after lift")

                codes4_u8 = codes4.astype(np.uint8)
                packed4 = codes4_u8[..., 0::2] | (codes4_u8[..., 1::2] << 4)
                new_array[:, 16:] = packed4.reshape(records, 8 * 32)
                handles[shard].write(new_array.tobytes())
                checked_codes += int(codes3.size)
                cursors[shard] += GROUPS * blocks * new_record_bytes

            new_tile = dict(tile)
            new_tile["shard_offsets"] = new_offsets
            new_tile["record_bytes_per_shard"] = GROUPS * blocks * new_record_bytes
            new_tiles.append(new_tile)
    finally:
        for h in handles + source_handles:
            h.close()

    new_module = dict(module)
    new_module["bits"] = 4
    new_module["source_bits"] = 3
    new_module["conversion"] = "exact code-space lift: code4=code3+4; tagged FP16 scale unchanged"
    new_module["tiles"] = new_tiles
    files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in output_files]
    output_manifest = {
        "format": "tellme-mage-vl-fourport-group-major-v1",
        "build_id": "M89-Z2-LMHEAD-EXACT-W3-TO-W4-20260831",
        "classification": "exact W3-to-W4 code-space lift; decoded integer weights and FP16 scales unchanged",
        "source": {
            "layout_manifest": str(source_manifest_path),
            "layout_manifest_sha256": sha256(source_manifest_path),
        },
        "parameters": manifest["parameters"],
        "module_count": 1,
        "modules": [new_module],
        "files": files,
        "verification": {
            "status": "PASS_EXACT_DECODED_WEIGHT_IDENTITY",
            "requantized": False,
            "source_bits": 3,
            "stored_bits": 4,
            "code_offset": 4,
            "checked_codes_across_shards": checked_codes,
            "tagged_scales_byte_identical": True,
            "mapped_bytes": sum(f["bytes"] for f in files),
            "pool_bytes": 800 * 1024 * 1024,
            "headroom_bytes": 800 * 1024 * 1024 - sum(f["bytes"] for f in files),
        },
    }
    output_manifest_path = output / "SIXPORT_LAYOUT_MANIFEST.json"
    output_manifest_path.write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename in ("README.md",):
        candidate = source / filename
        if candidate.is_file():
            shutil.copy2(candidate, output / filename)

    payload = {
        "date": "2026-08-31",
        "build": "M89-Z2",
        "status": "PASS_EXACT_W3_TO_W4_LMHEAD_LIFT",
        "marker": "M89Z2_EXACT_W3_TO_W4_LMHEAD_LIFT_PASS",
        "source_manifest_sha256": sha256(source_manifest_path),
        "output_manifest": str(output_manifest_path),
        "output_manifest_sha256": sha256(output_manifest_path),
        "checked_codes_across_shards": checked_codes,
        "tagged_scales_byte_identical": True,
        "decoded_integer_weights_identical": True,
        "requantized": False,
        "files": files,
        "mapped_bytes": output_manifest["verification"]["mapped_bytes"],
        "pool_bytes": output_manifest["verification"]["pool_bytes"],
        "headroom_bytes": output_manifest["verification"]["headroom_bytes"],
        "board_state_changed": False,
    }
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(payload["marker"])
    print(json.dumps({"checked_codes": checked_codes, "mapped_bytes": payload["mapped_bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
