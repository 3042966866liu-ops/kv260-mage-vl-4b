#!/usr/bin/env python3
"""Build a compact M89-T fixture from real M56 W2/W4 records."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

MAGIC = b"M89TCHN1"
SHARDS = 4
GROUPS = 3
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
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest_raw = manifest_path.read_bytes()
    layout = json.loads(manifest_raw)
    modules = {m["module"]: m for m in layout["modules"]
               if ".language_model.layers." in m["module"]}
    if len(modules) != 252 or int(layout["parameters"]["shard_count"]) != SHARDS:
        raise RuntimeError("M89-T requires the exact 252-module four-shard M56 layout")

    families = (
        ("qkv", ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj")),
        ("attention_out", ("self_attn.o_proj",)),
        ("gate_up", ("mlp.gate_proj", "mlp.up_proj")),
        ("mlp_down", ("mlp.down_proj",)),
    )
    chains = []
    for layer in range(36):
        prefix = f"model.language_model.layers.{layer}."
        for family, suffixes in families:
            selected = [modules[prefix + suffix] for suffix in suffixes]
            if len({int(m["input_groups"]) for m in selected}) != 1:
                raise RuntimeError(f"activation groups differ in {layer}/{family}")
            if min(int(m["input_groups"]) for m in selected) < GROUPS:
                raise RuntimeError(f"not enough groups in {layer}/{family}")
            if len(selected) > MAX_CHAIN:
                raise RuntimeError("compact module chain exceeds descriptor limit")
            chains.append((layer, family, selected))

    handles = [(args.layout / item["path"]).open("rb") for item in layout["files"]]
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.fixture.open("wb") as output:
            output.write(MAGIC)
            output.write(struct.pack("<III", len(chains), MAX_CHAIN, GROUPS))
            module_total = 0
            for chain_index, (_, _, selected) in enumerate(chains):
                output.write(struct.pack("<II", chain_index, len(selected)))
                for local, module in enumerate(selected):
                    module_total += 1
                    bits = int(module["bits"])
                    words = 1 + 4 * bits
                    tile = module["tiles"][(chain_index + local) % len(module["tiles"])]
                    blocks = int(tile["rows_per_shard"]) // 8
                    block = (chain_index * 7 + local * 3 + 1) % blocks
                    group_count = int(module["input_groups"])
                    group_ids = [
                        (chain_index * 13 + local * 5 + 1 + k * 17) % group_count
                        for k in range(GROUPS)
                    ]
                    if len(set(group_ids)) != GROUPS:
                        raise RuntimeError("fixture group selection collided")
                    output.write(struct.pack("<BBBB", bits, words, GROUPS, 0))
                    for shard, handle in enumerate(handles):
                        for group in group_ids:
                            offset = int(tile["shard_offsets"][shard]) + \
                                     (group * blocks + block) * words * 16
                            handle.seek(offset)
                            payload = handle.read(words * 16)
                            if len(payload) != words * 16:
                                raise RuntimeError("short real M56 record")
                            output.write(payload)
                            output.write(bytes((MAX_WORDS - words) * 16))
    finally:
        for handle in handles:
            handle.close()

    if len(chains) != 144 or module_total != 252:
        raise RuntimeError("unexpected M56 compact fixture cardinality")
    result = {
        "date": "2026-08-30",
        "build": "M89-T",
        "status": "PASS_REAL_M56_SCALE_CHAIN_FIXTURE_BUILT",
        "scope": "compact real M56 scale-record fixture; CSim and HLS remain separate gates",
        "layout_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "chain_count": len(chains),
        "language_module_count": module_total,
        "groups_per_module": GROUPS,
        "real_weight_records": module_total * SHARDS * GROUPS,
        "fixture": args.fixture.as_posix(),
        "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
