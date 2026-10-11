#!/usr/bin/env python3
"""Build a bounded real-record M120 numerical CSim fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path

import numpy as np


MAGIC = b"M128CSM1"
TOKENS = 32
VALID_TOKENS = 30
MAX_WORDS = 17
EXPECTED_LANGUAGE_CONTRACT_SHA256 = "c8bab2c1d4c7ba1cf2075559498243ed2803d8db8de90a8d812c94ceebfc7e9f"
EXPECTED_HEAD_CONTRACT_SHA256 = "3304da81b7e679291bfa59bb11d4fd2d978c2dc3facb2fc2dbbd23739fe5be4e"


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


def quantize(values: np.ndarray, groups: int) -> tuple[np.ndarray, np.ndarray]:
    source = np.asarray(values, dtype=np.float32)
    if source.shape != (VALID_TOKENS, groups * 64):
        raise RuntimeError(f"M128_ACTIVATION_GEOMETRY_FAIL shape={source.shape} groups={groups}")
    padded = np.zeros((TOKENS, groups, 64), dtype=np.float32)
    padded[:VALID_TOKENS] = source.reshape(VALID_TOKENS, groups, 64)
    maximum = np.max(np.abs(padded), axis=2)
    scale = (maximum / np.float32(127.0)).astype("<f2")
    safe = np.where(maximum == 0.0, np.float16(1.0), scale).astype("<f2")
    codes = np.clip(
        np.rint(padded / safe.astype(np.float32)[..., None]), -127, 127
    ).astype(np.int8)
    if not np.isfinite(safe).all():
        raise RuntimeError("M128_NONFINITE_ACTIVATION_SCALE")
    return codes, safe


def layout_index(root: Path) -> tuple[dict[str, dict], list[object], dict]:
    manifest_path = root / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    handles = []
    for item in manifest["files"]:
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"M128_LAYOUT_FILE_IDENTITY_FAIL path={path}")
        handles.append(path.open("rb"))
    return {module["module"]: module for module in manifest["modules"]}, handles, manifest


def select_language_chains(payload: dict) -> list[dict]:
    specifications = [
        (0, "q"),
        (0, "kv"),
        (0, "attention_out"),
        (0, "gate_up"),
        (0, "mlp_down"),
        (10, "qkv"),
    ]
    selected = []
    for layer, family in specifications:
        matches = [
            chain for chain in payload["chains"]
            if int(chain["layer"]) == layer and chain["family"] == family
        ]
        if len(matches) != 1:
            raise RuntimeError(f"M128_CHAIN_SELECTION_FAIL layer={layer} family={family}")
        selected.append(matches[0])
    if max(int(chain["descriptor_count"]) for chain in selected) != 10:
        raise RuntimeError("M128_MAX_DESCRIPTOR_COVERAGE_FAIL")
    if {int(chain["bits"]) for chain in selected} != {2, 4}:
        raise RuntimeError("M128_BIT_WIDTH_COVERAGE_FAIL")
    if {int(chain["groups"]) for chain in selected} != {40, 64, 152}:
        raise RuntimeError("M128_GROUP_GEOMETRY_COVERAGE_FAIL")
    return selected


def write_chain(
    output,
    ordinal: int,
    chain: dict,
    modules: dict[str, dict],
    handles: list[object],
    values: np.ndarray,
) -> dict:
    groups = int(chain["groups"])
    bits = int(chain["bits"])
    descriptors = chain["descriptors"]
    layer = 0xFFFFFFFF if chain["layer"] is None else int(chain["layer"])
    output.write(
        struct.pack(
            "<IIIIII",
            ordinal,
            layer,
            int(chain["family_code"]),
            len(descriptors),
            groups,
            bits,
        )
    )
    covered = []
    for local, item in enumerate(descriptors):
        module = modules[item["module"]]
        tile = module["tiles"][int(item["tile_index"])]
        words = 1 + 4 * bits
        blocks = int(tile["rows_per_shard"]) // 8
        block = (ordinal * 7 + local * 3 + 1) % blocks
        output.write(struct.pack("<BBBBI", bits, words, groups, 0, block))
        for shard, handle in enumerate(handles):
            for group in range(groups):
                offset = (
                    int(tile["shard_offsets"][shard])
                    + (group * blocks + block) * words * 16
                )
                handle.seek(offset)
                payload = handle.read(words * 16)
                if len(payload) != words * 16:
                    raise RuntimeError("M128_SHORT_WEIGHT_RECORD")
                output.write(payload)
                output.write(bytes((MAX_WORDS - words) * 16))
        covered.append(
            {
                "module": item["module"],
                "tile_index": int(item["tile_index"]),
                "block": block,
            }
        )

    codes, scales = quantize(values, groups)
    for group in range(groups):
        for token in range(TOKENS):
            output.write(codes[token, group].tobytes())
            output.write(np.asarray(scales[token, group], dtype="<f2").tobytes())
            output.write(bytes(14))
    return {
        "ordinal": ordinal,
        "source_chain_index": int(chain["chain_index"]),
        "layer": None if layer == 0xFFFFFFFF else layer,
        "family": chain["family"],
        "family_code": int(chain["family_code"]),
        "bits": bits,
        "groups": groups,
        "descriptor_count": len(descriptors),
        "covered_records": covered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout-root", type=Path, required=True)
    parser.add_argument("--language-contract", type=Path, required=True)
    parser.add_argument("--head-contract", type=Path, required=True)
    parser.add_argument("--golden-result", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M128-M120-real-record-numerical-CSim-fixture",
        "status": "FAIL",
        "classification": "offline bounded fixture build; CSim is a separate gate and no board state is changed",
    }
    language_handles = []
    head_handles = []
    golden_npz = None
    try:
        if sha256_file(args.language_contract) != EXPECTED_LANGUAGE_CONTRACT_SHA256:
            raise RuntimeError("M128_LANGUAGE_CONTRACT_IDENTITY_FAIL")
        if sha256_file(args.head_contract) != EXPECTED_HEAD_CONTRACT_SHA256:
            raise RuntimeError("M128_HEAD_CONTRACT_IDENTITY_FAIL")
        language_contract = json.loads(args.language_contract.read_text(encoding="utf-8"))
        head_contract = json.loads(args.head_contract.read_text(encoding="utf-8"))
        golden_result = json.loads(args.golden_result.read_text(encoding="utf-8"))
        if golden_result.get("status") != "PASS_M120_SAME_QUANTIZED_154_CHAIN_GOLDEN":
            raise RuntimeError("M128_GOLDEN_STATUS_FAIL")
        if sha256_file(args.golden) != golden_result["capture_output_sha256"]:
            raise RuntimeError("M128_GOLDEN_IDENTITY_FAIL")

        language_modules, language_handles, language_manifest = layout_index(
            args.layout_root / "language_fourport"
        )
        head_modules, head_handles, head_manifest = layout_index(
            args.layout_root / "lmhead_fourport"
        )
        selected = select_language_chains(language_contract)
        head_chain = head_contract["chains"][0]
        if int(head_chain["descriptor_count"]) != 10 or int(head_chain["bits"]) != 4:
            raise RuntimeError("M128_HEAD_CHAIN_COVERAGE_FAIL")
        selected.append(head_chain)

        golden_npz = np.load(args.golden, allow_pickle=False)
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        summaries = []
        with args.fixture.open("wb") as output:
            output.write(MAGIC)
            output.write(struct.pack("<IIII", len(selected), 10, TOKENS, VALID_TOKENS))
            for ordinal, chain in enumerate(selected):
                if chain["family"] == "lm_head":
                    columns = np.arange(2560, dtype=np.float32)[None, :]
                    rows = np.arange(1, VALID_TOKENS + 1, dtype=np.float32)[:, None]
                    values = (((columns % 257.0) - 128.0) / 128.0) * (rows / 30.0)
                    summary = write_chain(
                        output, ordinal, chain, head_modules, head_handles, values
                    )
                else:
                    key = f"layer{int(chain['layer']):02d}_{chain['family']}"
                    if key not in golden_npz.files:
                        raise RuntimeError(f"M128_GOLDEN_KEY_MISSING key={key}")
                    values = np.asarray(golden_npz[key], dtype=np.float32)
                    summary = write_chain(
                        output, ordinal, chain, language_modules, language_handles, values
                    )
                    summary["golden_key"] = key
                summaries.append(summary)
            output.flush()
            os.fsync(output.fileno())

        result.update(
            {
                "status": "PASS_M120_REAL_RECORD_CSIM_FIXTURE_BUILT",
                "language_layout_manifest_sha256": sha256_file(
                    args.layout_root / "language_fourport" / "SIXPORT_LAYOUT_MANIFEST.json"
                ),
                "head_layout_manifest_sha256": sha256_file(
                    args.layout_root / "lmhead_fourport" / "SIXPORT_LAYOUT_MANIFEST.json"
                ),
                "golden_result_sha256": sha256_file(args.golden_result),
                "golden_sha256": sha256_file(args.golden),
                "fixture": str(args.fixture),
                "fixture_bytes": args.fixture.stat().st_size,
                "fixture_sha256": sha256_file(args.fixture),
                "chain_count": len(summaries),
                "descriptor_count": sum(item["descriptor_count"] for item in summaries),
                "coverage": {
                    "families": [item["family"] for item in summaries],
                    "bits": sorted({item["bits"] for item in summaries}),
                    "groups": sorted({item["groups"] for item in summaries}),
                    "maximum_descriptor_count": max(item["descriptor_count"] for item in summaries),
                    "includes_split_q_and_kv": True,
                    "includes_w4_lm_head": True,
                    "uses_real_m120_weight_records": True,
                    "uses_m120_same_quantized_family_inputs": True,
                },
                "chains": summaries,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run Vitis HLS 2026.1 numerical CSim with the M89-X2 FP32-scale/accumulation kernel and an independent reference.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same fixture gate; do not run HLS or touch the board."
    finally:
        if golden_npz is not None:
            golden_npz.close()
        for handle in language_handles + head_handles:
            handle.close()
        atomic_json(args.result, result)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)

    if result["status"] != "PASS_M120_REAL_RECORD_CSIM_FIXTURE_BUILT":
        return 1
    print("M128_M120_REAL_RECORD_CSIM_FIXTURE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
