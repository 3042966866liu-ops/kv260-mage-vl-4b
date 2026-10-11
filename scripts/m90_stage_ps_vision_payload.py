#!/usr/bin/env python3
"""Create a self-contained BF16 Mage-VL vision payload for the PS runtime.

This is deliberately separate from the rejected visual W4A8 research branch.
Only ``model.visual.*`` tensors are copied, with their prefix removed so the
official ``MageVLVisionPretrainedModel`` can load them strictly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    model_root = args.model.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    state: dict[str, torch.Tensor] = {}
    source_bytes = 0
    metadata: list[dict[str, object]] = []
    for shard in sorted(model_root.glob("*.safetensors")):
        with safe_open(shard, framework="pt", device="cpu") as handle:
            for name in handle.keys():
                if not name.startswith("model.visual."):
                    continue
                short = name[len("model.visual.") :]
                if short in state:
                    raise RuntimeError(f"duplicate visual tensor: {short}")
                tensor = handle.get_tensor(name).contiguous()
                if tensor.dtype != torch.bfloat16:
                    raise RuntimeError(f"visual tensor is not BF16: {name} {tensor.dtype}")
                state[short] = tensor
                size = tensor.numel() * tensor.element_size()
                source_bytes += size
                metadata.append({"name": short, "shape": list(tensor.shape), "bytes": size})
    if len(state) != 297 or source_bytes != 660_739_072:
        raise RuntimeError(f"unexpected visual partition: tensors={len(state)} bytes={source_bytes}")

    weights = output / "vision_bf16.safetensors"
    temporary_weights = weights.with_suffix(".tmp.safetensors")
    save_file(state, temporary_weights, metadata={"format": "pt", "source": "microsoft/Mage-VL model.visual"})
    os.replace(temporary_weights, weights)
    del state

    support_names = ("config.json", "configuration_mage_vl.py", "modeling_mage_vl.py")
    for name in support_names:
        shutil.copy2(model_root / name, output / name)

    files = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "PAYLOAD_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    payload = {
        "gate": "M90-PS-high-precision-vision-payload",
        "status": "PASS",
        "route": "PS BF16 visual tower + M89-X FPGA language/head",
        "rejected_route": "M62 visual W4A8 is not promoted because its semantic gate passed only 2/3 cases",
        "tensor_count": len(metadata),
        "tensor_bytes": source_bytes,
        "tensor_metadata": metadata,
        "files": files,
        "dependencies": {
            "architecture": "aarch64",
            "python_modules": ["numpy", "torch", "transformers", "safetensors", "tokenizers"],
        },
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    atomic_json(output / "PAYLOAD_MANIFEST.json", payload)
    result = dict(payload)
    result["payload_manifest_sha256"] = sha256(output / "PAYLOAD_MANIFEST.json")
    atomic_json(args.result, result)
    print("M90_PS_VISION_PAYLOAD_PASS")
    print(json.dumps({k: v for k, v in result.items() if k != "tensor_metadata"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
