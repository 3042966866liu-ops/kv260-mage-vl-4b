#!/usr/bin/env python3
"""Build one real exact-lifted W4 LM-head block for final M89-X CSim."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


MAGIC = b"M89Z2W41"
GROUPS, TOKENS, BITS, ROWS, WORDS = 40, 32, 4, 8, 17


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--layout", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    args = p.parse_args()
    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    module = next(item for item in manifest["modules"] if item["module"] == "lm_head")
    if int(module["bits"]) != BITS or int(module["source_bits"]) != 3 or int(module["input_groups"]) != GROUPS:
        raise RuntimeError("M89Z2_LM_HEAD_GEOMETRY_FAIL")
    tile = module["tiles"][0]
    blocks, block = int(tile["rows_per_shard"]) // 8, 1
    handles = [(args.layout / item["path"]).open("rb") for item in manifest["files"]]
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.fixture.open("wb") as out:
            out.write(MAGIC)
            out.write(struct.pack("<IIIIII", GROUPS, BITS, ROWS, TOKENS, 4, block))
            for shard, handle in enumerate(handles):
                for group in range(GROUPS):
                    offset = int(tile["shard_offsets"][shard]) + (group * blocks + block) * WORDS * 16
                    handle.seek(offset)
                    payload = handle.read(WORDS * 16)
                    if len(payload) != WORDS * 16:
                        raise RuntimeError("M89Z2_SHORT_WEIGHT_RECORD")
                    out.write(payload)
            lane = np.arange(64, dtype=np.float32)
            for group in range(GROUPS):
                for token in range(TOKENS):
                    values = (np.sin((lane + 1) * (group + 3) * 0.013 + token * 0.071) *
                              (0.25 + (group % 7) * 0.11)).astype(np.float32)
                    maximum = float(np.max(np.abs(values)))
                    scale = np.float16(maximum / 127.0 if maximum else 1.0)
                    codes = np.clip(np.rint(values / np.float32(scale)), -127, 127).astype(np.int8)
                    out.write(codes.tobytes())
                    out.write(np.asarray(scale, dtype="<f2").tobytes())
                    out.write(bytes(14))
    finally:
        for handle in handles:
            handle.close()
    result = {
        "date": "2026-08-31", "build": "M89-Z2",
        "status": "PASS_REAL_EXACT_LIFTED_W4_LMHEAD_FIXTURE_BUILT",
        "layout_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "module": "lm_head", "source_bits": 3, "bits": BITS,
        "groups": GROUPS, "rows": ROWS, "tokens": TOKENS,
        "weight_shards": 4, "tile_index": 0, "block": block,
        "fixture": args.fixture.as_posix(), "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture), "requantized": False,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M89Z2_REAL_EXACT_LIFTED_W4_LMHEAD_FIXTURE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
