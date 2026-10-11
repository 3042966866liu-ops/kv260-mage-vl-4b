#!/usr/bin/env python3
"""Stream one safetensors matrix to a row-major little-endian FP16 blob."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from safetensors import safe_open


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--tensor-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--rows-per-chunk", type=int, default=2048)
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    index = json.loads((model_dir / "model.safetensors.index.json").read_text())
    mapping = index["weight_map"]
    if args.tensor_name not in mapping:
        raise KeyError(f"tensor not present in model index: {args.tensor_name}")
    shard = model_dir / mapping[args.tensor_name]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    with safe_open(shard, framework="pt", device="cpu") as source_file:
        source = source_file.get_slice(args.tensor_name)
        shape = tuple(int(value) for value in source.get_shape())
        if len(shape) != 2:
            raise ValueError(f"expected a matrix, got shape {shape}")
        rows, columns = shape
        destination = np.memmap(
            args.output, dtype="<f2", mode="w+", shape=(rows, columns)
        )
        for start in range(0, rows, int(args.rows_per_chunk)):
            stop = min(start + int(args.rows_per_chunk), rows)
            destination[start:stop] = source[start:stop].float().numpy()
            print(json.dumps({"rows": stop, "total_rows": rows}), flush=True)
        destination.flush()

    metadata = {
        "format": "fp16-little-endian-row-major",
        "source_tensor": args.tensor_name,
        "source_shard": shard.name,
        "shape": list(shape),
        "bytes": args.output.stat().st_size,
        "sha256": sha256(args.output),
        "file": args.output.name,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", **metadata}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
