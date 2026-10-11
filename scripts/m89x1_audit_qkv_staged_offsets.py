#!/usr/bin/env python3
"""Prove staged-low-CMA offsets reconstruct every real Layer-0 QKV byte.

This is a host-only gate.  It checks the exact issue that micro-tile CSim does
not cover: all descriptor/block bytes in the real four-shard layout must be at
the same address after `chain_window()` rebases descriptors for staged mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    runtime = workspace / "deployment/mage_vl4b/m89x_t32_runtime"
    sys.path.insert(0, str(runtime))
    from board_runtime import chain_window, verify_layout
    from contract_runtime import RuntimeContract

    root = workspace / "deployment/mage_vl4b"
    language = root / "artifacts/m89y_language_fourport"
    contract_path = root / "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json"
    contract = RuntimeContract.load(contract_path, "PASS_MERGED_648_TILE_RUNTIME_CONTRACT")
    layout_hash = contract.payload["source_evidence"]["fourport_layout_manifest_sha256"]
    layout = verify_layout(language, layout_hash, 252)
    chain = next(item for item in contract.chains if int(item["layer"]) == 0 and item["family"] == "qkv")
    base_words, window_bytes = chain_window(layout, chain)
    base_bytes = base_words * 16
    tiles = {(entry["module"], int(tile["tile_index"])): tile
             for entry in layout.manifest["modules"] for tile in entry["tiles"]}
    checks: list[dict] = []
    passed = True
    for descriptor in chain["descriptors"]:
        tile = tiles[(descriptor["module"], int(descriptor["tile_index"]))]
        original_offset = int(tile["shard_offsets"][0])
        size = int(tile["record_bytes_per_shard"])
        rebased = int(descriptor["offset_words"]) - base_words
        offset_matches = int(descriptor["offset_words"]) * 16 == original_offset
        in_window = 0 <= rebased * 16 and rebased * 16 + size <= window_bytes
        shard_equal = []
        for shard in range(4):
            path = language / f"weights{shard}.bin"
            with path.open("rb", buffering=0) as source:
                source.seek(original_offset)
                original = source.read(size)
                source.seek(base_bytes)
                staged_window = source.read(window_bytes)
            reconstructed = staged_window[rebased * 16:rebased * 16 + size]
            shard_equal.append(sha256(original) == sha256(reconstructed) and len(original) == size)
        ok = offset_matches and in_window and all(shard_equal)
        passed = passed and ok
        checks.append({
            "module": descriptor["module"],
            "tile_index": int(descriptor["tile_index"]),
            "original_offset_bytes": original_offset,
            "rebased_offset_words": rebased,
            "record_bytes_per_shard": size,
            "offset_matches_contract": offset_matches,
            "within_staged_window": in_window,
            "all_four_shards_byte_exact": all(shard_equal),
        })
    result = {
        "gate": "M89-X1-layer0-qkv-staged-offset-full-byte-audit",
        "status": "PASS" if passed else "FAIL",
        "chain_descriptor_count": len(chain["descriptors"]),
        "window_base_words": base_words,
        "window_bytes_per_shard": window_bytes,
        "descriptors": checks,
        "board_state_changed": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M89X1_QKV_STAGED_OFFSET_AUDIT_PASS" if passed else "M89X1_QKV_STAGED_OFFSET_AUDIT_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
