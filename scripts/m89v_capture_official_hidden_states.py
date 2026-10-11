#!/usr/bin/env python3
"""Capture the 144 real language Linear inputs from official BF16 Mage-VL.

This is an offline CPU reference capture.  It does not contact the network,
modify the checkpoint, use the board, or interrupt the existing GPU Web model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path


LAYERS = 36
FAMILIES = {
    "qkv": "self_attn.q_proj",
    "attention_out": "self_attn.o_proj",
    "gate_up": "mlp.gate_proj",
    "mlp_down": "mlp.down_proj",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prompt", default="3+26等于多少？只回答数字。")
    args = parser.parse_args()

    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        args.model, trust_remote_code=True, local_files_only=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    ).eval()

    messages = [{"role": "user", "content": [{"type": "text", "text": args.prompt}]}]
    rendered = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    encoded = processor(text=[rendered], return_tensors="pt")

    modules = dict(model.named_modules())
    requested: dict[str, str] = {}
    for layer in range(LAYERS):
        for family, suffix in FAMILIES.items():
            logical = f"layer{layer:02d}_{family}"
            exact = f"model.language_model.layers.{layer}.{suffix}"
            if exact in modules:
                requested[logical] = exact
                continue
            matches = [name for name in modules if name.endswith(
                f"language_model.layers.{layer}.{suffix}"
            )]
            if len(matches) != 1:
                raise RuntimeError(
                    f"M89V_TARGET_DISCOVERY_FAIL logical={logical} matches={matches}"
                )
            requested[logical] = matches[0]

    captured: dict[str, np.ndarray] = {}
    handles = []

    def make_hook(logical: str):
        def hook(_module, positional):
            if logical in captured:
                raise RuntimeError(f"M89V_DUPLICATE_HOOK logical={logical}")
            if not positional or not torch.is_tensor(positional[0]):
                raise RuntimeError(f"M89V_BAD_HOOK_INPUT logical={logical}")
            value = positional[0].detach().to(dtype=torch.float32, device="cpu")
            if value.ndim != 3 or value.shape[0] != 1:
                raise RuntimeError(
                    f"M89V_BAD_HIDDEN_SHAPE logical={logical} shape={tuple(value.shape)}"
                )
            captured[logical] = value[0].contiguous().numpy()
        return hook

    for logical, actual in requested.items():
        handles.append(modules[actual].register_forward_pre_hook(make_hook(logical)))

    try:
        with torch.inference_mode():
            outputs = model(**encoded, use_cache=False, return_dict=True)
            logits_shape = list(outputs.logits.shape)
    finally:
        for handle in handles:
            handle.remove()

    if len(captured) != LAYERS * len(FAMILIES):
        missing = sorted(set(requested) - set(captured))
        raise RuntimeError(f"M89V_CAPTURE_INCOMPLETE count={len(captured)} missing={missing}")
    token_count = int(encoded["input_ids"].shape[1])
    for logical, values in captured.items():
        if values.shape[0] != token_count or values.shape[1] % 64:
            raise RuntimeError(f"M89V_CAPTURE_GEOMETRY_FAIL {logical} {values.shape}")
        if not np.isfinite(values).all():
            raise RuntimeError(f"M89V_NONFINITE_HIDDEN logical={logical}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, **captured)
    result = {
        "date": "2026-08-30",
        "build": "M89-V",
        "status": "PASS_OFFICIAL_BF16_REAL_HIDDEN_STATE_CAPTURE",
        "classification": "official local Mage-VL BF16 CPU forward-hook capture; not FPGA execution",
        "model": "microsoft/Mage-VL",
        "model_path": str(args.model),
        "device": "cpu",
        "dtype": "bfloat16 model input captured losslessly as float32",
        "prompt": args.prompt,
        "chat_template": rendered,
        "prompt_token_ids": encoded["input_ids"][0].tolist(),
        "token_count": token_count,
        "capture_count": len(captured),
        "families_per_layer": sorted(FAMILIES),
        "shapes": {key: list(value.shape) for key, value in sorted(captured.items())},
        "logits_shape": logits_shape,
        "output": args.output.as_posix(),
        "output_bytes": args.output.stat().st_size,
        "output_sha256": sha256(args.output),
        "wall_ms": (time.perf_counter() - started) * 1000.0,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    print("M89V_OFFICIAL_BF16_144_HIDDEN_STATES_CAPTURE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
