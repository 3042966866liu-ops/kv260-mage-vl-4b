#!/usr/bin/env python3
"""Read-only Mage-VL safetensors metadata audit for the M90 video boundary."""

from __future__ import annotations

import argparse
import glob
import json

from safetensors import safe_open


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    byte_width = {"BF16": 2, "F16": 2, "F32": 4, "I64": 8, "I32": 4, "I8": 1, "U8": 1}
    groups: dict[str, dict[str, int]] = {}
    samples: dict[str, list[dict[str, object]]] = {}
    total = 0
    files = sorted(glob.glob(f"{args.model}/*.safetensors"))
    if not files:
        raise FileNotFoundError(f"no safetensors shards under {args.model}")
    for filename in files:
        with safe_open(filename, framework="pt", device="cpu") as handle:
            for name in handle.keys():
                view = handle.get_slice(name)
                shape = list(view.get_shape())
                dtype = str(view.get_dtype())
                size = byte_width.get(dtype, 2)
                for extent in shape:
                    size *= extent
                if ".visual." in name or name.startswith("model.visual"):
                    group = "vision"
                elif name.startswith("lm_head"):
                    group = "lm_head"
                else:
                    group = "language"
                entry = groups.setdefault(group, {"bytes": 0, "tensors": 0})
                entry["bytes"] += size
                entry["tensors"] += 1
                if len(samples.setdefault(group, [])) < 12:
                    samples[group].append({"name": name, "shape": shape, "dtype": dtype, "bytes": size})
                total += size
    print(json.dumps({"files": len(files), "groups": groups, "total_bytes": total, "samples": samples}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
