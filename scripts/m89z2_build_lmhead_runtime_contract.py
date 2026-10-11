#!/usr/bin/env python3
"""Build the exact eight-launch LM-head contract for M89-X."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


MAGIC = b"M89Z2RT\0"
TOKENS, SHARDS, MAX_CHAIN = 32, 4, 10


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--layout", type=Path, required=True)
    p.add_argument("--table", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    args = p.parse_args()
    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("module_count") != 1:
        raise RuntimeError("M89Z2_EXPECTED_ONE_MODULE")
    module = manifest["modules"][0]
    if module.get("module") != "lm_head" or int(module["bits"]) != 4 or int(module.get("source_bits", -1)) != 3:
        raise RuntimeError("M89Z2_LMHEAD_IDENTITY_FAIL")
    groups, bits = int(module["input_groups"]), int(module["bits"])
    files = []
    for item in manifest["files"]:
        path = args.layout / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M89Z2_LAYOUT_FILE_FAIL {path}")
        files.append(path)
    if len(files) != SHARDS:
        raise RuntimeError("M89Z2_EXPECTED_FOUR_SHARDS")

    table = bytearray(MAGIC)
    tiles = module["tiles"]
    chains = []
    total_output = total_macros = total_descriptors = 0
    for chain_index, start in enumerate(range(0, len(tiles), MAX_CHAIN)):
        selected = tiles[start:start + MAX_CHAIN]
        config = groups | (bits << 8) | (len(selected) << 16)
        descriptors = []
        output_words = macros = 0
        for descriptor_index, tile in enumerate(selected):
            offsets = [int(v) for v in tile["shard_offsets"]]
            if len(set(offsets)) != 1 or offsets[0] % 16:
                raise RuntimeError("M89Z2_OFFSET_FAIL")
            rows = int(tile["rows_per_shard"])
            valid = int(tile["valid_rows"])
            offset_words = offsets[0] // 16
            blocks = rows // 8
            end_words = offset_words + groups * blocks * (1 + 4 * bits)
            if rows < 8 or rows > 512 or rows % 8 or any(end_words * 16 > f.stat().st_size for f in files):
                raise RuntimeError("M89Z2_RANGE_FAIL")
            raw = offset_words | (rows << 32) | (bits << 42)
            words64 = blocks * TOKENS * SHARDS * 4
            descriptor_macros = groups * rows * SHARDS * TOKENS
            record = {
                "descriptor_index": descriptor_index,
                "tile_index": int(tile["tile_index"]),
                "row_start": int(tile["row_start"]),
                "rows_per_shard": rows,
                "valid_rows": valid,
                "bits": bits,
                "offset_words": offset_words,
                "encoded_u64": f"0x{raw:016x}",
                "output_words64": words64,
                "output_bytes": words64 * 8,
                "expected_macros": descriptor_macros,
            }
            descriptors.append(record)
            table.extend(struct.pack("<QIIII", raw, record["row_start"], valid, words64, descriptor_macros))
            output_words += words64
            macros += descriptor_macros
        chain = {
            "chain_index": chain_index,
            "groups": groups,
            "bits": bits,
            "descriptor_count": len(selected),
            "config_u32": f"0x{config:08x}",
            "input_words128": len(selected) + groups * TOKENS * 5,
            "input_bytes": (len(selected) + groups * TOKENS * 5) * 16,
            "output_words64": output_words,
            "output_bytes": output_words * 8,
            "expected_macros": macros,
            "descriptors": descriptors,
        }
        chains.append(chain)
        total_output += chain["output_bytes"]
        total_macros += macros
        total_descriptors += len(selected)
    if total_descriptors != 75 or len(chains) != 8:
        raise RuntimeError("M89Z2_CHAIN_CARDINALITY_FAIL")

    header = MAGIC + struct.pack("<IIII", len(chains), total_descriptors, TOKENS, bits)
    args.table.parent.mkdir(parents=True, exist_ok=True)
    args.table.write_bytes(header + table[len(MAGIC):])
    result = {
        "date": "2026-08-31", "build": "M89-Z2",
        "status": "PASS_EXACT_LMHEAD_RUNTIME_CONTRACT",
        "marker": "M89Z2_LMHEAD_8CHAIN_RUNTIME_CONTRACT_PASS",
        "classification": "offline fail-closed contract; exact W3-to-W4 lifted weights; not board execution",
        "source_manifest": manifest_path.as_posix(),
        "source_manifest_sha256": sha256(manifest_path),
        "module": "lm_head", "source_bits": 3, "stored_bits": 4,
        "requantized": False, "groups": groups, "tokens_per_call": TOKENS,
        "tile_descriptors": total_descriptors, "launch_chains": len(chains),
        "total_output_bytes": total_output, "total_expected_macros": total_macros,
        "descriptor_table": {"path": args.table.as_posix(), "bytes": args.table.stat().st_size,
                             "sha256": sha256(args.table), "magic": "M89Z2RT\\0"},
        "chains": chains,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["marker"])
    print(json.dumps({"chains": len(chains), "descriptors": total_descriptors,
                      "output_bytes": total_output, "macros": total_macros}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
