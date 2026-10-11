#!/usr/bin/env python3
"""Build the clean M120 video candidate after the fixed-text board gate.

The script is intentionally locked before inspecting or creating its output.
It copies only a fixed whitelist, independently rehashes every copied file,
replaces all stale M89-X1/M79 language components, and publishes the package
manifest hash through a separate PACKAGE_READY.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "deployment/mage_vl4b/m90_video_board_candidate"
REBASE = ROOT / "deployment/mage_vl4b/m151_m120_video_rebase_source"
TEXT = ROOT / "deployment/mage_vl4b/m175_m120_fixed_text_candidate"
VISION = ROOT / "deployment/mage_vl4b/artifacts/m90_vision_w4_fourport"
M79_AUX = ROOT / "deployment/mage_vl4b/artifacts/M79-full-text-aux"
OUTPUT = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
EXPECTED_BUILD_ID = "0x4D395832"
EXPECTED_OLD_MANIFEST = "dc2aa3a67b0b95039ce5b193b81e7b0eb72ae236d33aee7396b5e28e4612d2da"
EXPECTED_TEXT_PACKAGE_MANIFEST = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"
EXPECTED_FIXED_TEXT_RESULT = ROOT / "deployment/mage_vl4b/M179_M120_FIXED_TEXT_BOARD_RESULT_01.json"
EXPECTED_FIXED_TEXT_RESULT_SHA256 = "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"
EXPECTED_M175_BOARD_RUNTIME_SHA256 = "5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201"
EXPECTED_VISION_MANIFEST = "2d9bea77b8868d24fa7775886feb1b9c88b8e768d51b2e192802a439060b03c1"
OLD_SELECTED = (
    "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
    "auxiliary/m90_vision_raw_bf16.bin",
    "board_preprocess.py",
    "fixtures/m56_w4_vision_merged_bf16.npz",
    "fixtures/m56_w4_vision_merged_cpu_bf16.npz",
    "fixtures/official_four_frame_processor.npz",
    "fixtures/official_vision_merged_bf16.npz",
    "ps_vision_runtime.py",
    "static/style.css",
    "test_board_preprocess.py",
    "test_ps_vision_runtime.py",
    "test_ps_vision_weight_decode.py",
    "test_video_prompt_and_splice.py",
    "test_video_request.py",
    "video_prompt.py",
    "video_request.py",
)
TEXT_RUNTIME_SELECTED = (
    "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
    "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
    "overlay/m120_m89x2_t32.bit",
    "overlay/m120_m89x2_t32.hwh",
    "runtime/board_runtime.py",
    "runtime/contract_runtime.py",
    "runtime/m120_board_env_preflight.py",
    "runtime/support/reserved_ddr_pool.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def require_fixed_text(board_path: Path) -> tuple[dict[str, Any], str]:
    board = load(board_path)
    fixed = board.get("latest_m120_fixed_text_board_gate")
    if not isinstance(fixed, dict) or fixed.get("status") != "PASS":
        raise RuntimeError("M181_LOCKED_UNTIL_M179_FIXED_TEXT_BOARD_E2E_PASS")
    if str(fixed.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID.lower():
        raise RuntimeError("M181 fixed-text Build ID mismatch")
    if fixed.get("formal_result") != EXPECTED_FIXED_TEXT_RESULT.relative_to(ROOT).as_posix():
        raise RuntimeError("M181 fixed-text formal-result path mismatch")
    if fixed.get("formal_result_sha256") != EXPECTED_FIXED_TEXT_RESULT_SHA256:
        raise RuntimeError("M181 fixed-text formal-result declaration mismatch")
    if sha256(EXPECTED_FIXED_TEXT_RESULT) != EXPECTED_FIXED_TEXT_RESULT_SHA256:
        raise RuntimeError("M181 fixed-text formal-result bytes mismatch")
    if fixed.get("package_manifest_sha256") != EXPECTED_TEXT_PACKAGE_MANIFEST:
        raise RuntimeError("M181 fixed-text package identity mismatch")
    if fixed.get("fpga_execution_proved") is not True or fixed.get("cpu_linear_fallback") is not False:
        raise RuntimeError("M181 requires real FPGA execution with no CPU linear fallback")
    if fixed.get("reference_match") is not True or int(fixed.get("expected_calls", -1)) != 162:
        raise RuntimeError("M181 fixed-text numerical/call proof mismatch")
    if board.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M153 stable rollback prerequisite failed")
    return fixed, sha256(board_path)


def require_embedding(manifest_path: Path, embedding_path: Path) -> tuple[dict[str, Any], str]:
    result = load(manifest_path)
    if result.get("gate") != "M148-M120-W3-full-embedding-extraction" or result.get("status") != "PASS":
        raise RuntimeError("M153 requires the real M148 embedding extraction PASS")
    if result.get("build_id_gate") != EXPECTED_BUILD_ID:
        raise RuntimeError("M148 Build ID identity mismatch")
    if int(result.get("source_bits", -1)) != 3 or int(result.get("source_group_size", -1)) != 64:
        raise RuntimeError("M148 embedding is not M120 W3-G64")
    if int(result.get("output_bytes", -1)) != 777_912_320:
        raise RuntimeError("M148 embedding byte count mismatch")
    if embedding_path.stat().st_size != int(result["output_bytes"]):
        raise RuntimeError("M148 embedding file size mismatch")
    if sha256(embedding_path) != result.get("output_sha256"):
        raise RuntimeError("M148 embedding file hash mismatch")
    return result, sha256(manifest_path)


def copy_verified(source: Path, target: Path, expected_sha: str, expected_bytes: int | None = None) -> dict[str, Any]:
    if not source.is_file():
        raise RuntimeError(f"source file absent: {source}")
    if expected_bytes is not None and source.stat().st_size != expected_bytes:
        raise RuntimeError(f"source byte mismatch: {source}")
    if sha256(source) != expected_sha:
        raise RuntimeError(f"source hash mismatch: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError(f"refusing to overwrite package member: {target}")
    shutil.copyfile(source, target)
    if target.stat().st_size != source.stat().st_size or sha256(target) != expected_sha:
        raise RuntimeError(f"destination hash mismatch: {target}")
    return {"path": target.as_posix(), "bytes": target.stat().st_size, "sha256": expected_sha}


def add(records: list[dict[str, Any]], source: Path, staging: Path, relative: str,
        expected_sha: str, expected_bytes: int | None = None, origin: str | None = None) -> None:
    copied = copy_verified(source, staging / relative, expected_sha, expected_bytes)
    copied["path"] = relative
    copied["origin"] = origin or str(source.resolve())
    records.append(copied)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--board-gate", type=Path,
        default=ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json",
    )
    parser.add_argument("--embedding-manifest", type=Path, required=True)
    parser.add_argument("--embedding", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    # This must remain the first external-state gate.  No destination or large
    # source tree is inspected before the real fixed-text board PASS.
    fixed, board_sha = require_fixed_text(args.board_gate.resolve())
    embedding, embedding_manifest_sha = require_embedding(
        args.embedding_manifest.resolve(), args.embedding.resolve()
    )
    output = args.output.resolve()
    staging = output.with_name(f".{output.name}.partial")
    if output.exists() or staging.exists():
        raise RuntimeError("clean M181 output required; refusing existing output/staging")
    staging.mkdir(parents=True)
    records: list[dict[str, Any]] = []

    old_manifest_path = OLD / "CANDIDATE_MANIFEST.json"
    if sha256(old_manifest_path) != EXPECTED_OLD_MANIFEST:
        raise RuntimeError("old M90 manifest identity drift")
    old_manifest = load(old_manifest_path)
    old_files = {item["path"]: item for item in old_manifest["candidate_files"]}
    for relative in OLD_SELECTED:
        item = old_files[relative]
        add(records, OLD / relative, staging, relative, item["sha256"], int(item["bytes"]), "M90 verified immutable host/vision component")

    payload_manifest_path = OLD / "ps_vision_payload/PAYLOAD_MANIFEST.json"
    payload = load(payload_manifest_path)
    if payload.get("status") != "PASS" or payload.get("route") != "PS BF16 visual tower + M89-X FPGA language/head":
        raise RuntimeError("PS vision payload is not the accepted BF16 payload")
    for item in payload["files"]:
        relative = f"ps_vision_payload/{item['path']}"
        add(records, OLD / relative, staging, relative, item["sha256"], int(item["bytes"]), "immutable PS BF16 vision payload")
    rebased_payload = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate": "M181-M120-PS-high-precision-vision-payload",
        "status": "PASS",
        "route": "PS BF16 visual tower + M120/M89X2 FPGA language/head",
        "source_payload_manifest_sha256": sha256(payload_manifest_path),
        "files": payload["files"],
        "tensor_count": payload["tensor_count"],
        "tensor_bytes": payload["tensor_bytes"],
        "rejected_route": payload["rejected_route"],
        "stable_rollback_preserved": True,
    }
    rebased_payload_path = staging / "ps_vision_payload/PAYLOAD_MANIFEST.json"
    atomic_json(rebased_payload_path, rebased_payload)
    records.append({"path": "ps_vision_payload/PAYLOAD_MANIFEST.json", "bytes": rebased_payload_path.stat().st_size, "sha256": sha256(rebased_payload_path), "origin": "M181 metadata rebase over immutable PS BF16 payload"})

    vision_manifest_path = VISION / "SIXPORT_LAYOUT_MANIFEST.json"
    if sha256(vision_manifest_path) != EXPECTED_VISION_MANIFEST:
        raise RuntimeError("immutable vision layout manifest drift")
    vision_manifest = load(vision_manifest_path)
    for item in vision_manifest["files"]:
        add(records, VISION / item["path"], staging, f"vision_layout/{item['path']}", item["sha256"], int(item["bytes"]), "immutable M90 W4 vision layout")
    add(records, vision_manifest_path, staging, "vision_layout/SIXPORT_LAYOUT_MANIFEST.json", EXPECTED_VISION_MANIFEST, origin="immutable M90 W4 vision layout manifest")

    text_manifest_path = TEXT / "PACKAGE_MANIFEST.json"
    if sha256(text_manifest_path) != EXPECTED_TEXT_PACKAGE_MANIFEST:
        raise RuntimeError("M175 null-safe text package manifest drift")
    text_manifest = load(text_manifest_path)
    text_files = {item["path"]: item for item in text_manifest["files"]}
    text_slice_files = []
    for relative in TEXT_RUNTIME_SELECTED:
        item = text_files.get(relative)
        if item is None:
            raise RuntimeError(f"M175 null-safe text runtime member missing: {relative}")
        if relative == "runtime/board_runtime.py" and item["sha256"] != EXPECTED_M175_BOARD_RUNTIME_SHA256:
            raise RuntimeError("M175 null-safe board runtime identity mismatch")
        add(records, TEXT / relative, staging, f"text_runtime/{relative}", item["sha256"], int(item["bytes"]), "M175 null-safe M120 text runtime whitelist")
        text_slice_files.append({"path": relative, "bytes": int(item["bytes"]), "sha256": item["sha256"]})
    text_slice_manifest = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate": "M181-M120-video-text-runtime-slice",
        "status": "PASS",
        "build_id": EXPECTED_BUILD_ID,
        "source_package_manifest_sha256": EXPECTED_TEXT_PACKAGE_MANIFEST,
        "files": text_slice_files,
        "fixed_prompt_auxiliary_included": False,
        "layer0_reference_fixture_included": False,
        "lmhead_null_layer_safe": True,
        "unsafe_optional_layer_conversion_count": 0,
    }
    text_slice_path = staging / "text_runtime/M181_TEXT_RUNTIME_SLICE_MANIFEST.json"
    atomic_json(text_slice_path, text_slice_manifest)
    records.append({"path": "text_runtime/M181_TEXT_RUNTIME_SLICE_MANIFEST.json", "bytes": text_slice_path.stat().st_size, "sha256": sha256(text_slice_path), "origin": "generated by M181 correction"})

    for relative in ("video_language_runtime.py", "video_server.py", "static/index.html", "static/app.js"):
        source = REBASE / relative
        add(records, source, staging, relative, sha256(source), origin="M151/M152 rebased source")

    old_aux = load(M79_AUX / "M79_FULL_TEXT_AUX_MANIFEST.json")
    norms = old_aux["norms"]
    add(records, M79_AUX / norms["path"], staging, f"text_auxiliary/{norms['path']}", norms["sha256"], int(norms["bytes"]), "identity-retained text norms")
    for item in old_aux["tokenizer_files"]:
        add(records, M79_AUX / item["path"], staging, f"text_auxiliary/{item['path']}", item["sha256"], int(item["bytes"]), "identity-retained tokenizer")
    add(records, args.embedding.resolve(), staging, "text_auxiliary/embedding.fp16.rowmajor.bin", embedding["output_sha256"], int(embedding["output_bytes"]), "M148 dequantized M120 W3 embedding")

    text_aux_manifest = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate": "M181-M120-text-auxiliary",
        "status": "PASS",
        "build_id": EXPECTED_BUILD_ID,
        "embedding": {
            "path": "embedding.fp16.rowmajor.bin",
            "bytes": int(embedding["output_bytes"]),
            "sha256": embedding["output_sha256"],
            "shape": [151936, 2560],
            "dtype": "float16",
            "source_bits": 3,
            "source_group_size": 64,
            "m148_manifest_sha256": embedding_manifest_sha,
        },
        "norms": {"path": norms["path"], "bytes": int(norms["bytes"]), "sha256": norms["sha256"]},
        "tokenizer_files": old_aux["tokenizer_files"],
    }
    text_aux_path = staging / "text_auxiliary/M151_M120_TEXT_AUX_MANIFEST.json"
    atomic_json(text_aux_path, text_aux_manifest)
    records.append({"path": "text_auxiliary/M151_M120_TEXT_AUX_MANIFEST.json", "bytes": text_aux_path.stat().st_size, "sha256": sha256(text_aux_path), "origin": "generated by M181"})

    forbidden = [p.relative_to(staging).as_posix() for p in staging.rglob("*") if "__pycache__" in p.parts or p.suffix == ".pyc" or p.name.endswith(".partial")]
    if forbidden:
        raise RuntimeError(f"forbidden package paths present: {forbidden}")
    stale_fixed = [
        p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file() and (
            p.relative_to(staging).as_posix().startswith("text_runtime/auxiliary/")
            or p.relative_to(staging).as_posix().startswith("text_runtime/reference/")
            or p.name in {"m77_text_aux_fp16.npz", "M77_TEXT_AUX_MANIFEST.json", "m143_m120_layer0_boundaries.npz"}
        )
    ]
    if stale_fixed:
        raise RuntimeError(f"fixed-prompt/Layer-0 auxiliary leaked into video package: {stale_fixed}")
    paths = [item["path"] for item in records]
    if len(paths) != len(set(paths)):
        raise RuntimeError("duplicate package path")

    package = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate": "M181-M120-clean-video-board-package",
        "status": "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED",
        "build_id": EXPECTED_BUILD_ID,
        "kernel": "mage_m120_m89x2_0",
        "weight_mode": "staged-low-cma",
        "fixed_text_board_gate_sha256": board_sha,
        "fixed_text_gate": fixed,
        "m148_embedding_manifest_sha256": embedding_manifest_sha,
        "m175_null_safe_text_package_manifest_sha256": EXPECTED_TEXT_PACKAGE_MANIFEST,
        "m179_fixed_text_result_sha256": EXPECTED_FIXED_TEXT_RESULT_SHA256,
        "vision_layout_manifest_sha256": EXPECTED_VISION_MANIFEST,
        "language_layout_manifest_sha256": "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d",
        "lm_head_layout_manifest_sha256": "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef",
        "frozen_849_token_prefill_calls": 4166,
        "decode_calls_per_subsequent_token": 162,
        "files": sorted(records, key=lambda item: item["path"]),
        "file_count": len(records),
        "total_file_bytes": sum(int(item["bytes"]) for item in records),
        "forbidden_cache_path_count": 0,
        "forbidden_stale_fixed_text_auxiliary_count": 0,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
        "video_board_executed": False,
        "web_deployed": False,
    }
    package_path = staging / "PACKAGE_MANIFEST.json"
    atomic_json(package_path, package)
    package_sha = sha256(package_path)
    ready = {
        "status": "READY",
        "build_id": EXPECTED_BUILD_ID,
        "package_manifest_sha256": package_sha,
        "file_count": len(records),
        "total_file_bytes": package["total_file_bytes"],
    }
    atomic_json(staging / "PACKAGE_READY.json", ready)
    os.replace(staging, output)
    print(json.dumps({"gate": package["gate"], "status": package["status"], "output": str(output), "package_manifest_sha256": package_sha, "file_count": len(records), "total_file_bytes": package["total_file_bytes"]}, indent=2))
    print("M181_M120_CLEAN_VIDEO_PACKAGE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
