#!/usr/bin/env python3
"""Fail-closed real-M56 W2/W4 record gate for the T32 descriptor path.

This is deliberately a *data* gate before HLS integration.  It reads the
hash-locked M56 source and the derived six-port runtime records, then makes a
32-token integer dot product from both representations.  Thus a passing run
proves that the exact W2/W4 record contract, orientation bit and packed-code
order are suitable for the planned weight-stationary T32 kernel; it does not
claim that an HLS implementation, full model, board or performance gate has
passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import struct
from pathlib import Path


GROUP_SIZE = 64
TOKEN_LANES = 32
SHARDS = 6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_codes(payload: bytes, bits: int) -> list[int]:
    if len(payload) != GROUP_SIZE * bits // 8:
        raise RuntimeError(f"invalid code payload length {len(payload)} for W{bits}")
    mask = (1 << bits) - 1
    return [(payload[(lane * bits) >> 3] >> ((lane * bits) & 7)) & mask for lane in range(GROUP_SIZE)]


def qmin(bits: int, tagged_scale: int) -> int:
    half = 1 << (bits - 1)
    return -half + 1 if tagged_scale & 0x8000 else -half


def source_record(blob: bytes, entry: dict, row: int, group: int) -> tuple[int, bytes]:
    groups = int(entry["padded_columns"]) // GROUP_SIZE
    linear = row * groups + group
    scale = struct.unpack_from("<H", blob, int(entry["sections"]["scales"]["offset"]) + 2 * linear)[0]
    orient_offset = int(entry["sections"]["orientations"]["offset"]) + linear // 8
    orientation = (blob[orient_offset] >> (linear & 7)) & 1
    bits = int(entry["bits"])
    code_bytes = GROUP_SIZE * bits // 8
    code_offset = int(entry["sections"]["codes"]["offset"]) + linear * code_bytes
    return scale | (orientation << 15), blob[code_offset:code_offset + code_bytes]


def record_from_sixport(handle, module: dict, tile: dict, shard: int, group: int, block: int) -> tuple[list[int], list[bytes]]:
    bits = int(module["bits"])
    words_per_record = 1 + 4 * bits
    record_bytes = words_per_record * 16
    blocks = int(tile["rows_per_shard"]) // 8
    offset = int(tile["shard_offsets"][shard]) + (group * blocks + block) * record_bytes
    handle.seek(offset)
    payload = handle.read(record_bytes)
    if len(payload) != record_bytes:
        raise RuntimeError(f"short six-port record at offset {offset}")
    tagged = list(struct.unpack("<8H", payload[:16]))
    code_bytes = GROUP_SIZE * bits // 8
    codes = [payload[16 + pair * 2 * code_bytes + lane * code_bytes:16 + pair * 2 * code_bytes + (lane + 1) * code_bytes]
             for pair in range(4) for lane in range(2)]
    return tagged, codes


def selected_tiles(tiles: list[dict]) -> list[dict]:
    indexes = sorted({0, len(tiles) // 2, len(tiles) - 1})
    return [tiles[index] for index in indexes]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0x4D38394D)
    args = parser.parse_args()

    source_manifest_path = args.source / "CHECKPOINT_MANIFEST.json"
    source_manifest_raw = source_manifest_path.read_bytes()
    source_manifest = json.loads(source_manifest_raw)
    blob_path = args.source / "weights.bin"
    if sha256(blob_path) != source_manifest["blob"]["sha256"]:
        raise RuntimeError("M56 source blob hash mismatch")
    blob = blob_path.read_bytes()
    layout_manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    layout_manifest_raw = layout_manifest_path.read_bytes()
    layout = json.loads(layout_manifest_raw)
    if layout["source"]["blob_sha256"] != source_manifest["blob"]["sha256"]:
        raise RuntimeError("six-port layout source hash does not match M56")

    entries = {entry["module"]: entry for entry in source_manifest["entries"] if entry.get("kind") == "packed" and ".language_model.layers." in entry["module"]}
    modules = [module for module in layout["modules"] if module["module"] in entries]
    if len(entries) != 252 or len(modules) != 252:
        raise RuntimeError(f"expected 252 language descriptors, got source={len(entries)} layout={len(modules)}")
    files = [(args.layout / item["path"]).open("rb") for item in layout["files"]]
    if len(files) != SHARDS:
        raise RuntimeError("six-port layout does not contain six files")

    rng = random.Random(args.seed)
    checks = 0
    bit_counts = {"W2": 0, "W4": 0}
    try:
        for module in modules:
            entry = entries[module["module"]]
            bits = int(module["bits"])
            if bits not in (2, 4):
                raise RuntimeError(f"unexpected language bit width W{bits}: {module['module']}")
            groups = int(module["input_groups"])
            code_bytes = GROUP_SIZE * bits // 8
            activations = [[rng.randint(-127, 127) for _ in range(GROUP_SIZE)] for _ in range(TOKEN_LANES)]
            for tile in selected_tiles(module["tiles"]):
                blocks = int(tile["rows_per_shard"]) // 8
                for group in sorted({0, groups // 2, groups - 1}):
                    for shard in (0, SHARDS - 1):
                        for block in sorted({0, blocks // 2, blocks - 1}):
                            tagged, records = record_from_sixport(files[shard], module, tile, shard, group, block)
                            for lane in range(8):
                                row = int(tile["row_start"]) + shard * int(tile["rows_per_shard"]) + block * 8 + lane
                                valid = row < int(tile["row_start"]) + int(tile["valid_rows"]) and row < int(entry["shape"][0])
                                got_codes = records[lane]
                                if not valid:
                                    if tagged[lane] != 0 or got_codes != bytes(code_bytes):
                                        raise RuntimeError(f"nonzero padding in {module['module']}")
                                    continue
                                expected_tagged, expected_codes = source_record(blob, entry, row, group)
                                if tagged[lane] != expected_tagged or got_codes != expected_codes:
                                    raise RuntimeError(f"real record mismatch: {module['module']} row={row} group={group}")
                                decoded_layout = [value + qmin(bits, tagged[lane]) for value in decode_codes(got_codes, bits)]
                                decoded_source = [value + qmin(bits, expected_tagged) for value in decode_codes(expected_codes, bits)]
                                if decoded_layout != decoded_source:
                                    raise RuntimeError(f"decode mismatch: {module['module']} row={row} group={group}")
                                for token in activations:
                                    if sum(a * w for a, w in zip(token, decoded_layout)) != sum(a * w for a, w in zip(token, decoded_source)):
                                        raise RuntimeError(f"T32 dot mismatch: {module['module']} row={row} group={group}")
                                checks += 1
                                bit_counts[f"W{bits}"] += 1
    finally:
        for handle in files:
            handle.close()

    result = {
        "build": "M89-M",
        "status": "PASS_REAL_M56_W2_W4_SIXPORT_RECORD_T32_NUMERICAL_GATE",
        "scope": "offline data/numerical gate only; not HLS synthesis, full 4B E2E, board deployment or performance evidence",
        "source_manifest_sha256": hashlib.sha256(source_manifest_raw).hexdigest(),
        "source_blob_sha256": source_manifest["blob"]["sha256"],
        "sixport_manifest_sha256": hashlib.sha256(layout_manifest_raw).hexdigest(),
        "language_descriptors": len(modules),
        "token_lanes": TOKEN_LANES,
        "record_rows_checked": checks,
        "bit_counts": bit_counts,
        "coverage": "first/middle/last tile, group and block; first/last shard; all eight rows; 32 deterministic int8 activations per checked real record",
        "next_gate": "Implement this identical W2/W4 record decoder in the descriptor-chained HLS top and run CSim before synthesis.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
