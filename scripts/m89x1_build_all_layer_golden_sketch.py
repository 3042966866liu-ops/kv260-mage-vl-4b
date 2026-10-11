#!/usr/bin/env python3
"""Build a compact, deterministic sketch of all 144 quantized CPU family inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np


LAYERS = 36
FAMILIES = ("qkv", "attention_out", "gate_up", "mlp_down")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sketch(name: str, values: np.ndarray, sample_count: int) -> dict[str, object]:
    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise RuntimeError(f"invalid golden tensor: {name} {array.shape}")
    flat = array.reshape(-1)
    seed = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "little")
    generator = np.random.default_rng(seed)
    count = min(sample_count, flat.size)
    indices = np.sort(generator.choice(flat.size, size=count, replace=False)).astype(np.int64)
    samples = flat[indices]
    array64 = flat.astype(np.float64)
    return {
        "shape": list(array.shape),
        "element_count": int(flat.size),
        "sample_count": int(count),
        "sample_indices": indices.tolist(),
        "sample_values": samples.tolist(),
        "minimum": float(np.min(flat)),
        "maximum": float(np.max(flat)),
        "mean": float(np.mean(array64)),
        "rms": float(np.sqrt(np.mean(array64 * array64))),
        "l2": float(np.linalg.norm(array64)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=512)
    args = parser.parse_args()
    if not 64 <= args.sample_count <= 4096:
        raise ValueError("sample-count must be in [64, 4096]")

    source_result = json.loads(args.source_result.read_text(encoding="utf-8"))
    if source_result.get("status") != "MEASURED":
        raise RuntimeError("quantized CPU source result is not MEASURED")
    if source_result.get("capture_output_sha256") != sha256(args.input):
        raise RuntimeError("quantized CPU capture identity mismatch")

    expected = [f"layer{layer:02d}_{family}" for layer in range(LAYERS) for family in FAMILIES]
    with np.load(args.input, allow_pickle=False) as payload:
        if sorted(payload.files) != sorted(expected):
            raise RuntimeError("144-family golden key set mismatch")
        tensors = {name: sketch(name, payload[name], args.sample_count) for name in expected}

    result = {
        "gate": "M89-X1-quantized-CPU-all-layer-golden-sketch",
        "status": "PASS",
        "classification": "compact offline golden for a future same-level board differential; not FPGA evidence",
        "source_capture": args.input.as_posix(),
        "source_capture_sha256": sha256(args.input),
        "source_result": args.source_result.as_posix(),
        "source_result_sha256": sha256(args.source_result),
        "layer_count": LAYERS,
        "families_per_layer": len(FAMILIES),
        "tensor_count": len(tensors),
        "sample_count_per_tensor": args.sample_count,
        "tensors": tensors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(
        "M89X1_ALL_LAYER_GOLDEN_SKETCH_PASS "
        f"tensors={len(tensors)} bytes={args.output.stat().st_size} sha256={sha256(args.output)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
