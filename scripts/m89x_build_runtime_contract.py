#!/usr/bin/env python3
"""Merge the verified M89-R schedule and M89-W identities into a board runtime contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


MAGIC = b"M89XRT1\0"
TOKENS = 32
SHARDS = 4
FAMILY_CODE = {"qkv": 0, "attention_out": 1, "gate_up": 2, "mlp_down": 3}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--real-hidden", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    schedule = json.loads(args.schedule.read_text(encoding="utf-8"))
    hidden = json.loads(args.real_hidden.read_text(encoding="utf-8"))
    layout_path = args.layout / "FOURPORT_LAYOUT_MANIFEST.json"
    if not layout_path.is_file():
        # The retained converter kept the historical manifest filename while
        # changing the embedded format/shard_count to the four-port contract.
        layout_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if layout.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError("M89X_LAYOUT_FORMAT_FAIL")
    modules = {
        item["module"]: item for item in layout["modules"]
        if ".language_model.layers." in item["module"]
    }
    hidden_chains = {
        (int(item["layer"]), item["family"]): item for item in hidden["chains"]
    }
    if len(schedule["chains"]) != 144 or len(hidden_chains) != 144 or len(modules) != 252:
        raise RuntimeError("M89X_CARDINALITY_FAIL")
    if int(schedule["tile_descriptor_count"]) != 648:
        raise RuntimeError("M89X_TILE_COUNT_FAIL")

    layout_files = []
    for item in layout["files"]:
        path = args.layout / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M89X_LAYOUT_FILE_IDENTITY_FAIL path={path}")
        layout_files.append(path)
    if len(layout_files) != SHARDS:
        raise RuntimeError("M89X_EXPECTED_FOUR_SHARDS")

    result_chains = []
    total_input = total_output = total_macros = total_descriptors = 0
    table = bytearray(MAGIC + struct.pack("<III", 144, 648, TOKENS))
    for expected_index, chain in enumerate(schedule["chains"]):
        layer = int(chain["layer"])
        family = chain["family"]
        if int(chain["chain_index"]) != expected_index or family not in FAMILY_CODE:
            raise RuntimeError("M89X_CHAIN_ORDER_FAIL")
        reference = hidden_chains[(layer, family)]
        groups = int(chain["input_groups"])
        count = int(chain["descriptor_count"])
        if groups != int(reference["groups"]) or count < 1 or count > 10:
            raise RuntimeError(f"M89X_CHAIN_GEOMETRY_FAIL chain={expected_index}")
        allowed_modules = set(reference["descriptors"])
        descriptor_records = []
        bits_seen = set()
        output_words = macros = 0
        module_tiles_seen: dict[str, set[int]] = {}
        for descriptor_index, descriptor in enumerate(chain["descriptors"]):
            name = descriptor["module"]
            tile_index = int(descriptor["tile_index"])
            if name not in allowed_modules or name not in modules:
                raise RuntimeError(f"M89X_MODULE_IDENTITY_FAIL chain={expected_index} module={name}")
            module = modules[name]
            tile = module["tiles"][tile_index]
            offsets = [int(value) for value in tile["shard_offsets"]]
            if len(set(offsets)) != 1 or offsets[0] % 16:
                raise RuntimeError(f"M89X_OFFSET_CONTRACT_FAIL chain={expected_index}")
            offset_words = offsets[0] // 16
            rows = int(tile["rows_per_shard"])
            valid_rows = int(tile["valid_rows"])
            bits = int(module["bits"])
            if (bits not in (2, 4) or rows < 8 or rows > 512 or rows % 8 or
                    bits != int(descriptor["bits"]) or rows != int(descriptor["rows_per_shard"]) or
                    valid_rows != int(descriptor["valid_rows"])):
                raise RuntimeError(f"M89X_DESCRIPTOR_GEOMETRY_FAIL chain={expected_index}")
            words_per_record = 1 + 4 * bits
            blocks = rows // 8
            end_word = offset_words + groups * blocks * words_per_record
            for path in layout_files:
                if end_word * 16 > path.stat().st_size:
                    raise RuntimeError(f"M89X_WEIGHT_RANGE_FAIL chain={expected_index}")
            raw = offset_words | (rows << 32) | (bits << 42)
            if raw >> 45:
                raise RuntimeError("M89X_DESCRIPTOR_ENCODING_OVERFLOW")
            descriptor_output_words = blocks * TOKENS * SHARDS * 4
            descriptor_macros = groups * rows * SHARDS * TOKENS
            output_words += descriptor_output_words
            macros += descriptor_macros
            bits_seen.add(bits)
            module_tiles_seen.setdefault(name, set()).add(tile_index)
            record = {
                "descriptor_index": descriptor_index,
                "module": name,
                "tile_index": tile_index,
                "row_start": int(tile["row_start"]),
                "rows_per_shard": rows,
                "valid_rows": valid_rows,
                "bits": bits,
                "offset_words": offset_words,
                "encoded_u64": f"0x{raw:016x}",
                "output_words64": descriptor_output_words,
                "output_bytes": descriptor_output_words * 8,
                "expected_macros": descriptor_macros,
            }
            descriptor_records.append(record)
            table.extend(struct.pack("<QIIII", raw, int(tile["row_start"]), valid_rows,
                                     descriptor_output_words, descriptor_macros))
        if len(bits_seen) != 1 or bits_seen != {int(reference["bits"])}:
            raise RuntimeError(f"M89X_MIXED_BIT_CHAIN_FAIL chain={expected_index}")
        for name in allowed_modules:
            expected_tiles = set(range(len(modules[name]["tiles"])))
            if module_tiles_seen.get(name, set()) != expected_tiles:
                raise RuntimeError(f"M89X_MODULE_TILE_COVERAGE_FAIL chain={expected_index} module={name}")

        bits = bits_seen.pop()
        config = groups | (bits << 8) | (count << 16)
        input_words = count + groups * TOKENS * 5
        table_header = struct.pack(
            "<IIIIIIII", expected_index, layer, FAMILY_CODE[family], config,
            count, input_words, output_words, macros
        )
        insert_at = len(table) - count * struct.calcsize("<QIIII")
        table[insert_at:insert_at] = table_header
        total_input += input_words * 16
        total_output += output_words * 8
        total_macros += macros
        total_descriptors += count
        result_chains.append({
            "chain_index": expected_index,
            "layer": layer,
            "family": family,
            "groups": groups,
            "bits": bits,
            "descriptor_count": count,
            "config_u32": f"0x{config:08x}",
            "input_words128": input_words,
            "input_bytes": input_words * 16,
            "output_words64": output_words,
            "output_bytes": output_words * 8,
            "expected_macros": macros,
            "raw_descriptor_tlast_count": count,
            "coalesced_chain_tlast_count": 1,
            "descriptors": descriptor_records,
        })

    if total_descriptors != 648:
        raise RuntimeError("M89X_FINAL_DESCRIPTOR_COUNT_FAIL")
    args.table.parent.mkdir(parents=True, exist_ok=True)
    args.table.write_bytes(table)
    result = {
        "date": "2026-08-31",
        "build": "M89-X",
        "status": "PASS_MERGED_648_TILE_RUNTIME_CONTRACT",
        "classification": "offline fail-closed host/FPGA contract; not bitstream or board execution",
        "source_evidence": {
            "m89r_schedule": args.schedule.as_posix(),
            "m89r_schedule_sha256": sha256(args.schedule),
            "m89w_real_hidden": args.real_hidden.as_posix(),
            "m89w_real_hidden_sha256": sha256(args.real_hidden),
            "fourport_layout_manifest": layout_path.as_posix(),
            "fourport_layout_manifest_sha256": sha256(layout_path),
        },
        "contract": {
            "chains": 144,
            "tile_descriptors": 648,
            "language_linear_modules": 252,
            "tokens_per_call": TOKENS,
            "weight_shards": SHARDS,
            "max_descriptors_per_chain": 10,
            "total_input_bytes_for_one_30_token_prefill": total_input,
            "total_output_bytes_for_one_30_token_prefill": total_output,
            "total_expected_macros": total_macros,
            "descriptor_transport": "one 128-bit AXIS word per descriptor before activation payload",
            "output_order": "descriptor, block-of-8-rows, token, shard, row-pair",
            "tlast": "M89-X HLS emits exactly one TLAST on the final word of the final descriptor in each chain",
        },
        "descriptor_table": {
            "path": args.table.as_posix(),
            "bytes": len(table),
            "sha256": sha256(args.table),
            "magic": "M89XRT1\\0",
        },
        "chains": result_chains,
        "next_gate": "integrate M89-X into the proven KV260 PS/DMA/high-DDR shell and close implementation timing/DRC without touching the board",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M89X_MERGED_648_TILE_RUNTIME_CONTRACT_PASS")
    print(json.dumps({
        "chains": 144,
        "descriptors": 648,
        "input_bytes": total_input,
        "output_bytes": total_output,
        "macros": total_macros,
        "table_sha256": result["descriptor_table"]["sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
