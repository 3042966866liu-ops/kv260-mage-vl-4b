#!/usr/bin/env python3
"""Gate-locked streaming extraction of the accepted M120 W3 embedding."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


EXPECTED_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
EMBEDDING_NAME = "model.language_model.embed_tokens.weight"
BUILD_ID = "0x4D395832"
EXPECTED_FIXED_TEXT_RESULT = "deployment/mage_vl4b/M179_M120_FIXED_TEXT_BOARD_RESULT_01.json"
EXPECTED_FIXED_TEXT_RESULT_SHA256 = "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"
EXPECTED_TEXT_PACKAGE_MANIFEST = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--row-chunk", type=int, default=32)
    args = parser.parse_args()
    result = {
        "date": "2026-09-01",
        "gate": "M148-M120-W3-full-embedding-extraction",
        "status": "FAIL",
        "classification": "gate-locked offline artifact extraction; never board or video deployment evidence",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    temporary = args.output.with_suffix(args.output.suffix + f".tmp-{os.getpid()}")
    try:
        if args.row_chunk <= 0:
            raise ValueError("row chunk must be positive")
        board = json.loads(args.board_gate.read_text(encoding="utf-8"))
        fixed = board.get("latest_m120_fixed_text_board_gate", {})
        if not isinstance(fixed, dict) or fixed.get("status") != "PASS":
            raise RuntimeError("M148_LOCKED_UNTIL_M120_FIXED_TEXT_BOARD_E2E_PASS")
        if str(fixed.get("candidate_build_id", "")).lower() != BUILD_ID.lower():
            raise RuntimeError("M148 fixed-text Build ID mismatch")
        if fixed.get("formal_result") != EXPECTED_FIXED_TEXT_RESULT:
            raise RuntimeError("M148 fixed-text formal-result path mismatch")
        if fixed.get("formal_result_sha256") != EXPECTED_FIXED_TEXT_RESULT_SHA256:
            raise RuntimeError("M148 fixed-text formal-result declaration mismatch")
        if fixed.get("package_manifest_sha256") != EXPECTED_TEXT_PACKAGE_MANIFEST:
            raise RuntimeError("M148 fixed-text package identity mismatch")
        if fixed.get("fpga_execution_proved") is not True or fixed.get("cpu_linear_fallback") is not False:
            raise RuntimeError("M148 requires real FPGA execution with no CPU linear fallback")
        if fixed.get("reference_match") is not True or int(fixed.get("expected_calls", -1)) != 162:
            raise RuntimeError("M148 fixed-text numerical/call proof mismatch")
        formal_path = args.repo.resolve() / EXPECTED_FIXED_TEXT_RESULT
        if sha256_file(formal_path) != EXPECTED_FIXED_TEXT_RESULT_SHA256:
            raise RuntimeError("M148 fixed-text formal-result bytes mismatch")

        checkpoint = args.checkpoint.resolve()
        manifest_path = checkpoint / "CHECKPOINT_MANIFEST.json"
        if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("M120 checkpoint manifest identity mismatch")
        packed = json.loads(manifest_path.read_text(encoding="utf-8"))
        blob_info = packed["blob"]
        blob_path = checkpoint / blob_info["path"]
        if blob_info.get("sha256") != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M120 blob declaration mismatch")
        if blob_path.stat().st_size != int(blob_info["bytes"]):
            raise RuntimeError("M120 blob size mismatch")
        entries = [entry for entry in packed["entries"] if entry["name"] == EMBEDDING_NAME]
        if len(entries) != 1:
            raise RuntimeError("M120 embedding entry closure mismatch")
        entry = entries[0]
        if entry.get("kind") != "packed" or entry.get("shape") != [151936, 2560]:
            raise RuntimeError("M120 embedding geometry mismatch")
        if int(entry.get("bits", -1)) != 3 or int(entry.get("group_size", -1)) != 64:
            raise RuntimeError("M120 embedding is not W3-G64")

        scripts_root = args.repo.resolve() / "deployment" / "mage_vl4b" / "scripts"
        sys.path.insert(0, str(scripts_root))
        import numpy as np
        import torch
        from mixed_bit_checkpoint import (
            reconstruct_full_range_rows_from_storage,
            unpack_orientation_bits,
            unpack_unsigned_codes,
        )

        rows, columns = entry["shape"]
        bits = int(entry["bits"])
        groups_per_row = int(entry["padded_columns"]) // int(entry["group_size"])
        sections = entry["sections"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        written = 0
        with blob_path.open("rb") as blob, temporary.open("wb") as output:
            blob.seek(int(sections["orientations"]["offset"]))
            orientations = unpack_orientation_bits(
                blob.read(int(sections["orientations"]["bytes"])), int(entry["group_count"])
            )
            for row_start in range(0, rows, args.row_chunk):
                chunk_rows = min(args.row_chunk, rows - row_start)
                code_count = chunk_rows * int(entry["padded_columns"])
                code_offset = row_start * int(entry["padded_columns"]) * bits // 8
                code_bytes = code_count * bits // 8
                scale_offset = row_start * groups_per_row * 2
                scale_bytes = chunk_rows * groups_per_row * 2
                blob.seek(int(sections["codes"]["offset"]) + code_offset)
                codes = unpack_unsigned_codes(blob.read(code_bytes), bits, code_count)
                blob.seek(int(sections["scales"]["offset"]) + scale_offset)
                scale_bits = np.frombuffer(blob.read(scale_bytes), dtype=np.uint16)
                orientation_start = row_start * groups_per_row
                restored = reconstruct_full_range_rows_from_storage(
                    torch,
                    codes,
                    scale_bits,
                    orientations[orientation_start:orientation_start + chunk_rows * groups_per_row],
                    bits,
                    chunk_rows,
                    columns,
                    int(entry["group_size"]),
                    output_dtype=torch.bfloat16,
                    scale_format=packed["scale_format"],
                )
                payload = restored.to(torch.float16).contiguous().view(torch.uint8).numpy().tobytes()
                output.write(payload)
                digest.update(payload)
                written += len(payload)
            output.flush()
            os.fsync(output.fileno())
        expected_bytes = rows * columns * 2
        if written != expected_bytes or temporary.stat().st_size != expected_bytes:
            raise RuntimeError(f"M120 embedding output size mismatch {written} != {expected_bytes}")
        os.replace(temporary, args.output)
        output_sha = digest.hexdigest()
        if sha256_file(args.output) != output_sha:
            raise RuntimeError("M120 embedding post-write hash mismatch")
        result.update(
            {
                "status": "PASS",
                "build_id_gate": BUILD_ID,
                "fixed_text_formal_result": EXPECTED_FIXED_TEXT_RESULT,
                "fixed_text_formal_result_sha256": EXPECTED_FIXED_TEXT_RESULT_SHA256,
                "fixed_text_package_manifest_sha256": EXPECTED_TEXT_PACKAGE_MANIFEST,
                "source_checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "source_blob_sha256": EXPECTED_BLOB_SHA256,
                "embedding_name": EMBEDDING_NAME,
                "source_bits": bits,
                "source_group_size": int(entry["group_size"]),
                "shape": [rows, columns],
                "output": str(args.output.resolve()),
                "output_format": "fp16-rowmajor-dequantized-from-M120-W3",
                "output_bytes": expected_bytes,
                "output_sha256": output_sha,
                "row_chunk": args.row_chunk,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Build a clean M120 video candidate and re-run all offline host/video contracts before any COM3 video action.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Keep extraction locked or correct this same offline extraction gate."
    finally:
        if temporary.exists():
            temporary.unlink()
    atomic_json(args.manifest, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M148_M120_W3_EMBEDDING_EXTRACTION_PASS" if result["status"] == "PASS" else "M148_M120_W3_EMBEDDING_EXTRACTION_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
