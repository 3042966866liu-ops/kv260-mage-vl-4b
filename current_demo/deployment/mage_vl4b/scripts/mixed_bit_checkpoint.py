#!/usr/bin/env python3
"""Deterministic mixed-bit primitives for the Mage-VL FPGA checkpoint.

The board format packs every eight unsigned low-bit codes into exactly
``bits`` little-endian bytes.  Group scales are persisted as IEEE FP16 and
therefore quantization always uses the *persisted* scale, not a higher precision
temporary.  That makes an unload/reload gate meaningful and matches the data
the PL kernel will consume.

This module deliberately has no transformers or AutoRound dependency.  The
full candidate writer/loader imports these primitives after the format passes
its own unit and real-cache reconstruction gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


FORMAT = "tellme-mage-vl-mixed-bit-v1"
GROUP_SIZE = 64
PACK_BLOCK_CODES = 8


def sha256_file(path: Path, chunk_bytes: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def pack_unsigned_codes(codes: np.ndarray, bits: int) -> bytes:
    """Pack uint codes using a little-endian, eight-code block layout."""

    if bits not in (2, 3, 4):
        raise ValueError(f"unsupported bit width: {bits}")
    flat = np.asarray(codes, dtype=np.uint8).reshape(-1)
    if flat.size % PACK_BLOCK_CODES:
        raise ValueError("code count must be divisible by eight")
    limit = 1 << bits
    if flat.size and int(flat.max()) >= limit:
        raise ValueError(f"code exceeds {bits}-bit range")

    blocks = flat.reshape(-1, PACK_BLOCK_CODES).astype(np.uint64, copy=False)
    shifts = (np.arange(PACK_BLOCK_CODES, dtype=np.uint64) * bits).reshape(1, -1)
    words = np.bitwise_or.reduce(blocks << shifts, axis=1)
    packed = np.empty((words.size, bits), dtype=np.uint8)
    for byte_index in range(bits):
        packed[:, byte_index] = (words >> (8 * byte_index)).astype(np.uint8)
    return packed.tobytes(order="C")


def unpack_unsigned_codes(payload: bytes, bits: int, code_count: int) -> np.ndarray:
    """Inverse of :func:`pack_unsigned_codes`."""

    if bits not in (2, 3, 4):
        raise ValueError(f"unsupported bit width: {bits}")
    if code_count % PACK_BLOCK_CODES:
        raise ValueError("code count must be divisible by eight")
    expected = code_count * bits // 8
    if len(payload) != expected:
        raise ValueError(f"packed byte count {len(payload)} != expected {expected}")

    packed = np.frombuffer(payload, dtype=np.uint8).reshape(-1, bits)
    words = np.zeros(packed.shape[0], dtype=np.uint64)
    for byte_index in range(bits):
        words |= packed[:, byte_index].astype(np.uint64) << (8 * byte_index)
    mask = np.uint64((1 << bits) - 1)
    codes = np.empty((words.size, PACK_BLOCK_CODES), dtype=np.uint8)
    for code_index in range(PACK_BLOCK_CODES):
        codes[:, code_index] = (
            (words >> (bits * code_index)) & mask
        ).astype(np.uint8)
    return codes.reshape(-1)


def pack_orientation_bits(orientations: np.ndarray) -> bytes:
    flat = np.asarray(orientations, dtype=np.uint8).reshape(-1)
    if flat.size and int(flat.max()) > 1:
        raise ValueError("orientation values must be zero or one")
    return np.packbits(flat, bitorder="little").tobytes()


def unpack_orientation_bits(payload: bytes, orientation_count: int) -> np.ndarray:
    expected = math.ceil(orientation_count / 8)
    if len(payload) != expected:
        raise ValueError(f"orientation byte count {len(payload)} != expected {expected}")
    values = np.unpackbits(
        np.frombuffer(payload, dtype=np.uint8), bitorder="little"
    )[:orientation_count]
    return values.astype(np.uint8, copy=False)


def quantize_rows_for_storage(
    torch,
    source,
    bits: int,
    group_size: int = GROUP_SIZE,
):
    """Return unsigned codes, persisted FP16 scales, and reconstructed rows.

    ``source`` must be a two-dimensional floating tensor.  Columns are padded
    to ``group_size``.  Codes use the full-range signed convention
    ``[-2^(b-1), 2^(b-1)-1]`` and are shifted to unsigned only for packing.
    """

    if bits not in (2, 3, 4):
        raise ValueError(f"unsupported bit width: {bits}")
    if source.ndim != 2:
        raise ValueError("source must be two-dimensional")
    if group_size <= 0 or group_size % PACK_BLOCK_CODES:
        raise ValueError("group size must be a positive multiple of eight")

    rows = source.float()
    columns = rows.shape[1]
    padded_columns = math.ceil(columns / group_size) * group_size
    if padded_columns != columns:
        padded = torch.nn.functional.pad(rows, (0, padded_columns - columns))
    else:
        padded = rows
    grouped = padded.reshape(rows.shape[0], -1, group_size)

    qmin = -(1 << (bits - 1))
    qmax = (1 << (bits - 1)) - 1
    minimum = grouped.amin(dim=-1, keepdim=True)
    maximum = grouped.amax(dim=-1, keepdim=True)
    scale_f32 = torch.maximum(
        (-minimum) / float(-qmin),
        maximum / float(qmax),
    ).clamp_min(1e-8)
    # Persist first, then quantize with the value a loader/kernel will see.
    scale_f16 = scale_f32.to(torch.float16)
    effective_scale = scale_f16.float().clamp_min(1e-8)
    signed = torch.round(grouped / effective_scale).clamp(qmin, qmax).to(torch.int8)
    restored = (signed.float() * effective_scale).reshape(rows.shape[0], padded_columns)
    unsigned = (signed.to(torch.int16) - qmin).to(torch.uint8)
    return unsigned, scale_f16.squeeze(-1), restored[:, :columns]


def recover_full_range_rows_for_storage(
    torch,
    source,
    bits: int,
    group_size: int = GROUP_SIZE,
    scale_format: str = "bf16",
    scale_search: str = "endpoints",
):
    """Recover AutoRound full-range symmetric codes from fake-quant weights.

    Full-range symmetric quantization chooses one of two integer lattices per
    group: ``[-half, half-1]`` or ``[-half+1, half]``.  The one-bit orientation
    is persisted beside the FP16 scale.  Two endpoint-derived scale candidates
    are evaluated for each orientation using BF16 reconstruction error.
    """

    if bits not in (2, 3, 4):
        raise ValueError(f"unsupported bit width: {bits}")
    if source.ndim != 2:
        raise ValueError("source must be two-dimensional")
    rows = source.float()
    columns = rows.shape[1]
    padded_columns = math.ceil(columns / group_size) * group_size
    if padded_columns != columns:
        padded = torch.nn.functional.pad(rows, (0, padded_columns - columns))
    else:
        padded = rows
    grouped = padded.reshape(rows.shape[0], -1, group_size)
    minimum = grouped.amin(dim=-1, keepdim=True)
    maximum = grouped.amax(dim=-1, keepdim=True)
    half = 1 << (bits - 1)
    lattices = ((-half, half - 1), (-half + 1, half))

    if scale_format not in ("fp16", "bf16"):
        raise ValueError(f"unsupported scale format: {scale_format}")
    if scale_search not in ("endpoints", "exhaustive"):
        raise ValueError(f"unsupported scale search: {scale_search}")
    scale_dtype = torch.float16 if scale_format == "fp16" else torch.bfloat16
    best_error = torch.full(
        grouped.shape[:-1], float("inf"), dtype=torch.float32, device=grouped.device
    )
    best_scale = torch.zeros_like(best_error, dtype=scale_dtype)
    best_orientation = torch.zeros_like(best_error, dtype=torch.uint8)
    for orientation, (qmin, qmax) in enumerate(lattices):
        negative_codes = (qmin,) if scale_search == "endpoints" else range(qmin, 0)
        positive_codes = (qmax,) if scale_search == "endpoints" else range(1, qmax + 1)
        scale_candidates = [minimum / float(code) for code in negative_codes]
        scale_candidates.extend(maximum / float(code) for code in positive_codes)
        for candidate_scale in scale_candidates:
            stored_scale = candidate_scale.clamp_min(1e-8).to(scale_dtype)
            effective = stored_scale.float().clamp_min(1e-8)
            signed = torch.round(grouped / effective).clamp(qmin, qmax)
            restored = (signed * effective).to(source.dtype).float()
            error = torch.sum((restored - grouped) ** 2, dim=-1)
            update = error < best_error
            best_error = torch.where(update, error, best_error)
            best_scale = torch.where(update, stored_scale.squeeze(-1), best_scale)
            best_orientation = torch.where(
                update,
                torch.full_like(best_orientation, orientation),
                best_orientation,
            )

    selected_scale = best_scale
    orientation = best_orientation
    qmin_tensor = torch.where(orientation.bool(), -half + 1, -half)
    qmax_tensor = torch.where(orientation.bool(), half, half - 1)
    signed = torch.round(grouped / selected_scale.float().unsqueeze(-1).clamp_min(1e-8))
    signed = torch.maximum(
        torch.minimum(signed, qmax_tensor.unsqueeze(-1)), qmin_tensor.unsqueeze(-1)
    ).to(torch.int16)
    restored = (
        signed.float() * selected_scale.float().unsqueeze(-1)
    ).reshape(rows.shape[0], padded_columns)
    unsigned = (signed - qmin_tensor.unsqueeze(-1)).to(torch.uint8)
    return unsigned, selected_scale, orientation, restored[:, :columns].to(source.dtype)


def reconstruct_rows_from_storage(
    torch,
    unsigned_codes: np.ndarray,
    scales_f16: np.ndarray,
    bits: int,
    rows: int,
    columns: int,
    group_size: int = GROUP_SIZE,
):
    padded_columns = math.ceil(columns / group_size) * group_size
    expected_codes = rows * padded_columns
    codes = np.asarray(unsigned_codes, dtype=np.uint8).reshape(-1)
    if codes.size != expected_codes:
        raise ValueError(f"code count {codes.size} != expected {expected_codes}")
    groups_per_row = padded_columns // group_size
    scales = np.asarray(scales_f16, dtype=np.float16).reshape(rows, groups_per_row)
    qmin = -(1 << (bits - 1))
    signed = torch.from_numpy(codes.copy()).to(torch.int16) + qmin
    signed = signed.reshape(rows, groups_per_row, group_size).float()
    scale_tensor = torch.from_numpy(scales.copy()).float().unsqueeze(-1)
    restored = (signed * scale_tensor).reshape(rows, padded_columns)
    return restored[:, :columns]


def reconstruct_full_range_rows_from_storage(
    torch,
    unsigned_codes: np.ndarray,
    scale_bits_u16: np.ndarray,
    orientation_bits: np.ndarray,
    bits: int,
    rows: int,
    columns: int,
    group_size: int = GROUP_SIZE,
    output_dtype=None,
    scale_format: str = "bf16",
):
    padded_columns = math.ceil(columns / group_size) * group_size
    groups_per_row = padded_columns // group_size
    codes = np.asarray(unsigned_codes, dtype=np.uint8).reshape(
        rows, groups_per_row, group_size
    )
    if scale_format not in ("fp16", "bf16"):
        raise ValueError(f"unsupported scale format: {scale_format}")
    scale_dtype = torch.float16 if scale_format == "fp16" else torch.bfloat16
    scale_bits = np.asarray(scale_bits_u16, dtype=np.uint16).reshape(rows, groups_per_row)
    scales = torch.from_numpy(scale_bits.copy()).view(scale_dtype)
    orientations = np.asarray(orientation_bits, dtype=np.uint8).reshape(
        rows, groups_per_row
    )
    half = 1 << (bits - 1)
    qmin = np.where(orientations != 0, -half + 1, -half).astype(np.int16)
    signed = torch.from_numpy(codes.astype(np.int16, copy=False)) + torch.from_numpy(qmin).unsqueeze(-1)
    restored = signed.float() * scales.float().unsqueeze(-1)
    restored = restored.reshape(rows, padded_columns)[:, :columns]
    return restored.to(output_dtype) if output_dtype is not None else restored


def relative_l2(torch, candidate, reference) -> float:
    delta = (candidate.float() - reference.float()).reshape(-1)
    base = reference.float().reshape(-1)
    denominator = float(torch.sum(base * base).item())
    if denominator == 0.0:
        return 0.0 if float(torch.sum(delta * delta).item()) == 0.0 else math.inf
    return math.sqrt(float(torch.sum(delta * delta).item()) / denominator)


def simulate_module_storage_roundtrip(
    torch,
    module,
    bits: int,
    group_size: int = GROUP_SIZE,
    scale_format: str = "fp16",
    row_chunk: int = 32,
    scale_search: str = "endpoints",
) -> dict:
    """Apply the exact code/scale/orientation writer-loader path in memory."""

    weight = module.weight.data
    if weight.ndim != 2:
        raise ValueError("only two-dimensional weights can be packed")
    error_squared = 0.0
    source_squared = 0.0
    max_abs = 0.0
    code_bytes = 0
    scale_bytes = 0
    orientation_bytes = 0
    positive_groups = 0
    group_count = 0
    for row_start in range(0, weight.shape[0], row_chunk):
        source = weight[row_start:row_start + row_chunk].detach().clone()
        codes, scales, orientations, _writer = recover_full_range_rows_for_storage(
            torch, source, bits, group_size, scale_format, scale_search
        )
        flat_codes = codes.cpu().numpy().reshape(-1)
        code_payload = pack_unsigned_codes(flat_codes, bits)
        reloaded_codes = unpack_unsigned_codes(code_payload, bits, flat_codes.size)
        flat_orientations = orientations.cpu().numpy().reshape(-1)
        orientation_payload = pack_orientation_bits(flat_orientations)
        reloaded_orientations = unpack_orientation_bits(
            orientation_payload, flat_orientations.size
        )
        reloaded = reconstruct_full_range_rows_from_storage(
            torch,
            reloaded_codes,
            scales.view(torch.uint16).cpu().numpy(),
            reloaded_orientations,
            bits,
            source.shape[0],
            source.shape[1],
            group_size,
            output_dtype=weight.dtype,
            scale_format=scale_format,
        )
        delta = reloaded.float() - source.float()
        error_squared += float(torch.sum(delta * delta).item())
        source_squared += float(torch.sum(source.float() ** 2).item())
        max_abs = max(max_abs, float(torch.max(torch.abs(delta)).item()))
        weight[row_start:row_start + source.shape[0]].copy_(reloaded)
        code_bytes += len(code_payload)
        scale_bytes += int(scales.numel() * 2)
        orientation_bytes += len(orientation_payload)
        positive_groups += int(np.sum(reloaded_orientations, dtype=np.int64))
        group_count += int(flat_orientations.size)
    return {
        "bits": bits,
        "group_size": group_size,
        "scale_format": scale_format,
        "scale_search": scale_search,
        "parameters": int(weight.numel()),
        "code_bytes": code_bytes,
        "scale_bytes": scale_bytes,
        "orientation_bytes": orientation_bytes,
        "packed_bytes": code_bytes + scale_bytes + orientation_bytes,
        "group_count": group_count,
        "positive_full_range_groups": positive_groups,
        "relative_l2_to_calibrated_weight": (
            math.sqrt(error_squared / source_squared) if source_squared else 0.0
        ),
        "max_abs_to_calibrated_weight": max_abs,
    }


def audit_language_cache(args) -> dict:
    import torch
    from safetensors import safe_open

    cache_dir = args.cache.resolve()
    manifest_path = cache_dir / "CACHE_MANIFEST.json"
    cache_manifest = json.loads(manifest_path.read_text())
    samples = []
    for layer_index, bits in ((0, 2), (10, 4)):
        item = next(
            entry
            for entry in cache_manifest["files"]
            if entry["path"] == f"language-layer-{layer_index:02d}.safetensors"
        )
        shard = cache_dir / item["path"]
        if shard.stat().st_size != item["bytes"] or sha256_file(shard) != item["sha256"]:
            raise RuntimeError(f"cache identity failed: {shard}")
        with safe_open(str(shard), framework="pt", device="cpu") as handle:
            tensor_name = next(name for name in handle.keys() if name.endswith("q_proj.weight"))
            weight = handle.get_tensor(tensor_name)
        row_count = min(args.rows, weight.shape[0])
        source = weight[:row_count].contiguous()
        grouped_source = source.float().reshape(row_count, -1, args.group_size)
        unique_counts = [
            int(torch.unique(group).numel())
            for group in grouped_source.reshape(-1, args.group_size)
        ]
        group_examples = []
        for group in grouped_source.reshape(-1, args.group_size)[:3]:
            values = torch.unique(group).sort().values.tolist()
            group_examples.append({
                "values": [float(value) for value in values],
                "adjacent_differences": [
                    float(values[index + 1] - values[index])
                    for index in range(len(values) - 1)
                ],
            })
        unsigned, scales, orientations, reconstructed = recover_full_range_rows_for_storage(
            torch, source, bits, args.group_size, args.scale_format, args.scale_search
        )
        unsigned_np = unsigned.cpu().numpy().reshape(-1)
        packed = pack_unsigned_codes(unsigned_np, bits)
        unpacked = unpack_unsigned_codes(packed, bits, unsigned_np.size)
        restored = reconstruct_full_range_rows_from_storage(
            torch,
            unpacked,
            scales.view(torch.uint16).cpu().numpy(),
            orientations.cpu().numpy(),
            bits,
            source.shape[0],
            source.shape[1],
            args.group_size,
            output_dtype=source.dtype,
            scale_format=args.scale_format,
        )
        samples.append({
            "layer": layer_index,
            "tensor": tensor_name,
            "bits": bits,
            "rows": row_count,
            "columns": int(source.shape[1]),
            "code_count": int(unsigned_np.size),
            "packed_bytes": len(packed),
            "scale_bytes": int(scales.numel() * 2),
            "orientation_bits": int(orientations.numel()),
            "positive_full_range_groups": int(torch.sum(orientations).item()),
            "source_unique_values_per_group_min": min(unique_counts),
            "source_unique_values_per_group_median": float(np.median(unique_counts)),
            "source_unique_values_per_group_max": max(unique_counts),
            "source_group_examples": group_examples,
            "code_roundtrip_exact": bool(np.array_equal(unsigned_np, unpacked)),
            "writer_loader_max_abs": float(torch.max(torch.abs(restored.float() - reconstructed.float())).item()),
            "relative_l2_to_cached_fake_quant": relative_l2(torch, restored, source),
        })

    passed = all(
        item["code_roundtrip_exact"]
        and item["writer_loader_max_abs"] == 0.0
        and item["relative_l2_to_cached_fake_quant"] <= args.max_relative_l2
        for item in samples
    )
    return {
        "date": "2026-08-28",
        "gate": "mage-vl-mixed-bit-real-cache-reconstruction",
        "status": "PASS" if passed else "FAIL",
        "classification": "real cached language-weight storage-format screen; no checkpoint export or board action",
        "format": FORMAT,
        "cache": str(cache_dir),
        "cache_manifest_sha256": sha256_file(manifest_path),
        "group_size": args.group_size,
        "scale_format": args.scale_format,
        "scale_search": args.scale_search,
        "max_relative_l2": args.max_relative_l2,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-language-cache", action="store_true")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--rows", type=int, default=64)
    parser.add_argument("--group-size", type=int, default=GROUP_SIZE)
    parser.add_argument("--scale-format", choices=("fp16", "bf16"), default="bf16")
    parser.add_argument("--scale-search", choices=("endpoints", "exhaustive"), default="exhaustive")
    parser.add_argument("--max-relative-l2", type=float, default=0.01)
    args = parser.parse_args()
    if not args.audit_language_cache:
        parser.error("select --audit-language-cache")
    if args.cache is None or args.result is None:
        parser.error("--cache and --result are required")

    payload = audit_language_cache(args)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(rendered)
    os.replace(temporary, args.result)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
