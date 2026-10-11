#!/usr/bin/env python3
"""Report LM-head dimensions and storage requirements without loading weights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()

    model = args.root / "model"
    config = json.loads((model / "config.json").read_text())
    indexes = sorted(model.glob("*_mixed_gs_index.json"))
    if len(indexes) != 1:
        raise RuntimeError(f"expected one Mixed-GS index, found {len(indexes)}")
    index = json.loads(indexes[0].read_text())
    embedding = next(
        item
        for item in index["aux_tensors"]
        if item["name"] == "model.embed_tokens.weight"
    )
    vocab, hidden = (int(value) for value in embedding["shape"])
    groups = (hidden + 63) // 64
    blocks = (vocab + 7) // 8
    packed_bytes = groups * blocks * 288
    result = {
        "hidden_size": int(config["hidden_size"]),
        "vocab_size": int(config["vocab_size"]),
        "embedding_shape": [vocab, hidden],
        "fp16_bytes": vocab * hidden * 2,
        "w4_gs64_packed_bytes": packed_bytes,
        "input_groups": groups,
        "output_blocks": blocks,
        "macros": groups * blocks,
        "linear_count": len(index["linears"]),
        "aux_file": index["aux_file"],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
