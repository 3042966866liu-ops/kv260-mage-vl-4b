#!/usr/bin/env python3
"""Build the M89-V all-group fixture from official hidden states and M56."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


SHARDS = 4
TOKENS = 32
VALID_TOKENS = 30
MAX_WORDS = 17
MAX_CHAIN = 10
FAMILIES = (
    ("qkv", ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj")),
    ("attention_out", ("self_attn.o_proj",)),
    ("gate_up", ("mlp.gate_proj", "mlp.up_proj")),
    ("mlp_down", ("mlp.down_proj",)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantize(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    grouped = np.asarray(values, dtype=np.float32).reshape(values.shape[0], -1, 64)
    maximum = np.max(np.abs(grouped), axis=2)
    scale = (maximum / np.float32(127.0)).astype("<f2")
    safe = np.where(maximum == 0, np.float16(1), scale).astype("<f2")
    codes = np.clip(
        np.rint(grouped / safe.astype(np.float32)[..., None]), -127, 127
    ).astype(np.int8)
    return codes, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--hidden", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--all-chains", action="store_true",
                        help="emit all 36 layers x four families for M89-W")
    args = parser.parse_args()

    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest_raw = manifest_path.read_bytes()
    layout = json.loads(manifest_raw)
    modules = {
        item["module"]: item
        for item in layout["modules"]
        if ".language_model.layers." in item["module"]
    }
    if len(modules) != 252 or int(layout["parameters"]["shard_count"]) != SHARDS:
        raise RuntimeError("M89V_LAYOUT_IDENTITY_FAIL")
    if sha256(args.hidden) != "e1bc0534a107a63728b9d9d4e8c717a29396f9f046906beb9163ca75aeae3e99":
        raise RuntimeError("M89V_HIDDEN_CAPTURE_HASH_FAIL")

    hidden = np.load(args.hidden, allow_pickle=False)
    selected = []
    if args.all_chains:
        for layer in range(36):
            for family_code, (family, suffixes) in enumerate(FAMILIES):
                chain = [modules[f"model.language_model.layers.{layer}.{suffix}"]
                         for suffix in suffixes]
                selected.append((layer, family_code, family, chain))
    else:
        for target_bits in (2, 4):
            for family_code, (family, suffixes) in enumerate(FAMILIES):
                found = None
                for layer in range(36):
                    chain = [modules[f"model.language_model.layers.{layer}.{suffix}"]
                             for suffix in suffixes]
                    if all(int(module["bits"]) == target_bits for module in chain):
                        found = (layer, family_code, family, chain)
                        break
                if found is None:
                    raise RuntimeError(
                        f"M89V_NO_CHAIN family={family} bits={target_bits}"
                    )
                selected.append(found)

    magic = b"M89WALL1" if args.all_chains else b"M89VALL1"
    build = "M89-W" if args.all_chains else "M89-V"

    handles = [(args.layout / item["path"]).open("rb") for item in layout["files"]]
    summaries = []
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.fixture.open("wb") as output:
            output.write(magic)
            output.write(struct.pack("<IIII", len(selected), MAX_CHAIN, TOKENS,
                                     VALID_TOKENS))
            for chain_id, (layer, family_code, family, chain) in enumerate(selected):
                groups = int(chain[0]["input_groups"])
                bits = int(chain[0]["bits"])
                if any(int(item["input_groups"]) != groups or
                       int(item["bits"]) != bits for item in chain):
                    raise RuntimeError("M89V_CHAIN_GEOMETRY_FAIL")
                values = hidden[f"layer{layer:02d}_{family}"]
                if values.shape != (VALID_TOKENS, groups * 64):
                    raise RuntimeError(
                        f"M89V_HIDDEN_GEOMETRY_FAIL family={family} shape={values.shape}"
                    )
                codes, scales = quantize(values)
                output.write(struct.pack("<IIIIII", chain_id, layer, family_code,
                                         len(chain), groups, bits))

                for local, module in enumerate(chain):
                    words = 1 + 4 * bits
                    tile = module["tiles"][(chain_id + local) % len(module["tiles"])]
                    blocks = int(tile["rows_per_shard"]) // 8
                    block = (chain_id * 7 + local * 3 + 1) % blocks
                    output.write(struct.pack("<BBBBI", bits, words, groups, 0, block))
                    for shard, handle in enumerate(handles):
                        for group in range(groups):
                            offset = int(tile["shard_offsets"][shard]) + \
                                (group * blocks + block) * words * 16
                            handle.seek(offset)
                            payload = handle.read(words * 16)
                            if len(payload) != words * 16:
                                raise RuntimeError("M89V_SHORT_WEIGHT_RECORD")
                            output.write(payload)
                            output.write(bytes((MAX_WORDS - words) * 16))

                for group in range(groups):
                    for token in range(TOKENS):
                        if token < VALID_TOKENS:
                            token_codes = codes[token, group]
                            token_scale = scales[token, group]
                        else:
                            token_codes = np.zeros(64, dtype=np.int8)
                            token_scale = np.float16(1)
                        output.write(token_codes.tobytes())
                        output.write(np.asarray(token_scale, dtype="<f2").tobytes())
                        output.write(bytes(14))

                summaries.append({
                    "chain_id": chain_id,
                    "layer": layer,
                    "family": family,
                    "bits": bits,
                    "groups": groups,
                    "descriptors": [item["module"] for item in chain],
                    "hidden_key": f"layer{layer:02d}_{family}",
                })
    finally:
        for handle in handles:
            handle.close()
        hidden.close()

    result = {
        "date": "2026-08-30",
        "build": build,
        "status": "PASS_REAL_HIDDEN_ALLGROUP_FIXTURE_BUILT",
        "classification": "offline exact fixture; CSim remains a separate gate",
        "layout_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "hidden_capture_sha256": sha256(args.hidden),
        "chain_count": len(summaries),
        "descriptor_count": sum(len(item["descriptors"]) for item in summaries),
        "bitwidths": [2, 4],
        "families": [item[0] for item in FAMILIES],
        "tokens": TOKENS,
        "valid_tokens": VALID_TOKENS,
        "padded_tokens": TOKENS - VALID_TOKENS,
        "chains": summaries,
        "fixture": args.fixture.as_posix(),
        "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    print(f"{build.replace('-', '')}_REAL_HIDDEN_ALLGROUP_FIXTURE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
