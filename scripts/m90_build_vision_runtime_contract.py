#!/usr/bin/env python3
"""Build the fail-closed M90 vision descriptor and raw-auxiliary contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path


MAGIC = b"M90VRT1\0"
TOKENS = 32
SHARDS = 4
GROUP_SIZE = 64
ALIGNMENT = 64


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_names() -> list[str]:
    names = []
    for layer in range(24):
        base = f"model.visual.encoder.layers.{layer}"
        names.extend((
            f"{base}.self_attn.qkv",
            f"{base}.self_attn.proj",
            f"{base}.mlp.fc1",
            f"{base}.mlp.fc2",
        ))
    names.extend(("model.visual.merger.mlp.0", "model.visual.merger.mlp.2"))
    return names


def role(name: str) -> str:
    if name.endswith("self_attn.qkv"):
        return "qkv"
    if name.endswith("self_attn.proj"):
        return "attention_out"
    if name.endswith("mlp.fc1"):
        return "mlp_fc1"
    if name.endswith("mlp.fc2"):
        return "mlp_fc2"
    if name.endswith("merger.mlp.0"):
        return "merger_fc1"
    if name.endswith("merger.mlp.2"):
        return "merger_fc2"
    raise ValueError(name)


def copy_raw_visual(source_manifest: Path, output_blob: Path, output_manifest: Path) -> dict:
    manifest_bytes = source_manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    source_blob = source_manifest.parent / manifest["blob"]["path"]
    if source_blob.stat().st_size != int(manifest["blob"]["bytes"]):
        raise RuntimeError("M90_SOURCE_BLOB_SIZE_FAIL")
    entries = [item for item in manifest["entries"] if item["kind"] == "raw" and item["name"].startswith("model.visual.")]
    if len(entries) != 199:
        raise RuntimeError(f"M90_VISUAL_RAW_COUNT_FAIL count={len(entries)}")
    output_blob.parent.mkdir(parents=True, exist_ok=True)
    compact_entries = []
    with source_blob.open("rb") as source, output_blob.open("wb") as destination:
        for item in entries:
            padding = (-destination.tell()) % ALIGNMENT
            destination.write(bytes(padding))
            section = item["section"]
            source.seek(int(section["offset"]))
            payload = source.read(int(section["bytes"]))
            if len(payload) != int(section["bytes"]):
                raise RuntimeError(f"M90_RAW_SOURCE_TRUNCATED name={item['name']}")
            if hashlib.sha256(payload).hexdigest() != section["sha256"]:
                raise RuntimeError(f"M90_RAW_SOURCE_HASH_FAIL name={item['name']}")
            offset = destination.tell()
            destination.write(payload)
            compact_entries.append({
                "name": item["name"],
                "shape": item["shape"],
                "dtype": item["dtype"],
                "offset": offset,
                "bytes": len(payload),
                "sha256": section["sha256"],
            })
        destination.flush()
        os.fsync(destination.fileno())
    compact = {
        "format": "tellme-mage-vl-m90-vision-raw-aux-v1",
        "source_manifest": source_manifest.as_posix(),
        "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_blob_sha256": manifest["blob"]["sha256"],
        "entry_count": len(compact_entries),
        "blob": {"path": output_blob.name, "bytes": output_blob.stat().st_size, "sha256": sha256(output_blob)},
        "entries": compact_entries,
    }
    output_manifest.write_text(json.dumps(compact, indent=2) + "\n", encoding="utf-8")
    return compact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--checkpoint-manifest", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--aux-blob", type=Path, required=True)
    parser.add_argument("--aux-manifest", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    layout_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if layout.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError("M90_LAYOUT_FORMAT_FAIL")
    files = []
    for item in layout["files"]:
        path = args.layout / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M90_LAYOUT_FILE_IDENTITY_FAIL path={path}")
        files.append(path)
    if len(files) != SHARDS:
        raise RuntimeError("M90_LAYOUT_SHARD_COUNT_FAIL")
    modules = {item["module"]: item for item in layout["modules"]}
    names = expected_names()
    if set(modules) != set(names) or len(modules) != 98:
        raise RuntimeError("M90_VISION_MODULE_IDENTITY_FAIL")

    args.table.parent.mkdir(parents=True, exist_ok=True)
    table = bytearray(MAGIC + struct.pack("<III", len(names), TOKENS, SHARDS))
    chains = []
    per_video_calls = per_video_descriptors = per_video_macros = 0
    for chain_index, name in enumerate(names):
        module = modules[name]
        if int(module["bits"]) != 4:
            raise RuntimeError(f"M90_EXPECTED_W4 module={name}")
        output_rows, input_columns = map(int, module["shape"])
        if input_columns % GROUP_SIZE:
            raise RuntimeError(f"M90_INPUT_GROUP_GEOMETRY_FAIL module={name}")
        groups = input_columns // GROUP_SIZE
        descriptor_count = len(module["tiles"])
        batch_count = 25 if name.startswith("model.visual.merger.") else 98
        records = []
        output_words = macros = 0
        for descriptor_index, tile in enumerate(module["tiles"]):
            offsets = [int(value) for value in tile["shard_offsets"]]
            if len(offsets) != SHARDS or len(set(offsets)) != 1 or offsets[0] % 16:
                raise RuntimeError(f"M90_TILE_OFFSET_FAIL module={name}")
            rows = int(tile["rows_per_shard"])
            valid_rows = int(tile["valid_rows"])
            if rows < 8 or rows > 512 or rows % 8:
                raise RuntimeError(f"M90_TILE_ROW_GEOMETRY_FAIL module={name}")
            offset_words = offsets[0] // 16
            words_per_record = 17
            end_word = offset_words + groups * (rows // 8) * words_per_record
            if any(end_word * 16 > path.stat().st_size for path in files):
                raise RuntimeError(f"M90_TILE_RANGE_FAIL module={name}")
            raw = offset_words | (rows << 32) | (4 << 42)
            descriptor_output_words = (rows // 8) * TOKENS * SHARDS * 4
            descriptor_macros = groups * rows * SHARDS * TOKENS
            output_words += descriptor_output_words
            macros += descriptor_macros
            record = {
                "descriptor_index": descriptor_index,
                "module": name,
                "tile_index": int(tile["tile_index"]),
                "row_start": int(tile["row_start"]),
                "rows_per_shard": rows,
                "valid_rows": valid_rows,
                "offset_words": offset_words,
                "encoded_u64": f"0x{raw:016x}",
                "output_words64": descriptor_output_words,
                "output_bytes": descriptor_output_words * 8,
                "expected_macros": descriptor_macros,
            }
            records.append(record)
            table.extend(struct.pack("<QIIII", raw, int(tile["row_start"]), valid_rows,
                                     descriptor_output_words, descriptor_macros))
        config = groups | (4 << 8) | (descriptor_count << 16)
        input_words = descriptor_count + groups * TOKENS * 5
        header = struct.pack("<IIIIIIII", chain_index, groups, descriptor_count, config,
                             output_rows, input_columns, batch_count, macros)
        insert_at = len(table) - descriptor_count * struct.calcsize("<QIIII")
        table[insert_at:insert_at] = header
        per_video_calls += batch_count
        per_video_descriptors += batch_count * descriptor_count
        per_video_macros += batch_count * macros
        chains.append({
            "chain_index": chain_index,
            "module": name,
            "role": role(name),
            "shape": [output_rows, input_columns],
            "groups": groups,
            "bits": 4,
            "descriptor_count": descriptor_count,
            "config_u32": f"0x{config:08x}",
            "input_words128": input_words,
            "input_bytes": input_words * 16,
            "t32_batches_per_video": batch_count,
            "output_words64_per_batch": output_words,
            "output_bytes": output_words * 8,
            "expected_macros": macros,
            "expected_macros_per_batch": macros,
            "descriptors": records,
        })
    args.table.write_bytes(table)
    aux = copy_raw_visual(args.checkpoint_manifest, args.aux_blob, args.aux_manifest)
    result = {
        "date": "2026-08-31",
        "build": "M90-V",
        "status": "PASS_M90_VISION_RUNTIME_CONTRACT",
        "classification": "offline vision host/FPGA contract; not board execution or E2E video inference",
        "source_evidence": {
            "fourport_layout_manifest": layout_path.as_posix(),
            "fourport_layout_manifest_sha256": sha256(layout_path),
            "m56_checkpoint_manifest": args.checkpoint_manifest.as_posix(),
            "m56_checkpoint_manifest_sha256": sha256(args.checkpoint_manifest),
        },
        "contract": {
            "packed_linear_modules": len(names),
            "raw_visual_tensors": aux["entry_count"],
            "tokens_per_fpga_call": TOKENS,
            "encoder_patch_tokens": 3136,
            "merged_visual_tokens": 784,
            "encoder_t32_batches": 98,
            "merger_t32_batches": 25,
            "fpga_chain_calls_per_video": per_video_calls,
            "fpga_descriptor_executions_per_video": per_video_descriptors,
            "expected_macros_per_video": per_video_macros,
            "ps_operations": [
                "fixed RGB normalization and patchify",
                "BF16 patch embedding convolution",
                "LayerNorm, 3-D RoPE, attention softmax/matmul, bias, GELU and residuals",
                "2x2 patch merge assembly and language-token splice",
            ],
            "pl_operations": "all 98 W4 vision/projector Linear modules through the existing M89-X T32 kernel",
        },
        "descriptor_table": {"path": args.table.as_posix(), "bytes": len(table), "sha256": sha256(args.table), "magic": "M90VRT1\\0"},
        "raw_auxiliary": {"manifest": args.aux_manifest.as_posix(), "manifest_sha256": sha256(args.aux_manifest), **aux["blob"]},
        "chains": chains,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Implement the PS vision operator loop and compare its 784x2560 BF16 output against the official M90 golden before packaging or board action.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M90_VISION_RUNTIME_CONTRACT_PASS")
    print(json.dumps({"chains": len(names), "calls": per_video_calls, "descriptors": per_video_descriptors,
                      "macros": per_video_macros, "raw_aux_bytes": aux["blob"]["bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
