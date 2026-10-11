#!/usr/bin/env python3
"""Build the exact M56 tile schedule and compact real-record chain fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

MAGIC = b"M89RCHN1"
SHARDS = 4
MAX_WORDS = 17
MAX_CHAIN = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    raw = manifest_path.read_bytes()
    layout = json.loads(raw)
    modules = {m["module"]: m for m in layout["modules"] if ".language_model.layers." in m["module"]}
    if len(modules) != 252 or int(layout["parameters"]["shard_count"]) != SHARDS:
        raise RuntimeError("expected exact 252-module, four-shard M56 language layout")

    chains = []
    compact_specs = []
    families = (
        ("qkv", ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj")),
        ("attention_out", ("self_attn.o_proj",)),
        ("gate_up", ("mlp.gate_proj", "mlp.up_proj")),
        ("mlp_down", ("mlp.down_proj",)),
    )
    for layer in range(36):
        prefix = f"model.language_model.layers.{layer}."
        for family, suffixes in families:
            selected = [modules[prefix + suffix] for suffix in suffixes]
            groups = {int(m["input_groups"]) for m in selected}
            if len(groups) != 1:
                raise RuntimeError(f"shared-activation group mismatch in layer {layer} {family}")
            descriptors = []
            for module in selected:
                for tile in module["tiles"]:
                    offsets = [int(value) for value in tile["shard_offsets"]]
                    if len(set(offsets)) != 1 or offsets[0] % 16:
                        raise RuntimeError(f"non-shared/aligned four-port offset in {module['module']}")
                    descriptors.append({
                        "module": module["module"],
                        "tile_index": int(tile["tile_index"]),
                        "offset_words": offsets[0] // 16,
                        "rows_per_shard": int(tile["rows_per_shard"]),
                        "valid_rows": int(tile["valid_rows"]),
                        "bits": int(module["bits"]),
                    })
                compact_specs.append(module)
            if len(descriptors) > MAX_CHAIN:
                raise RuntimeError(f"chain {layer}/{family} exceeds {MAX_CHAIN} descriptors")
            chains.append({
                "chain_index": len(chains),
                "layer": layer,
                "family": family,
                "input_groups": groups.pop(),
                "descriptor_count": len(descriptors),
                "descriptors": descriptors,
            })

    if len(chains) != 144 or sum(c["descriptor_count"] for c in chains) != 648:
        raise RuntimeError("unexpected full tile-chain schedule cardinality")
    if len(compact_specs) != 252:
        raise RuntimeError("compact fixture does not cover 252 modules exactly once")

    handles = [(args.layout / f["path"]).open("rb") for f in layout["files"]]
    compact_records = []
    try:
        cursor = 0
        for chain in chains:
            chain_records = []
            module_count = {"qkv": 3, "attention_out": 1, "gate_up": 2, "mlp_down": 1}[chain["family"]]
            for local in range(module_count):
                module = compact_specs[cursor]
                cursor += 1
                bits = int(module["bits"])
                words = 1 + 4 * bits
                tile = module["tiles"][(chain["chain_index"] + local) % len(module["tiles"])]
                groups = int(module["input_groups"])
                blocks = int(tile["rows_per_shard"]) // 8
                group = (chain["chain_index"] * 13 + local * 5 + 1) % groups
                block = (chain["chain_index"] * 7 + local * 3 + 1) % blocks
                record = bytearray(struct.pack("<BBH", bits, words, 0))
                for shard, handle in enumerate(handles):
                    offset = int(tile["shard_offsets"][shard]) + (group * blocks + block) * words * 16
                    handle.seek(offset)
                    payload = handle.read(words * 16)
                    if len(payload) != words * 16:
                        raise RuntimeError("short compact real record")
                    record.extend(payload)
                    record.extend(bytes((MAX_WORDS - words) * 16))
                chain_records.append(bytes(record))
            compact_records.append(chain_records)
    finally:
        for handle in handles:
            handle.close()

    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    with args.fixture.open("wb") as output:
        output.write(MAGIC)
        output.write(struct.pack("<II", len(compact_records), MAX_CHAIN))
        for chain_index, records in enumerate(compact_records):
            output.write(struct.pack("<II", chain_index, len(records)))
            for record in records:
                output.write(record)

    result = {
        "date": "2026-08-30",
        "build": "M89-R",
        "status": "PASS_FULL_M56_DESCRIPTOR_CHAIN_SCHEDULE_AND_FIXTURE_BUILT",
        "scope": "offline descriptor schedule and compact real-record fixture; HLS CSim/synthesis are separate gates",
        "layout_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "chain_count": len(chains),
        "tile_descriptor_count": sum(c["descriptor_count"] for c in chains),
        "language_module_count": len(compact_specs),
        "max_chain_descriptors": max(c["descriptor_count"] for c in chains),
        "family_chain_counts": {family: 36 for family, _ in families},
        "family_tile_descriptors_per_layer": {"qkv": 4, "attention_out": 2, "gate_up": 10, "mlp_down": 2},
        "fixture": args.fixture.as_posix(),
        "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture),
        "chains": chains,
    }
    args.schedule.parent.mkdir(parents=True, exist_ok=True)
    args.schedule.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "chains"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
