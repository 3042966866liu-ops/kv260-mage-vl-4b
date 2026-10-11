#!/usr/bin/env python3
"""Atomic writer and hash-verified loader for Mage-VL mixed-bit weights."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import numpy as np

from mixed_bit_checkpoint import (
    FORMAT,
    GROUP_SIZE,
    pack_orientation_bits,
    pack_unsigned_codes,
    reconstruct_full_range_rows_from_storage,
    recover_full_range_rows_for_storage,
    sha256_file,
    unpack_orientation_bits,
    unpack_unsigned_codes,
)


ARTIFACT_FORMAT = f"{FORMAT}-artifact-v1"
DEFAULT_ALIGNMENT = 4096


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise ValueError("alignment must be a positive power of two")
    return (value + alignment - 1) & -alignment


def _dtype_name(torch, dtype) -> str:
    mapping = {
        torch.bfloat16: "bfloat16",
        torch.float16: "float16",
        torch.float32: "float32",
    }
    if dtype not in mapping:
        raise TypeError(f"unsupported parameter dtype: {dtype}")
    return mapping[dtype]


def _dtype_from_name(torch, name: str):
    mapping = {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }
    if name not in mapping:
        raise TypeError(f"unsupported stored dtype: {name}")
    return mapping[name]


def _hash_region(handle, offset: int, length: int, chunk_bytes: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    handle.seek(offset)
    remaining = length
    while remaining:
        payload = handle.read(min(remaining, chunk_bytes))
        if not payload:
            raise EOFError("checkpoint blob ended inside a declared region")
        digest.update(payload)
        remaining -= len(payload)
    return digest.hexdigest()


def _plan_layout(torch, model, storage_targets: dict[str, int], alignment: int) -> tuple[list[dict], int]:
    parameters = dict(model.named_parameters())
    expected_low_bit_names = {f"{name}.weight" for name in storage_targets}
    missing = sorted(expected_low_bit_names - set(parameters))
    if missing:
        raise RuntimeError(f"packed targets absent from model parameters: {missing[:3]}")

    entries: list[dict] = []
    cursor = 0
    for name, parameter in parameters.items():
        shape = [int(value) for value in parameter.shape]
        module_name = name.removesuffix(".weight")
        if name in expected_low_bit_names:
            if parameter.ndim != 2:
                raise ValueError(f"packed parameter must be two-dimensional: {name}")
            bits = int(storage_targets[module_name])
            rows, columns = shape
            padded_columns = math.ceil(columns / GROUP_SIZE) * GROUP_SIZE
            group_count = rows * padded_columns // GROUP_SIZE
            code_bytes = rows * padded_columns * bits // 8
            scale_bytes = group_count * 2
            orientation_bytes = math.ceil(group_count / 8)
            sections = {}
            for section_name, section_bytes in (
                ("codes", code_bytes),
                ("scales", scale_bytes),
                ("orientations", orientation_bytes),
            ):
                cursor = align_up(cursor, alignment)
                sections[section_name] = {"offset": cursor, "bytes": section_bytes}
                cursor += section_bytes
            entries.append({
                "name": name,
                "module": module_name,
                "kind": "packed",
                "shape": shape,
                "dtype": _dtype_name(torch, parameter.dtype),
                "bits": bits,
                "group_size": GROUP_SIZE,
                "padded_columns": padded_columns,
                "group_count": group_count,
                "sections": sections,
            })
        else:
            cursor = align_up(cursor, alignment)
            byte_count = int(parameter.numel() * parameter.element_size())
            entries.append({
                "name": name,
                "kind": "raw",
                "shape": shape,
                "dtype": _dtype_name(torch, parameter.dtype),
                "section": {"offset": cursor, "bytes": byte_count},
            })
            cursor += byte_count
    return entries, cursor


def write_packed_checkpoint(
    torch,
    model,
    storage_targets: dict[str, int],
    output_dir: Path,
    *,
    source_checkpoint: str,
    checkpoint_config_sha256: str,
    checkpoint_index_sha256: str,
    scale_format: str = "fp16",
    scale_search: str = "endpoints",
    scale_search_overrides: dict[str, str] | None = None,
    row_chunk: int = 32,
    alignment: int = DEFAULT_ALIGNMENT,
    apply_reconstructed: bool = True,
) -> dict:
    """Write a complete parameter artifact, then atomically publish its directory."""

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite packed checkpoint: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_dir.with_name(f"{output_dir.name}.tmp-{os.getpid()}")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir()
    blob_path = temporary / "weights.bin"
    entries, blob_bytes = _plan_layout(torch, model, storage_targets, alignment)
    parameters = dict(model.named_parameters())
    scale_search_overrides = scale_search_overrides or {}
    unknown_overrides = sorted(set(scale_search_overrides) - set(storage_targets))
    if unknown_overrides:
        raise RuntimeError(
            f"scale-search overrides are not packed targets: {unknown_overrides[:3]}"
        )
    try:
        with blob_path.open("w+b") as blob:
            blob.truncate(blob_bytes)
            for entry_index, entry in enumerate(entries, start=1):
                parameter = parameters[entry["name"]]
                if entry["kind"] == "raw":
                    payload = (
                        parameter.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
                    )
                    section = entry["section"]
                    if len(payload) != section["bytes"]:
                        raise RuntimeError(f"raw size mismatch for {entry['name']}")
                    blob.seek(section["offset"])
                    blob.write(payload)
                    section["sha256"] = hashlib.sha256(payload).hexdigest()
                    continue

                rows, columns = entry["shape"]
                bits = entry["bits"]
                entry_scale_search = scale_search_overrides.get(
                    entry["module"], scale_search
                )
                if entry_scale_search not in ("endpoints", "exhaustive"):
                    raise ValueError(
                        f"unsupported scale search for {entry['module']}: {entry_scale_search}"
                    )
                entry["scale_search"] = entry_scale_search
                sections = entry["sections"]
                code_cursor = scale_cursor = 0
                orientation_chunks = []
                for row_start in range(0, rows, row_chunk):
                    source = parameter.data[row_start:row_start + row_chunk].detach().clone()
                    codes, scales, orientations, _ = recover_full_range_rows_for_storage(
                        torch,
                        source,
                        bits,
                        GROUP_SIZE,
                        scale_format,
                        entry_scale_search,
                    )
                    flat_codes = codes.cpu().numpy().reshape(-1)
                    code_payload = pack_unsigned_codes(flat_codes, bits)
                    scale_payload = scales.view(torch.uint16).cpu().numpy().tobytes()
                    blob.seek(sections["codes"]["offset"] + code_cursor)
                    blob.write(code_payload)
                    blob.seek(sections["scales"]["offset"] + scale_cursor)
                    blob.write(scale_payload)
                    code_cursor += len(code_payload)
                    scale_cursor += len(scale_payload)
                    orientation_chunks.append(orientations.cpu().numpy().reshape(-1))

                    if apply_reconstructed:
                        reloaded_codes = unpack_unsigned_codes(
                            code_payload, bits, flat_codes.size
                        )
                        reloaded = reconstruct_full_range_rows_from_storage(
                            torch,
                            reloaded_codes,
                            scales.view(torch.uint16).cpu().numpy(),
                            orientations.cpu().numpy(),
                            bits,
                            source.shape[0],
                            columns,
                            GROUP_SIZE,
                            output_dtype=parameter.dtype,
                            scale_format=scale_format,
                        )
                        parameter.data[row_start:row_start + source.shape[0]].copy_(reloaded)

                all_orientations = np.concatenate(orientation_chunks)
                orientation_payload = pack_orientation_bits(all_orientations)
                blob.seek(sections["orientations"]["offset"])
                blob.write(orientation_payload)
                if code_cursor != sections["codes"]["bytes"]:
                    raise RuntimeError(f"code size mismatch for {entry['name']}")
                if scale_cursor != sections["scales"]["bytes"]:
                    raise RuntimeError(f"scale size mismatch for {entry['name']}")
                if len(orientation_payload) != sections["orientations"]["bytes"]:
                    raise RuntimeError(f"orientation size mismatch for {entry['name']}")
                for section in sections.values():
                    section["sha256"] = _hash_region(
                        blob, section["offset"], section["bytes"]
                    )
                if entry_index == 1 or entry_index % 50 == 0:
                    print(f"[PackedWriter] {entry_index}/{len(entries)} {entry['name']}", flush=True)
            blob.flush()
            os.fsync(blob.fileno())

        manifest = {
            "format": ARTIFACT_FORMAT,
            "model": "microsoft/Mage-VL",
            "source_checkpoint": source_checkpoint,
            "checkpoint_config_sha256": checkpoint_config_sha256,
            "checkpoint_index_sha256": checkpoint_index_sha256,
            "group_size": GROUP_SIZE,
            "scale_format": scale_format,
            "scale_search": scale_search,
            "scale_search_override_count": len(scale_search_overrides),
            "alignment": alignment,
            "blob": {
                "path": blob_path.name,
                "bytes": blob_path.stat().st_size,
                "sha256": sha256_file(blob_path),
            },
            "parameter_count": int(sum(parameter.numel() for parameter in parameters.values())),
            "packed_module_count": len(storage_targets),
            "tensor_count": len(entries),
            "entries": entries,
        }
        manifest_path = temporary / "CHECKPOINT_MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        with manifest_path.open("rb") as manifest_handle:
            os.fsync(manifest_handle.fileno())
        os.replace(temporary, output_dir)
        return manifest
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def load_packed_checkpoint(torch, model, checkpoint_dir: Path, *, verify_blob: bool = True, row_chunk: int = 32) -> dict:
    """Fail closed, verify the blob, and replace every model parameter."""

    checkpoint_dir = checkpoint_dir.resolve()
    manifest_path = checkpoint_dir / "CHECKPOINT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format") != ARTIFACT_FORMAT:
        raise RuntimeError("unsupported packed checkpoint artifact format")
    blob_path = checkpoint_dir / manifest["blob"]["path"]
    if blob_path.stat().st_size != manifest["blob"]["bytes"]:
        raise RuntimeError("packed checkpoint blob size mismatch")
    if verify_blob and sha256_file(blob_path) != manifest["blob"]["sha256"]:
        raise RuntimeError("packed checkpoint blob hash mismatch")
    parameters = dict(model.named_parameters())
    if set(parameters) != {entry["name"] for entry in manifest["entries"]}:
        raise RuntimeError("packed checkpoint parameter-name set does not match model")

    with blob_path.open("rb") as blob:
        for entry_index, entry in enumerate(manifest["entries"], start=1):
            parameter = parameters[entry["name"]]
            if list(parameter.shape) != entry["shape"]:
                raise RuntimeError(f"shape mismatch for {entry['name']}")
            stored_dtype = _dtype_from_name(torch, entry["dtype"])
            if parameter.dtype != stored_dtype:
                raise RuntimeError(f"dtype mismatch for {entry['name']}")
            if entry["kind"] == "raw":
                section = entry["section"]
                blob.seek(section["offset"])
                payload = bytearray(blob.read(section["bytes"]))
                if hashlib.sha256(payload).hexdigest() != section["sha256"]:
                    raise RuntimeError(f"raw section hash mismatch for {entry['name']}")
                values = torch.frombuffer(payload, dtype=torch.uint8).view(stored_dtype)
                parameter.data.copy_(values.reshape(entry["shape"]))
                continue

            rows, columns = entry["shape"]
            bits = entry["bits"]
            groups_per_row = entry["padded_columns"] // entry["group_size"]
            sections = entry["sections"]
            blob.seek(sections["orientations"]["offset"])
            orientation_payload = blob.read(sections["orientations"]["bytes"])
            all_orientations = unpack_orientation_bits(
                orientation_payload, entry["group_count"]
            )
            for section in sections.values():
                if _hash_region(blob, section["offset"], section["bytes"]) != section["sha256"]:
                    raise RuntimeError(f"packed section hash mismatch for {entry['name']}")
            for row_start in range(0, rows, row_chunk):
                chunk_rows = min(row_chunk, rows - row_start)
                code_count = chunk_rows * entry["padded_columns"]
                code_offset = row_start * entry["padded_columns"] * bits // 8
                code_bytes = code_count * bits // 8
                scale_offset = row_start * groups_per_row * 2
                scale_bytes = chunk_rows * groups_per_row * 2
                blob.seek(sections["codes"]["offset"] + code_offset)
                codes = unpack_unsigned_codes(blob.read(code_bytes), bits, code_count)
                blob.seek(sections["scales"]["offset"] + scale_offset)
                scale_bits = np.frombuffer(blob.read(scale_bytes), dtype=np.uint16)
                orientation_start = row_start * groups_per_row
                orientations = all_orientations[
                    orientation_start:orientation_start + chunk_rows * groups_per_row
                ]
                restored = reconstruct_full_range_rows_from_storage(
                    torch,
                    codes,
                    scale_bits,
                    orientations,
                    bits,
                    chunk_rows,
                    columns,
                    entry["group_size"],
                    output_dtype=stored_dtype,
                    scale_format=manifest["scale_format"],
                )
                parameter.data[row_start:row_start + chunk_rows].copy_(restored)
            if entry_index == 1 or entry_index % 50 == 0:
                print(f"[PackedLoader] {entry_index}/{len(manifest['entries'])} {entry['name']}", flush=True)

    return {
        "format": manifest["format"],
        "manifest_sha256": sha256_file(manifest_path),
        "blob_sha256": manifest["blob"]["sha256"],
        "blob_bytes": manifest["blob"]["bytes"],
        "parameter_count": manifest["parameter_count"],
        "packed_module_count": manifest["packed_module_count"],
        "tensor_count": manifest["tensor_count"],
        "blob_hash_verified": verify_blob,
    }
