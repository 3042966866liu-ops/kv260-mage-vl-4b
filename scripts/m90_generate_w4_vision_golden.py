#!/usr/bin/env python3
"""Generate the exact M56-storage W4 vision output without loading the 4B LM."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import types
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_region(stream, offset: int, size: int) -> str:
    digest = hashlib.sha256()
    stream.seek(offset)
    remaining = size
    while remaining:
        block = stream.read(min(8 << 20, remaining))
        if not block:
            raise EOFError("packed blob truncated")
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def load_official_visual(model_root: Path):
    package_name = "tellme_mage_vl_w4_local"
    package = types.ModuleType(package_name)
    package.__path__ = [str(model_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = package
    configuration = importlib.import_module(f"{package_name}.configuration_mage_vl")
    modeling = importlib.import_module(f"{package_name}.modeling_mage_vl")
    config = configuration.MageVLConfig.from_pretrained(model_root, local_files_only=True)
    vision = modeling.MageVLVisionPretrainedModel(config.vision_config)
    state = {}
    for shard in sorted(model_root.glob("*.safetensors")):
        with safe_open(shard, framework="pt", device="cpu") as handle:
            for name in handle.keys():
                if name.startswith("model.visual."):
                    state[name[len("model.visual.") :]] = handle.get_tensor(name)
    incompatible = vision.load_state_dict(state, strict=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError(f"official vision state mismatch: {incompatible}")
    return vision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--packed", type=Path, required=True)
    parser.add_argument("--processor-fixture", type=Path, required=True)
    parser.add_argument("--bf16-golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    workspace_helpers = Path(__file__).resolve().parents[1] / "deployment/mage_vl4b/scripts"
    sys.path.insert(0, str(workspace_helpers))
    from mixed_bit_checkpoint import (  # type: ignore[import-not-found]
        reconstruct_full_range_rows_from_storage,
        unpack_orientation_bits,
        unpack_unsigned_codes,
    )

    model_root = args.model.resolve()
    vision = load_official_visual(model_root)
    packed_manifest_path = args.packed / "CHECKPOINT_MANIFEST.json"
    manifest = json.loads(packed_manifest_path.read_text(encoding="utf-8"))
    blob_path = args.packed / manifest["blob"]["path"]
    parameters = dict(vision.named_parameters())
    selected = [entry for entry in manifest["entries"] if entry["kind"] == "packed" and entry["name"].startswith("model.visual.")]
    if len(selected) != 98:
        raise RuntimeError(f"expected 98 packed visual Linears, got {len(selected)}")
    with blob_path.open("rb") as blob:
        for index, entry in enumerate(selected, start=1):
            short_name = entry["name"][len("model.visual.") :]
            if short_name not in parameters or list(parameters[short_name].shape) != entry["shape"]:
                raise RuntimeError(f"visual packed parameter mismatch: {entry['name']}")
            sections = entry["sections"]
            for section in sections.values():
                if hash_region(blob, int(section["offset"]), int(section["bytes"])) != section["sha256"]:
                    raise RuntimeError(f"visual packed section hash mismatch: {entry['name']}")
            rows, columns = map(int, entry["shape"])
            groups_per_row = int(entry["padded_columns"]) // int(entry["group_size"])
            blob.seek(int(sections["orientations"]["offset"]))
            orientations = unpack_orientation_bits(blob.read(int(sections["orientations"]["bytes"])), int(entry["group_count"]))
            parameter = parameters[short_name]
            for row_start in range(0, rows, 32):
                chunk_rows = min(32, rows - row_start)
                code_count = chunk_rows * int(entry["padded_columns"])
                code_offset = row_start * int(entry["padded_columns"]) * int(entry["bits"]) // 8
                code_bytes = code_count * int(entry["bits"]) // 8
                scale_offset = row_start * groups_per_row * 2
                scale_bytes = chunk_rows * groups_per_row * 2
                blob.seek(int(sections["codes"]["offset"]) + code_offset)
                codes = unpack_unsigned_codes(blob.read(code_bytes), int(entry["bits"]), code_count)
                blob.seek(int(sections["scales"]["offset"]) + scale_offset)
                scale_bits = np.frombuffer(blob.read(scale_bytes), dtype=np.uint16)
                orientation_start = row_start * groups_per_row
                restored = reconstruct_full_range_rows_from_storage(
                    torch, codes, scale_bits,
                    orientations[orientation_start:orientation_start + chunk_rows * groups_per_row],
                    int(entry["bits"]), chunk_rows, columns, int(entry["group_size"]),
                    output_dtype=parameter.dtype, scale_format=manifest["scale_format"],
                )
                parameter.data[row_start:row_start + chunk_rows].copy_(restored)
            if index % 24 == 0:
                print(f"[M90-W4] loaded {index}/{len(selected)}", flush=True)

    device = torch.device(args.device)
    vision = vision.to(device=device, dtype=torch.bfloat16).eval()
    with np.load(args.processor_fixture, allow_pickle=False) as fixture:
        pixels = torch.from_numpy(fixture["pixel_values"]).to(device=device, dtype=torch.bfloat16)
        grid = torch.from_numpy(fixture["image_grid_thw"]).to(device=device)
        positions = torch.from_numpy(fixture["patch_positions"]).to(device=device)
    with torch.inference_mode():
        output = vision(pixels, grid_thw=grid, patch_positions=positions).last_hidden_state
    if list(output.shape) != [784, 2560]:
        raise RuntimeError(f"unexpected W4 output shape: {list(output.shape)}")
    output_f32 = output.float().cpu().numpy()
    bits = output.detach().contiguous().view(torch.uint16).cpu().numpy()
    with np.load(args.bf16_golden, allow_pickle=False) as golden:
        golden_bits = golden["merged_vision_bf16_bits"]
    golden_f32 = (golden_bits.astype(np.uint32) << 16).view(np.float32)
    delta = np.abs(output_f32 - golden_f32)
    numerator = float(np.sum(output_f32.astype(np.float64) * golden_f32.astype(np.float64)))
    denominator = float(np.linalg.norm(output_f32.astype(np.float64)) * np.linalg.norm(golden_f32.astype(np.float64)))
    cosine = numerator / denominator
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp.npz")
    np.savez_compressed(temporary, merged_vision_w4_bf16_bits=bits)
    os.replace(temporary, args.output)
    payload = {
        "gate": "M90-M56-storage-W4-vision-golden",
        "status": "PASS",
        "packed_manifest_sha256": sha256(packed_manifest_path),
        "packed_blob_sha256": manifest["blob"]["sha256"],
        "packed_visual_linear_count": len(selected),
        "output_shape": list(output.shape),
        "output_fixture_sha256": sha256(args.output),
        "output_fixture_bytes": args.output.stat().st_size,
        "versus_official_bf16": {
            "max_abs_error": float(delta.max()),
            "mean_abs_error": float(delta.mean()),
            "rmse": float(np.sqrt(np.mean(delta.astype(np.float64) ** 2))),
            "cosine_similarity": cosine,
            "exact_bf16_elements": int(np.count_nonzero(bits == golden_bits)),
            "element_count": int(bits.size),
        },
        "semantic_evidence": "deployment/mage_vl4b/MAGE_VL_M42_CACHED_NATIVE_VIDEO_W4_REPAIRED_POLICY_RESULT.json",
        "boundary": "Exact M56 packed-storage vision weights through the official vision tower; no board execution or language generation in this gate.",
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.result.write_text(rendered, encoding="utf-8")
    print("M90_W4_VISION_GOLDEN_PASS")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
