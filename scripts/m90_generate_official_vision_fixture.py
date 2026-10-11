#!/usr/bin/env python3
"""Run only the official Mage-VL vision tower and lock its merged-token output."""

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
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--processor-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    model_root = args.model.resolve()
    # The checkpoint directory contains a hyphen, so load its relative-import
    # modules through a stable synthetic package rather than changing files.
    package_name = "tellme_mage_vl_local"
    package = types.ModuleType(package_name)
    package.__path__ = [str(model_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = package
    configuration = importlib.import_module(f"{package_name}.configuration_mage_vl")
    modeling = importlib.import_module(f"{package_name}.modeling_mage_vl")
    MageVLConfig = configuration.MageVLConfig
    MageVLVisionPretrainedModel = modeling.MageVLVisionPretrainedModel

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    config = MageVLConfig.from_pretrained(model_root, local_files_only=True)
    vision = MageVLVisionPretrainedModel(config.vision_config)
    state: dict[str, torch.Tensor] = {}
    tensor_meta: list[dict[str, object]] = []
    tensor_count = 0
    tensor_bytes = 0
    for shard in sorted(model_root.glob("*.safetensors")):
        with safe_open(shard, framework="pt", device="cpu") as handle:
            for name in handle.keys():
                if not name.startswith("model.visual."):
                    continue
                short = name[len("model.visual.") :]
                tensor = handle.get_tensor(name)
                state[short] = tensor
                size = tensor.numel() * tensor.element_size()
                tensor_meta.append({"name": name, "shape": list(tensor.shape), "dtype": str(tensor.dtype), "bytes": size})
                tensor_count += 1
                tensor_bytes += size
    incompatible = vision.load_state_dict(state, strict=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError(f"vision state mismatch: {incompatible}")
    del state
    device = torch.device(args.device)
    vision = vision.to(device=device, dtype=torch.bfloat16).eval()
    with np.load(args.processor_fixture, allow_pickle=False) as fixture:
        pixels = torch.from_numpy(fixture["pixel_values"]).to(device=device, dtype=torch.bfloat16)
        grid = torch.from_numpy(fixture["image_grid_thw"]).to(device=device)
        positions = torch.from_numpy(fixture["patch_positions"]).to(device=device)
    with torch.inference_mode():
        output = vision(pixels, grid_thw=grid, patch_positions=positions).last_hidden_state
    if list(output.shape) != [784, 2560]:
        raise RuntimeError(f"unexpected merged vision output shape: {list(output.shape)}")
    bits = output.detach().contiguous().view(torch.uint16).cpu().numpy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp.npz")
    np.savez_compressed(temporary, merged_vision_bf16_bits=bits)
    os.replace(temporary, args.output)
    payload = {
        "gate": "M90-official-Mage-VL-vision-tower-golden",
        "status": "PASS",
        "device": args.device,
        "vision_tensor_count": tensor_count,
        "vision_bf16_bytes": tensor_bytes,
        "vision_tensor_metadata": tensor_meta,
        "input_shapes": {
            "pixel_values": list(pixels.shape),
            "image_grid_thw": list(grid.shape),
            "patch_positions": list(positions.shape),
        },
        "output_shape": list(output.shape),
        "output_dtype": str(output.dtype),
        "output_fixture_sha256": sha256(args.output),
        "output_fixture_bytes": args.output.stat().st_size,
        "boundary": "Official BF16 vision tower through merged 784x2560 tokens; language generation is not part of this gate.",
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary_result = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary_result.write_text(rendered, encoding="utf-8")
    os.replace(temporary_result, args.result)
    print("M90_OFFICIAL_VISION_GOLDEN_PASS")
    print(json.dumps({k: v for k, v in payload.items() if k != "vision_tensor_metadata"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
