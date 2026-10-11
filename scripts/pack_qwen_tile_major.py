#!/usr/bin/env python3
"""Reorder TeLLMe W4 packets into the exact 560-block execution-tile order.

The existing Mixed-GS files are tensor-major and group-major.  Large output
projections are consumed a tile at a time, which makes each runtime tile a
strided read across the complete tensor.  This tool writes the same 288-byte
macro records in the exact order consumed by the shared KV260 kernel so every
runtime tile is one contiguous file extent.  No quantization data is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


PACKET_BYTES = 288
DEFAULT_TILE_BLOCKS = 560


def sha256_file(path: Path, chunk_bytes: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def execution_schedule(linears: dict[str, dict], layers: int) -> list[tuple[str, ...]]:
    schedule: list[tuple[str, ...]] = []
    for layer in range(layers):
        prefix = f"model.layers.{layer}"
        schedule.extend(
            [
                (
                    f"{prefix}.self_attn.q_proj.weight",
                    f"{prefix}.self_attn.k_proj.weight",
                    f"{prefix}.self_attn.v_proj.weight",
                ),
                (f"{prefix}.self_attn.o_proj.weight",),
                (f"{prefix}.mlp.gate_proj.weight",),
                (f"{prefix}.mlp.up_proj.weight",),
                (f"{prefix}.mlp.down_proj.weight",),
            ]
        )
    scheduled = {name for key in schedule for name in key}
    missing = set(linears) - scheduled
    extra = scheduled - set(linears)
    if missing or extra:
        raise RuntimeError(
            f"execution schedule mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return schedule


def write_transformer_tiles(
    source_path: Path,
    index: dict,
    output_path: Path,
    tile_blocks: int,
) -> dict:
    linears = {item["name"]: item for item in index["linears"]}
    layers = int(index["config"]["num_hidden_layers"])
    source = np.memmap(source_path, dtype=np.uint8, mode="r")
    entries: list[dict] = []
    output_offset = 0

    with output_path.open("wb", buffering=8 << 20) as output:
        for key in execution_schedule(linears, layers):
            items = [linears[name] for name in key]
            groups = int(items[0]["input_groups"])
            if any(int(item["input_groups"]) != groups for item in items):
                raise RuntimeError(f"fused entry has mismatched input groups: {key}")
            layouts: list[list[int]] = []
            logical = 0
            for item in items:
                blocks = int(item["output_blocks"])
                layouts.append([logical, logical + blocks])
                logical += blocks
            total_blocks = logical
            tiles: list[dict] = []

            for block_start in range(0, total_blocks, tile_blocks):
                block_stop = min(block_start + tile_blocks, total_blocks)
                block_count = block_stop - block_start
                tile = np.empty((groups, block_count, PACKET_BYTES), dtype=np.uint8)
                target_start = 0
                logical_start = 0
                for item in items:
                    blocks = int(item["output_blocks"])
                    logical_stop = logical_start + blocks
                    overlap_start = max(block_start, logical_start)
                    overlap_stop = min(block_stop, logical_stop)
                    if overlap_start < overlap_stop:
                        start = int(item["offset"])
                        stop = start + int(item["bytes"])
                        matrix = source[start:stop].reshape(groups, blocks, PACKET_BYTES)
                        source_start = overlap_start - logical_start
                        count = overlap_stop - overlap_start
                        tile[:, target_start : target_start + count, :] = matrix[
                            :, source_start : source_start + count, :
                        ]
                        target_start += count
                    logical_start = logical_stop
                if target_start != block_count:
                    raise RuntimeError(f"tile coverage mismatch for {key} at {block_start}")
                payload = tile.tobytes(order="C")
                output.write(payload)
                tiles.append(
                    {
                        "block_start": block_start,
                        "block_stop": block_stop,
                        "offset": output_offset,
                        "bytes": len(payload),
                    }
                )
                output_offset += len(payload)
            entries.append(
                {
                    "key": list(key),
                    "input_groups": groups,
                    "total_blocks": total_blocks,
                    "layouts": layouts,
                    "tiles": tiles,
                }
            )

    expected = sum(int(item["bytes"]) for item in linears.values())
    if output_offset != expected or output_path.stat().st_size != expected:
        raise RuntimeError(
            f"transformer byte conservation failed: output={output_offset}, expected={expected}"
        )
    return {
        "format": "tellme-w4g64-execution-tile-major-v1",
        "packet_bytes": PACKET_BYTES,
        "tile_blocks": tile_blocks,
        "source_file": source_path.name,
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256_file(source_path),
        "tile_file": output_path.name,
        "tile_bytes": output_path.stat().st_size,
        "tile_sha256": sha256_file(output_path),
        "entries": entries,
    }


def write_lm_head_tiles(
    source_path: Path,
    info: dict,
    output_path: Path,
    tile_blocks: int,
) -> dict:
    groups = int(info["input_groups"])
    blocks = int(info["output_blocks"])
    source = np.memmap(source_path, dtype=np.uint8, mode="r").reshape(
        groups, blocks, PACKET_BYTES
    )
    tiles: list[dict] = []
    output_offset = 0
    with output_path.open("wb", buffering=8 << 20) as output:
        for block_start in range(0, blocks, tile_blocks):
            block_stop = min(block_start + tile_blocks, blocks)
            tile = np.ascontiguousarray(source[:, block_start:block_stop, :])
            payload = tile.tobytes(order="C")
            output.write(payload)
            tiles.append(
                {
                    "block_start": block_start,
                    "block_stop": block_stop,
                    "offset": output_offset,
                    "bytes": len(payload),
                }
            )
            output_offset += len(payload)
    expected = int(info["bytes"])
    if output_offset != expected or output_path.stat().st_size != expected:
        raise RuntimeError(
            f"LM-head byte conservation failed: output={output_offset}, expected={expected}"
        )
    return {
        "format": "tellme-w4g64-execution-tile-major-v1",
        "packet_bytes": PACKET_BYTES,
        "tile_blocks": tile_blocks,
        "input_groups": groups,
        "output_blocks": blocks,
        "source_file": source_path.name,
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256_file(source_path),
        "tile_file": output_path.name,
        "tile_bytes": output_path.stat().st_size,
        "tile_sha256": sha256_file(output_path),
        "tiles": tiles,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tile-blocks", type=int, default=DEFAULT_TILE_BLOCKS)
    args = parser.parse_args()
    if args.tile_blocks <= 0:
        raise ValueError("tile-blocks must be positive")

    root = args.root.resolve()
    output_root = args.output_root.resolve()
    model_indexes = sorted((root / "model").glob("*_mixed_gs_index.json"))
    lm_indexes = sorted((root / "lm_head").glob("*_lm_head_w4g64.json"))
    if len(model_indexes) != 1 or len(lm_indexes) != 1:
        raise RuntimeError("expected exactly one Transformer and one LM-head index")
    model_index = json.loads(model_indexes[0].read_text())
    lm_info = json.loads(lm_indexes[0].read_text())
    linear_source = root / "model" / Path(model_index["linear_file"]["path"]).name
    lm_source = lm_indexes[0].with_suffix(".mgs")

    model_out = output_root / "model"
    lm_out = output_root / "lm_head"
    model_out.mkdir(parents=True, exist_ok=True)
    lm_out.mkdir(parents=True, exist_ok=True)
    transformer_file = model_out / "qwen25_7b_linears_w4g64_tilemajor.tmg"
    transformer_index = model_out / "qwen25_7b_tile_major_index.json"
    lm_file = lm_out / "qwen25_7b_lm_head_w4g64_tilemajor.tmg"
    lm_index = lm_out / "qwen25_7b_lm_head_tile_major_index.json"
    for path in (transformer_file, transformer_index, lm_file, lm_index):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")

    transformer_result = write_transformer_tiles(
        linear_source, model_index, transformer_file, args.tile_blocks
    )
    transformer_index.write_text(json.dumps(transformer_result, indent=2) + "\n")
    lm_result = write_lm_head_tiles(lm_source, lm_info, lm_file, args.tile_blocks)
    lm_index.write_text(json.dumps(lm_result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "transformer": transformer_result,
                "lm_head": lm_result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
