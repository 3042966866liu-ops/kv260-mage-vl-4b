#!/usr/bin/env python3
"""Fail-closed capacity and chain plan for the frozen M120 checkpoint.

This gate does not write a DDR layout.  It derives the exact four-port byte
count from the canonical layout rules and proves whether the selected mixed
precision policy can reuse the existing homogeneous W2/W4 M89-X2 kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path


EXPECTED_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
EXPECTED_BLOB_BYTES = 2_380_646_272
HIGH_RESERVED_BYTES = 1_744_830_464
LOW_CMA_BYTES = 800 * 1024 * 1024
SHARDS = 4
GROUP_SIZE = 64
ROW_BLOCK = 8
MIN_ROWS_PER_SHARD = 16
MAX_ROWS_PER_SHARD = 512
ALIGNMENT = 4096
LANGUAGE_PREFIX = "model.language_model.layers."


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def align_up(value: int, alignment: int = ALIGNMENT) -> int:
    return (value + alignment - 1) // alignment * alignment


def tiles(rows: int) -> list[dict[str, int]]:
    result = []
    row_start = 0
    while row_start < rows:
        valid_rows = min(rows - row_start, SHARDS * MAX_ROWS_PER_SHARD)
        rows_per_shard = max(
            MIN_ROWS_PER_SHARD,
            align_up(math.ceil(valid_rows / SHARDS), ROW_BLOCK),
        )
        if rows_per_shard > MAX_ROWS_PER_SHARD:
            raise RuntimeError("M124_ROWS_PER_SHARD_OVERFLOW")
        result.append(
            {
                "row_start": row_start,
                "valid_rows": valid_rows,
                "rows_per_shard": rows_per_shard,
            }
        )
        row_start += valid_rows
    return result


def plan_layout(entries: list[dict]) -> dict:
    cursor = 0
    descriptor_count = 0
    max_record_bytes_per_shard = 0
    max_staged_window_bytes_all_shards = 0
    modules = []
    for entry in entries:
        bits = int(entry["bits"])
        if bits not in (2, 4):
            raise RuntimeError(f"M124_KERNEL_BIT_WIDTH_UNSUPPORTED module={entry['module']} bits={bits}")
        if int(entry["group_size"]) != GROUP_SIZE:
            raise RuntimeError(f"M124_GROUP_SIZE_UNSUPPORTED module={entry['module']}")
        groups = int(entry["padded_columns"]) // GROUP_SIZE
        module_tiles = []
        for tile_index, tile in enumerate(tiles(int(entry["shape"][0]))):
            cursor = align_up(cursor)
            record_bytes = (
                groups
                * (int(tile["rows_per_shard"]) // ROW_BLOCK)
                * (1 + 4 * bits)
                * 16
            )
            module_tiles.append(
                {
                    "tile_index": tile_index,
                    **tile,
                    "offset_bytes_per_shard": cursor,
                    "record_bytes_per_shard": record_bytes,
                }
            )
            cursor += record_bytes
            descriptor_count += 1
            max_record_bytes_per_shard = max(max_record_bytes_per_shard, record_bytes)
            max_staged_window_bytes_all_shards = max(
                max_staged_window_bytes_all_shards, record_bytes * SHARDS
            )
        modules.append(
            {
                "module": entry["module"],
                "bits": bits,
                "input_groups": groups,
                "tile_count": len(module_tiles),
                "tiles": module_tiles,
            }
        )
    return {
        "module_count": len(modules),
        "descriptor_count": descriptor_count,
        "bytes_per_shard": cursor,
        "mapped_bytes_all_shards": cursor * SHARDS,
        "max_record_bytes_per_shard": max_record_bytes_per_shard,
        "max_staged_window_bytes_all_shards": max_staged_window_bytes_all_shards,
        "modules": modules,
    }


def module_map(entries: list[dict]) -> dict[str, dict]:
    return {entry["module"]: entry for entry in entries}


def homogeneous_chain_plan(language: list[dict]) -> dict:
    modules = module_map(language)
    chains = []
    split_layers = []
    family_specs = (
        ("qkv", ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj")),
        ("attention_out", ("self_attn.o_proj",)),
        ("gate_up", ("mlp.gate_proj", "mlp.up_proj")),
        ("mlp_down", ("mlp.down_proj",)),
    )
    for layer in range(36):
        prefix = f"{LANGUAGE_PREFIX}{layer}."
        for family, suffixes in family_specs:
            selected = [modules[prefix + suffix] for suffix in suffixes]
            bits = [int(entry["bits"]) for entry in selected]
            if len(set(bits)) == 1:
                chains.append(
                    {
                        "layer": layer,
                        "family": family,
                        "bits": bits[0],
                        "modules": [entry["module"] for entry in selected],
                    }
                )
                continue
            if family != "qkv" or bits != [2, 4, 4]:
                raise RuntimeError(
                    f"M124_UNSUPPORTED_MIXED_CHAIN layer={layer} family={family} bits={bits}"
                )
            # The existing M89-X2 kernel uses one config bit width per call.
            # Preserve the selected Pareto point by splitting Q from K/V,
            # rather than spending another 25 MiB to promote Q merely to keep
            # the historical fused call shape.
            chains.append(
                {
                    "layer": layer,
                    "family": "q",
                    "bits": 2,
                    "modules": [selected[0]["module"]],
                }
            )
            chains.append(
                {
                    "layer": layer,
                    "family": "kv",
                    "bits": 4,
                    "modules": [selected[1]["module"], selected[2]["module"]],
                }
            )
            split_layers.append(layer)

    covered = [name for chain in chains for name in chain["modules"]]
    if len(chains) != 154 or len(covered) != 252 or set(covered) != set(modules):
        raise RuntimeError("M124_CHAIN_CLOSURE_FAIL")
    for index, chain in enumerate(chains):
        chain["chain_index"] = index
        chain["descriptor_count"] = sum(
            len(tiles(int(modules[name]["shape"][0]))) for name in chain["modules"]
        )
        if chain["descriptor_count"] > 10:
            raise RuntimeError(f"M124_CHAIN_DESCRIPTOR_BOUND_FAIL chain={index}")
    return {
        "chain_count": len(chains),
        "language_module_count": len(covered),
        "split_q_kv_layers": split_layers,
        "extra_calls_vs_m56": len(split_layers),
        "max_descriptors_per_chain": max(chain["descriptor_count"] for chain in chains),
        "chains": chains,
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--verify-blob", action="store_true")
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M124-frozen-M120-hardware-mapping-plan",
        "status": "FAIL",
        "classification": "offline exact layout/chain planning only; not CSim, CoSim, FPGA, board, performance or Web evidence",
    }
    try:
        source = args.source.resolve()
        manifest_path = source / "CHECKPOINT_MANIFEST.json"
        blob_path = source / "weights.bin"
        manifest_raw = manifest_path.read_bytes()
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        manifest = json.loads(manifest_raw)
        if manifest_sha != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError(f"M124_MANIFEST_IDENTITY_FAIL observed={manifest_sha}")
        if int(manifest["blob"]["bytes"]) != EXPECTED_BLOB_BYTES:
            raise RuntimeError("M124_DECLARED_BLOB_SIZE_FAIL")
        if manifest["blob"]["sha256"] != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M124_DECLARED_BLOB_HASH_FAIL")
        if blob_path.stat().st_size != EXPECTED_BLOB_BYTES:
            raise RuntimeError("M124_BLOB_SIZE_FAIL")
        observed_blob_sha = sha256_file(blob_path) if args.verify_blob else None
        if args.verify_blob and observed_blob_sha != EXPECTED_BLOB_SHA256:
            raise RuntimeError(f"M124_BLOB_HASH_FAIL observed={observed_blob_sha}")

        packed = [entry for entry in manifest["entries"] if entry.get("kind") == "packed"]
        language = [
            entry for entry in packed if entry.get("module", "").startswith(LANGUAGE_PREFIX)
        ]
        lm_head = [entry for entry in packed if entry.get("module") == "lm_head"]
        embedding = [
            entry for entry in packed
            if entry.get("module") == "model.language_model.embed_tokens"
        ]
        if len(language) != 252 or len(lm_head) != 1 or len(embedding) != 1:
            raise RuntimeError("M124_MODULE_CARDINALITY_FAIL")
        if Counter(int(entry["bits"]) for entry in language) != Counter({2: 28, 4: 224}):
            raise RuntimeError("M124_LANGUAGE_BIT_POLICY_FAIL")
        if int(lm_head[0]["bits"]) != 4 or int(embedding[0]["bits"]) != 3:
            raise RuntimeError("M124_HEAD_OR_EMBEDDING_POLICY_FAIL")

        language_plan = plan_layout(language)
        head_plan = plan_layout(lm_head)
        chain_plan = homogeneous_chain_plan(language)
        language_resident_fits = (
            int(language_plan["mapped_bytes_all_shards"]) <= HIGH_RESERVED_BYTES
        )
        head_low_cma_fits = int(head_plan["mapped_bytes_all_shards"]) <= LOW_CMA_BYTES
        if language_resident_fits:
            raise RuntimeError(
                "M124_EXPECTED_STREAMING_CLASSIFICATION_CHANGED; review before promotion"
            )
        if not head_low_cma_fits:
            raise RuntimeError("M124_LMHEAD_LOW_CMA_OVERFLOW")

        result.update(
            {
                "status": "PASS_STREAMED_LANGUAGE_SPLIT_QKV_PLAN",
                "checkpoint": {
                    "path": str(source),
                    "manifest_sha256": manifest_sha,
                    "blob_sha256": EXPECTED_BLOB_SHA256,
                    "blob_bytes": EXPECTED_BLOB_BYTES,
                    "blob_hash_recomputed": bool(args.verify_blob),
                    "observed_blob_sha256": observed_blob_sha,
                },
                "selected_policy": {
                    "language_bits": dict(sorted(Counter(int(e["bits"]) for e in language).items())),
                    "embedding_bits": 3,
                    "lm_head_bits": 4,
                    "embedding_execution": "PS; excluded from M89-X2 W2/W4 DDR layout",
                },
                "language_fourport_plan": {
                    key: value for key, value in language_plan.items() if key != "modules"
                },
                "language_resident_pool": {
                    "bytes": HIGH_RESERVED_BYTES,
                    "full_resident_fits": language_resident_fits,
                    "overflow_bytes": int(language_plan["mapped_bytes_all_shards"]) - HIGH_RESERVED_BYTES,
                    "selected_mode": "staged-low-cma per descriptor window",
                    "boot_dtb_cma_change_required": False,
                },
                "lm_head_fourport_plan": {
                    key: value for key, value in head_plan.items() if key != "modules"
                },
                "lm_head_low_cma": {
                    "bytes": LOW_CMA_BYTES,
                    "fits": head_low_cma_fits,
                    "headroom_bytes": LOW_CMA_BYTES - int(head_plan["mapped_bytes_all_shards"]),
                },
                "chain_plan": {
                    key: value for key, value in chain_plan.items() if key != "chains"
                },
                "kernel_reuse": {
                    "rtl_change_required": False,
                    "reason": "Every emitted call remains homogeneous W2 or W4 and within the existing <=10 descriptor bound.",
                    "host_contract_change_required": True,
                    "host_change": "Split layers 0-9 historical QKV call into one W2 Q call and one W4 KV call; retain all selected weight widths.",
                },
                "next_gate": "Build and reverse-verify exact M120 language and LM-head four-port layouts, then generate the 154-chain descriptor table and same-quantized golden.",
                "board_state_changed": False,
                "stable_rollback_preserved": True,
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline mapping gate; do not touch the board."

    atomic_json(args.result, result)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_STREAMED_LANGUAGE_SPLIT_QKV_PLAN":
        return 1
    print("M124_STREAMED_LANGUAGE_SPLIT_QKV_PLAN_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
