#!/usr/bin/env python3
"""Build a compact real M56 W3 LM-head fixture for the M89-X runtime kernel."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


MAGIC = b"M89ZLMH1"
GROUPS = 40
TOKENS = 32
BITS = 3
ROWS = 8
WORDS = 13


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    module = next(item for item in manifest["modules"] if item["module"] == "lm_head")
    if int(module["bits"]) != BITS or int(module["input_groups"]) != GROUPS:
        raise RuntimeError("M89Z_LM_HEAD_GEOMETRY_FAIL")
    tile = module["tiles"][0]
    if int(tile["rows_per_shard"]) < ROWS:
        raise RuntimeError("M89Z_TILE_TOO_SMALL")
    blocks = int(tile["rows_per_shard"]) // 8
    block = 1
    handles = [(args.layout / item["path"]).open("rb") for item in manifest["files"]]
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    try:
        with args.fixture.open("wb") as output:
            output.write(MAGIC)
            output.write(struct.pack("<IIIIII", GROUPS, BITS, ROWS, TOKENS, 4, block))
            for shard, handle in enumerate(handles):
                for group in range(GROUPS):
                    offset = int(tile["shard_offsets"][shard]) + (group * blocks + block) * WORDS * 16
                    handle.seek(offset)
                    payload = handle.read(WORDS * 16)
                    if len(payload) != WORDS * 16:
                        raise RuntimeError("M89Z_SHORT_WEIGHT_RECORD")
                    output.write(payload)
            lane = np.arange(64, dtype=np.float32)
            for group in range(GROUPS):
                for token in range(TOKENS):
                    values = (np.sin((lane + 1) * (group + 3) * 0.013 + token * 0.071) *
                              (0.25 + (group % 7) * 0.11)).astype(np.float32)
                    maximum = float(np.max(np.abs(values)))
                    scale = np.float16(maximum / 127.0 if maximum else 1.0)
                    codes = np.clip(np.rint(values / np.float32(scale)), -127, 127).astype(np.int8)
                    output.write(codes.tobytes())
                    output.write(np.asarray(scale, dtype="<f2").tobytes())
                    output.write(bytes(14))
    finally:
        for handle in handles:
            handle.close()
    result = {
        "date": "2026-08-31",
        "build": "M89-Z",
        "status": "PASS_REAL_M56_W3_LMHEAD_FIXTURE_BUILT",
        "layout_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "module": "lm_head",
        "bits": BITS,
        "groups": GROUPS,
        "rows": ROWS,
        "tokens": TOKENS,
        "weight_shards": 4,
        "tile_index": 0,
        "block": block,
        "fixture": args.fixture.as_posix(),
        "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M89Z_REAL_M56_W3_LMHEAD_FIXTURE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
