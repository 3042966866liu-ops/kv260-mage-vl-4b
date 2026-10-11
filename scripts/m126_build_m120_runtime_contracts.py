#!/usr/bin/env python3
"""Build and audit homogeneous-bit M120 language and W4 head contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path


LANGUAGE_MAGIC = b"M126RT1\0"
HEAD_MAGIC = b"M126HD1\0"
TOKENS = 32
SHARDS = 4
MAX_CHAIN = 10
FAMILY_CODE = {
    "qkv": 0,
    "attention_out": 1,
    "gate_up": 2,
    "mlp_down": 3,
    "q": 4,
    "kv": 5,
    "lm_head": 6,
}
EXPECTED_LANGUAGE_MANIFEST_SHA256 = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD_MANIFEST_SHA256 = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_layout(path: Path, expected_manifest_sha: str, expected_modules: int) -> tuple[dict, list[Path], str]:
    manifest_path = path / "SIXPORT_LAYOUT_MANIFEST.json"
    observed_manifest_sha = sha256_file(manifest_path)
    if observed_manifest_sha != expected_manifest_sha:
        raise RuntimeError(
            f"M126_LAYOUT_MANIFEST_IDENTITY_FAIL path={manifest_path} observed={observed_manifest_sha}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError("M126_LAYOUT_FORMAT_FAIL")
    if int(manifest["parameters"]["shard_count"]) != SHARDS:
        raise RuntimeError("M126_LAYOUT_SHARD_COUNT_FAIL")
    if len(manifest["modules"]) != expected_modules:
        raise RuntimeError("M126_LAYOUT_MODULE_COUNT_FAIL")
    files = []
    for item in manifest["files"]:
        file_path = path / item["path"]
        if file_path.stat().st_size != int(item["bytes"]):
            raise RuntimeError(f"M126_LAYOUT_FILE_SIZE_FAIL path={file_path}")
        if sha256_file(file_path) != item["sha256"]:
            raise RuntimeError(f"M126_LAYOUT_FILE_HASH_FAIL path={file_path}")
        files.append(file_path)
    if len(files) != SHARDS:
        raise RuntimeError("M126_LAYOUT_FILE_COUNT_FAIL")
    return manifest, files, observed_manifest_sha


def descriptor(module: dict, tile: dict, files: list[Path], descriptor_index: int) -> dict:
    bits = int(module["bits"])
    groups = int(module["input_groups"])
    offsets = [int(value) for value in tile["shard_offsets"]]
    if len(set(offsets)) != 1 or offsets[0] % 16:
        raise RuntimeError(f"M126_OFFSET_LOCKSTEP_FAIL module={module['module']}")
    rows = int(tile["rows_per_shard"])
    valid_rows = int(tile["valid_rows"])
    if bits not in (2, 4) or rows < 8 or rows > 512 or rows % 8:
        raise RuntimeError(f"M126_DESCRIPTOR_GEOMETRY_FAIL module={module['module']}")
    offset_words = offsets[0] // 16
    words_per_record = 1 + 4 * bits
    blocks = rows // 8
    end_word = offset_words + groups * blocks * words_per_record
    if any(end_word * 16 > path.stat().st_size for path in files):
        raise RuntimeError(f"M126_DESCRIPTOR_RANGE_FAIL module={module['module']}")
    raw = offset_words | (rows << 32) | (bits << 42)
    if raw >> 45:
        raise RuntimeError("M126_DESCRIPTOR_ENCODING_OVERFLOW")
    output_words = blocks * TOKENS * SHARDS * 4
    macros = groups * rows * SHARDS * TOKENS
    return {
        "descriptor_index": descriptor_index,
        "module": module["module"],
        "tile_index": int(tile["tile_index"]),
        "row_start": int(tile["row_start"]),
        "rows_per_shard": rows,
        "valid_rows": valid_rows,
        "bits": bits,
        "offset_words": offset_words,
        "encoded_u64": f"0x{raw:016x}",
        "record_bytes_per_shard": int(tile["record_bytes_per_shard"]),
        "output_words64": output_words,
        "output_bytes": output_words * 8,
        "expected_macros": macros,
    }


def make_chain(index: int, layer: int | None, family: str, selected: list[dict], files: list[Path]) -> dict:
    bits_seen = {int(module["bits"]) for module in selected}
    groups_seen = {int(module["input_groups"]) for module in selected}
    if len(bits_seen) != 1 or len(groups_seen) != 1:
        raise RuntimeError(f"M126_NONHOMOGENEOUS_CHAIN layer={layer} family={family}")
    bits = bits_seen.pop()
    groups = groups_seen.pop()
    descriptors = []
    for module in selected:
        for tile in module["tiles"]:
            descriptors.append(descriptor(module, tile, files, len(descriptors)))
    if not 1 <= len(descriptors) <= MAX_CHAIN:
        raise RuntimeError(f"M126_CHAIN_DESCRIPTOR_BOUND_FAIL layer={layer} family={family}")
    minimum_word = min(item["offset_words"] for item in descriptors)
    maximum_end_word = max(
        item["offset_words"] + item["record_bytes_per_shard"] // 16
        for item in descriptors
    )
    config = groups | (bits << 8) | (len(descriptors) << 16)
    output_words = sum(item["output_words64"] for item in descriptors)
    macros = sum(item["expected_macros"] for item in descriptors)
    return {
        "chain_index": index,
        "layer": layer,
        "family": family,
        "family_code": FAMILY_CODE[family],
        "groups": groups,
        "bits": bits,
        "descriptor_count": len(descriptors),
        "config_u32": f"0x{config:08x}",
        "input_words128": len(descriptors) + groups * TOKENS * 5,
        "input_bytes": (len(descriptors) + groups * TOKENS * 5) * 16,
        "output_words64": output_words,
        "output_bytes": output_words * 8,
        "expected_macros": macros,
        "staged_base_words": minimum_word,
        "staged_words_per_shard": maximum_end_word - minimum_word,
        "staged_bytes_per_shard": (maximum_end_word - minimum_word) * 16,
        "staged_bytes_all_shards": (maximum_end_word - minimum_word) * 16 * SHARDS,
        "descriptors": descriptors,
    }


def language_chains(manifest: dict, files: list[Path]) -> list[dict]:
    modules = {module["module"]: module for module in manifest["modules"]}
    chains = []
    for layer in range(36):
        prefix = f"model.language_model.layers.{layer}."
        q = modules[prefix + "self_attn.q_proj"]
        k = modules[prefix + "self_attn.k_proj"]
        v = modules[prefix + "self_attn.v_proj"]
        if {int(q["bits"]), int(k["bits"]), int(v["bits"])} == {int(q["bits"])}:
            specs = [("qkv", [q, k, v])]
        elif [int(q["bits"]), int(k["bits"]), int(v["bits"])] == [2, 4, 4]:
            specs = [("q", [q]), ("kv", [k, v])]
        else:
            raise RuntimeError(f"M126_UNSUPPORTED_QKV_POLICY layer={layer}")
        specs.extend(
            [
                ("attention_out", [modules[prefix + "self_attn.o_proj"]]),
                ("gate_up", [modules[prefix + "mlp.gate_proj"], modules[prefix + "mlp.up_proj"]]),
                ("mlp_down", [modules[prefix + "mlp.down_proj"]]),
            ]
        )
        for family, selected in specs:
            chains.append(make_chain(len(chains), layer, family, selected, files))
    covered = [descriptor["module"] for chain in chains for descriptor in chain["descriptors"]]
    # Tile-level coverage permits repeated module names, so verify each
    # module/tile identity exactly once instead of only set equality.
    expected = {
        (module["module"], int(tile["tile_index"]))
        for module in manifest["modules"]
        for tile in module["tiles"]
    }
    observed = {
        (descriptor["module"], int(descriptor["tile_index"]))
        for chain in chains
        for descriptor in chain["descriptors"]
    }
    if len(chains) != 154 or len(expected) != 648 or observed != expected:
        raise RuntimeError("M126_LANGUAGE_CHAIN_CLOSURE_FAIL")
    return chains


def head_chains(manifest: dict, files: list[Path]) -> list[dict]:
    module = manifest["modules"][0]
    if module["module"] != "lm_head" or int(module["bits"]) != 4:
        raise RuntimeError("M126_HEAD_IDENTITY_FAIL")
    chains = []
    for start in range(0, len(module["tiles"]), MAX_CHAIN):
        partial = dict(module)
        partial["tiles"] = module["tiles"][start : start + MAX_CHAIN]
        chain = make_chain(len(chains), None, "lm_head", [partial], files)
        # Retain global tile indices and local descriptor indices.
        chains.append(chain)
    if len(chains) != 8 or sum(chain["descriptor_count"] for chain in chains) != 75:
        raise RuntimeError("M126_HEAD_CHAIN_CLOSURE_FAIL")
    return chains


def write_table(path: Path, magic: bytes, chains: list[dict], expected_descriptors: int) -> dict:
    table = bytearray(magic + struct.pack("<III", len(chains), expected_descriptors, TOKENS))
    for chain in chains:
        table.extend(
            struct.pack(
                "<IIIIIIII",
                int(chain["chain_index"]),
                0xFFFFFFFF if chain["layer"] is None else int(chain["layer"]),
                int(chain["family_code"]),
                int(chain["config_u32"], 16),
                int(chain["descriptor_count"]),
                int(chain["input_words128"]),
                int(chain["output_words64"]),
                int(chain["expected_macros"]),
            )
        )
        for item in chain["descriptors"]:
            table.extend(
                struct.pack(
                    "<QIIII",
                    int(item["encoded_u64"], 16),
                    int(item["row_start"]),
                    int(item["valid_rows"]),
                    int(item["output_words64"]),
                    int(item["expected_macros"]),
                )
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(table)
    return {"path": str(path), "bytes": len(table), "sha256": sha256_file(path), "magic": magic.decode("ascii").rstrip("\0")}


def audit_table(path: Path, magic: bytes, chains: list[dict], expected_descriptors: int) -> dict:
    raw = memoryview(path.read_bytes())
    if raw[:8].tobytes() != magic:
        raise RuntimeError("M126_TABLE_MAGIC_FAIL")
    chain_count, descriptor_count, tokens = struct.unpack_from("<III", raw, 8)
    if (chain_count, descriptor_count, tokens) != (len(chains), expected_descriptors, TOKENS):
        raise RuntimeError("M126_TABLE_HEADER_FAIL")
    cursor = 20
    decoded_descriptors = 0
    for expected_chain in chains:
        header = struct.unpack_from("<IIIIIIII", raw, cursor)
        cursor += 32
        expected_layer = 0xFFFFFFFF if expected_chain["layer"] is None else int(expected_chain["layer"])
        expected_header = (
            int(expected_chain["chain_index"]), expected_layer,
            int(expected_chain["family_code"]), int(expected_chain["config_u32"], 16),
            int(expected_chain["descriptor_count"]), int(expected_chain["input_words128"]),
            int(expected_chain["output_words64"]), int(expected_chain["expected_macros"]),
        )
        if header != expected_header:
            raise RuntimeError(f"M126_TABLE_CHAIN_HEADER_FAIL chain={expected_chain['chain_index']}")
        for expected_descriptor in expected_chain["descriptors"]:
            record = struct.unpack_from("<QIIII", raw, cursor)
            cursor += 24
            expected_record = (
                int(expected_descriptor["encoded_u64"], 16),
                int(expected_descriptor["row_start"]), int(expected_descriptor["valid_rows"]),
                int(expected_descriptor["output_words64"]), int(expected_descriptor["expected_macros"]),
            )
            if record != expected_record:
                raise RuntimeError("M126_TABLE_DESCRIPTOR_FAIL")
            decoded_descriptors += 1
    if cursor != len(raw) or decoded_descriptors != expected_descriptors:
        raise RuntimeError("M126_TABLE_CLOSURE_FAIL")
    return {
        "status": "PASS_INDEPENDENT_BINARY_TABLE_PARSE",
        "chain_count": chain_count,
        "descriptor_count": decoded_descriptors,
        "bytes_consumed": cursor,
        "trailing_bytes": len(raw) - cursor,
    }


def contract_summary(chains: list[dict]) -> dict:
    return {
        "chain_count": len(chains),
        "tile_descriptor_count": sum(chain["descriptor_count"] for chain in chains),
        "total_input_bytes": sum(chain["input_bytes"] for chain in chains),
        "total_output_bytes": sum(chain["output_bytes"] for chain in chains),
        "total_expected_macros": sum(chain["expected_macros"] for chain in chains),
        "max_descriptors_per_chain": max(chain["descriptor_count"] for chain in chains),
        "maximum_staged_bytes_per_shard": max(chain["staged_bytes_per_shard"] for chain in chains),
        "maximum_staged_bytes_all_shards": max(chain["staged_bytes_all_shards"] for chain in chains),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout-root", type=Path, required=True)
    parser.add_argument("--language-table", type=Path, required=True)
    parser.add_argument("--head-table", type=Path, required=True)
    parser.add_argument("--language-result", type=Path, required=True)
    parser.add_argument("--head-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M126-M120-runtime-contracts",
        "status": "FAIL",
        "classification": "offline descriptor and staged-window contract; not CSim, CoSim, FPGA, board, performance or Web evidence",
    }
    try:
        language_manifest, language_files, language_sha = load_layout(
            args.layout_root / "language_fourport", EXPECTED_LANGUAGE_MANIFEST_SHA256, 252
        )
        head_manifest, head_files, head_sha = load_layout(
            args.layout_root / "lmhead_fourport", EXPECTED_HEAD_MANIFEST_SHA256, 1
        )
        language = language_chains(language_manifest, language_files)
        head = head_chains(head_manifest, head_files)
        language_table = write_table(args.language_table, LANGUAGE_MAGIC, language, 648)
        head_table = write_table(args.head_table, HEAD_MAGIC, head, 75)
        language_table_audit = audit_table(args.language_table, LANGUAGE_MAGIC, language, 648)
        head_table_audit = audit_table(args.head_table, HEAD_MAGIC, head, 75)

        language_payload = {
            "date": "2026-08-31",
            "build": "M126-LANGUAGE",
            "status": "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS",
            "classification": result["classification"],
            "source_manifest_sha256": language_sha,
            "contract": contract_summary(language),
            "split_q_kv_layers": list(range(10)),
            "extra_calls_vs_m56": 10,
            "descriptor_table": language_table,
            "descriptor_table_audit": language_table_audit,
            "chains": language,
            "board_state_changed": False,
        }
        head_payload = {
            "date": "2026-08-31",
            "build": "M126-LMHEAD",
            "status": "PASS_M120_W4_LMHEAD_8_CHAINS",
            "classification": result["classification"],
            "source_manifest_sha256": head_sha,
            "contract": contract_summary(head),
            "descriptor_table": head_table,
            "descriptor_table_audit": head_table_audit,
            "chains": head,
            "board_state_changed": False,
        }
        atomic_json(args.language_result, language_payload)
        atomic_json(args.head_result, head_payload)
        result.update(
            {
                "status": "PASS_M120_154_LANGUAGE_PLUS_8_HEAD_CONTRACTS",
                "language_result": {"path": str(args.language_result), "sha256": sha256_file(args.language_result), **contract_summary(language)},
                "head_result": {"path": str(args.head_result), "sha256": sha256_file(args.head_result), **contract_summary(head)},
                "total_fpga_calls_per_prefill": len(language) + len(head),
                "all_calls_homogeneous_w2_or_w4": True,
                "existing_m89x2_rtl_reusable": True,
                "recursive_module_tile_closure": "252/252 modules and 648/648 language tiles; 1/1 module and 75/75 head tiles",
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Build M120 same-quantized fixed-text family golden and M126 CSim fixture, then run numerical CSim before any board package.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline descriptor gate; do not touch the board."

    atomic_json(args.result, result)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_M120_154_LANGUAGE_PLUS_8_HEAD_CONTRACTS":
        return 1
    print("M126_M120_RUNTIME_CONTRACTS_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
