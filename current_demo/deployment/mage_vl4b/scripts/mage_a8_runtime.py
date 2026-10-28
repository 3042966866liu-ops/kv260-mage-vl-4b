#!/usr/bin/env python3
"""Accuracy-first A8-G64 helpers for the Mage six-port runtime.

The PL consumes one 80-byte AXI record per input group: 64 signed int8
activations, one little-endian FP16 scale, and fourteen reserved zero bytes.
The scale is rounded to FP16 before the integer codes are computed, matching
the exact value later multiplied by ``mage_decode_sixport_v2``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np


GROUP_SIZE = 64
RECORD_BYTES = 80


def quantize_activation_records(activation: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return contiguous ``[groups, 80]`` records, int8 codes, and FP16 scales."""
    source = np.asarray(activation, dtype=np.float32)
    if source.ndim != 1 or source.size < GROUP_SIZE or source.size % GROUP_SIZE:
        raise ValueError("activation must be a non-empty 1-D multiple of 64")
    grouped = source.reshape(-1, GROUP_SIZE)
    maximum = np.max(np.abs(grouped), axis=1)
    scale = (maximum / np.float32(127.0)).astype("<f2")
    safe_scale = np.where(maximum == 0.0, np.float16(1.0), scale).astype("<f2")
    codes = np.clip(
        np.rint(grouped / safe_scale.astype(np.float32)[:, None]), -127, 127
    ).astype(np.int8)
    records = np.zeros((grouped.shape[0], RECORD_BYTES), dtype=np.uint8)
    records[:, :GROUP_SIZE] = codes.view(np.uint8)
    records[:, 64:66] = safe_scale.view(np.uint8).reshape(-1, 2)
    return np.ascontiguousarray(records), codes, safe_scale


def dequantize_activation(codes: np.ndarray, scales: np.ndarray) -> np.ndarray:
    codes = np.asarray(codes, dtype=np.int8)
    scales = np.asarray(scales, dtype="<f2")
    if codes.ndim != 2 or codes.shape[1] != GROUP_SIZE or scales.shape != codes.shape[:1]:
        raise ValueError("codes/scales shape mismatch")
    return (codes.astype(np.float32) * scales.astype(np.float32)[:, None]).reshape(-1)


def torch_a8_qdq(torch, activation):
    """Apply the same scale-first A8-G64 quantize/dequantize to a Torch tensor."""
    if activation.shape[-1] < GROUP_SIZE or activation.shape[-1] % GROUP_SIZE:
        raise ValueError("last activation dimension must be a non-empty multiple of 64")
    original_dtype = activation.dtype
    source = activation.to(torch.float32)
    grouped = source.reshape(*source.shape[:-1], -1, GROUP_SIZE)
    maximum = grouped.abs().amax(dim=-1)
    scale = (maximum / 127.0).to(torch.float16)
    safe_scale = torch.where(maximum == 0.0, torch.ones_like(scale), scale)
    codes = torch.round(grouped / safe_scale.to(torch.float32).unsqueeze(-1)).clamp(-127, 127)
    restored = codes * safe_scale.to(torch.float32).unsqueeze(-1)
    return restored.reshape_as(source).to(original_dtype)


def install_packed_linear_a8_hooks(
    torch, model, checkpoint: Path, module_pattern: str | None = None
):
    """Install A8 input-QDQ hooks on exactly the packed M56 Linear modules."""
    manifest_path = Path(checkpoint) / "CHECKPOINT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    packed_names = {
        entry["module"] for entry in manifest["entries"] if entry.get("kind") == "packed"
    }
    modules = dict(model.named_modules())
    missing = sorted(packed_names - modules.keys())
    if missing:
        raise RuntimeError(f"packed modules missing from model: {missing[:3]}")
    all_linear_names = sorted(
        name for name in packed_names if isinstance(modules[name], torch.nn.Linear)
    )
    skipped = sorted(packed_names - set(all_linear_names))
    if any(not isinstance(modules[name], torch.nn.Embedding) for name in skipped):
        raise RuntimeError(f"unexpected packed non-Linear modules: {skipped}")
    if len(skipped) != 1:
        raise RuntimeError(f"expected exactly one CPU-indexed embedding, found: {skipped}")
    if module_pattern is None:
        linear_names = all_linear_names
    else:
        matcher = re.compile(module_pattern)
        linear_names = [name for name in all_linear_names if matcher.search(name)]
        if not linear_names:
            raise RuntimeError(f"A8 module pattern selected no Linear: {module_pattern!r}")
    handles = []

    def hook(_module, inputs):
        if not inputs:
            raise RuntimeError("packed Linear received no activation")
        return (torch_a8_qdq(torch, inputs[0]), *inputs[1:])

    for name in linear_names:
        handles.append(modules[name].register_forward_pre_hook(hook))
    return handles, linear_names
