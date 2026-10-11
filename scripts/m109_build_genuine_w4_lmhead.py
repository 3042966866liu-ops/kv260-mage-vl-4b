#!/usr/bin/env python3
"""Build a genuine official-source W4/FP16-scale Mage-VL LM-head artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path


ALIGNMENT = 4096
GROUP_SIZE = 64
BITS = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_region(handle, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    handle.seek(offset)
    remaining = length
    while remaining:
        block = handle.read(min(8 << 20, remaining))
        if not block:
            raise EOFError("LM-head blob ended inside a declared section")
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def align(value: int) -> int:
    return (value + ALIGNMENT - 1) & -ALIGNMENT


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--row-chunk", type=int, default=32)
    args = parser.parse_args()
    if args.row_chunk <= 0:
        parser.error("--row-chunk must be positive")

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M109-official-source-genuine-W4-LM-head",
        "status": "FAIL",
        "classification": (
            "offline exact storage artifact and round-trip audit; not a model-quality PASS, "
            "FPGA result, board package, performance result, video result, or Web result"
        ),
    }
    started = time.perf_counter()
    temporary: Path | None = None
    try:
        sys.path.insert(0, str(args.deps.resolve()))
        sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "deployment" / "mage_vl4b" / "scripts").resolve()))
        import numpy as np
        import torch
        from safetensors import safe_open

        from mixed_bit_checkpoint import (
            pack_orientation_bits,
            pack_unsigned_codes,
            reconstruct_full_range_rows_from_storage,
            recover_full_range_rows_for_storage,
            unpack_orientation_bits,
            unpack_unsigned_codes,
        )

        model = args.model.resolve()
        index_path = model / "model.safetensors.index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        shard_name = index.get("weight_map", {}).get("lm_head.weight")
        if not shard_name:
            raise RuntimeError("official index does not contain lm_head.weight")
        shard_path = model / shard_name
        if not shard_path.is_file():
            raise RuntimeError(f"official LM-head shard is missing: {shard_path}")
        print(f"[M109] loading official lm_head.weight from {shard_name}", flush=True)
        with safe_open(str(shard_path), framework="pt", device="cpu") as handle:
            weight = handle.get_tensor("lm_head.weight").contiguous()
        if weight.ndim != 2 or tuple(weight.shape) != (151936, 2560):
            raise RuntimeError(f"unexpected LM-head shape: {tuple(weight.shape)}")
        if weight.dtype != torch.bfloat16:
            raise RuntimeError(f"unexpected LM-head dtype: {weight.dtype}")

        rows, columns = map(int, weight.shape)
        padded_columns = math.ceil(columns / GROUP_SIZE) * GROUP_SIZE
        groups_per_row = padded_columns // GROUP_SIZE
        group_count = rows * groups_per_row
        code_bytes = rows * padded_columns * BITS // 8
        scale_bytes = group_count * 2
        orientation_bytes = math.ceil(group_count / 8)
        code_offset = 0
        scale_offset = align(code_offset + code_bytes)
        orientation_offset = align(scale_offset + scale_bytes)
        blob_bytes = orientation_offset + orientation_bytes

        output = args.output.resolve()
        if output.exists():
            raise FileExistsError(f"refusing to overwrite LM-head artifact: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + f".tmp-{os.getpid()}")
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir()
        blob_path = temporary / "lm_head_w4.bin"

        error_squared = 0.0
        source_squared = 0.0
        max_abs = 0.0
        positive_groups = 0
        code_cursor = scale_cursor = orientation_cursor = 0
        pack_started = time.perf_counter()
        with blob_path.open("w+b") as blob:
            blob.truncate(blob_bytes)
            for row_start in range(0, rows, args.row_chunk):
                source = weight[row_start : row_start + args.row_chunk]
                codes, scales, orientations, _ = recover_full_range_rows_for_storage(
                    torch,
                    source,
                    bits=BITS,
                    group_size=GROUP_SIZE,
                    scale_format="fp16",
                    scale_search="exhaustive",
                )
                flat_codes = codes.cpu().numpy().reshape(-1)
                flat_orientations = orientations.cpu().numpy().reshape(-1)
                code_payload = pack_unsigned_codes(flat_codes, BITS)
                scale_payload = scales.view(torch.uint16).cpu().numpy().tobytes()
                orientation_payload = pack_orientation_bits(flat_orientations)

                blob.seek(code_offset + code_cursor)
                blob.write(code_payload)
                blob.seek(scale_offset + scale_cursor)
                blob.write(scale_payload)
                blob.seek(orientation_offset + orientation_cursor)
                blob.write(orientation_payload)

                restored = reconstruct_full_range_rows_from_storage(
                    torch,
                    unpack_unsigned_codes(code_payload, BITS, flat_codes.size),
                    np.frombuffer(scale_payload, dtype=np.uint16),
                    unpack_orientation_bits(orientation_payload, flat_orientations.size),
                    bits=BITS,
                    rows=int(source.shape[0]),
                    columns=columns,
                    group_size=GROUP_SIZE,
                    output_dtype=torch.bfloat16,
                    scale_format="fp16",
                )
                delta = restored.float() - source.float()
                error_squared += float(torch.sum(delta * delta))
                source_squared += float(torch.sum(source.float() ** 2))
                max_abs = max(max_abs, float(torch.max(torch.abs(delta))))
                positive_groups += int(np.sum(flat_orientations, dtype=np.int64))

                code_cursor += len(code_payload)
                scale_cursor += len(scale_payload)
                orientation_cursor += len(orientation_payload)
                done_rows = row_start + int(source.shape[0])
                if done_rows == rows or done_rows % 16384 == 0:
                    print(f"[M109] packed rows {done_rows}/{rows}", flush=True)

            if code_cursor != code_bytes:
                raise RuntimeError("LM-head code byte count mismatch")
            if scale_cursor != scale_bytes:
                raise RuntimeError("LM-head scale byte count mismatch")
            if orientation_cursor != orientation_bytes:
                raise RuntimeError("LM-head orientation byte count mismatch")
            sections = {
                "codes": {
                    "offset": code_offset,
                    "bytes": code_bytes,
                    "sha256": hash_region(blob, code_offset, code_bytes),
                },
                "scales": {
                    "offset": scale_offset,
                    "bytes": scale_bytes,
                    "sha256": hash_region(blob, scale_offset, scale_bytes),
                },
                "orientations": {
                    "offset": orientation_offset,
                    "bytes": orientation_bytes,
                    "sha256": hash_region(blob, orientation_offset, orientation_bytes),
                },
            }
            blob.flush()
            os.fsync(blob.fileno())

        manifest = {
            "format": "tellme-mage-vl-genuine-w4-lmhead-v1",
            "model": "microsoft/Mage-VL",
            "source": {
                "checkpoint": str(model),
                "index_sha256": sha256_file(index_path),
                "shard": shard_name,
                "shard_sha256": sha256_file(shard_path),
                "tensor": "lm_head.weight",
                "shape": [rows, columns],
                "dtype": "bfloat16",
            },
            "quantization": {
                "bits": BITS,
                "group_size": GROUP_SIZE,
                "symmetric_full_range": True,
                "scale_format": "fp16",
                "scale_search": "exhaustive",
                "orientation_bit": True,
            },
            "blob": {
                "path": blob_path.name,
                "bytes": blob_path.stat().st_size,
                "sha256": sha256_file(blob_path),
                "sections": sections,
            },
            "groups_per_row": groups_per_row,
            "group_count": group_count,
            "roundtrip": {
                "finite": math.isfinite(error_squared),
                "relative_l2_to_official_bf16": math.sqrt(error_squared / source_squared),
                "max_abs_to_official_bf16": max_abs,
                "positive_orientation_groups": positive_groups,
            },
            "pack_ms": (time.perf_counter() - pack_started) * 1000.0,
        }
        manifest_path = temporary / "LM_HEAD_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output)
        temporary = None
        result.update(
            {
                "status": "PASS_GENUINE_OFFICIAL_SOURCE_W4_LMHEAD_ARTIFACT_ONLY",
                "artifact": str(output),
                "manifest_sha256": sha256_file(output / "LM_HEAD_MANIFEST.json"),
                "blob_sha256": manifest["blob"]["sha256"],
                "blob_bytes": manifest["blob"]["bytes"],
                "code_bytes": code_bytes,
                "scale_bytes": scale_bytes,
                "orientation_bytes": orientation_bytes,
                "roundtrip": manifest["roundtrip"],
                "next_gate": (
                    "Load this exact W4 head with M56 plus the M108 selected calibrated W4 "
                    "cache and run the frozen multi-case text/video software-quality gate."
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline LM-head artifact gate; do not stage a board candidate."
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
    finally:
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_GENUINE_OFFICIAL_SOURCE_W4_LMHEAD_ARTIFACT_ONLY":
        return 1
    print("M109_GENUINE_W4_LMHEAD_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
