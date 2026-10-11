#!/usr/bin/env python3
"""Build a compact fail-closed real-M56 fixture for the M89-P HLS top."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


MAGIC = b"M89QREAL"
SHARDS = 4
MAX_WORDS = 17
EXPECTED_LANGUAGE = 252
EXPECTED_SOURCE_BLOB = "24774ce383eb8261257942bb2a7a565d75fa3961754905973759d8e58ac24e4f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    source_raw = (args.source / "CHECKPOINT_MANIFEST.json").read_bytes()
    source = json.loads(source_raw)
    if source["blob"]["sha256"] != EXPECTED_SOURCE_BLOB:
        raise RuntimeError("unexpected M56 source blob identity")
    if sha256(args.source / "weights.bin") != EXPECTED_SOURCE_BLOB:
        raise RuntimeError("M56 source blob hash mismatch")

    layout_path = args.layout / "SIXPORT_LAYOUT_MANIFEST.json"
    layout_raw = layout_path.read_bytes()
    layout = json.loads(layout_raw)
    if layout["source"]["blob_sha256"] != EXPECTED_SOURCE_BLOB:
        raise RuntimeError("four-port layout source identity mismatch")
    if int(layout["parameters"]["shard_count"]) != SHARDS:
        raise RuntimeError("fixture requires exactly four layout shards")

    modules = [m for m in layout["modules"] if ".language_model.layers." in m["module"]]
    if len(modules) != EXPECTED_LANGUAGE:
        raise RuntimeError(f"expected {EXPECTED_LANGUAGE} language descriptors, got {len(modules)}")
    bit_counts = {"W2": 0, "W4": 0}
    handles = [(args.layout / f["path"]).open("rb") for f in layout["files"]]
    records: list[bytes] = []
    selections: list[dict] = []
    try:
        for index, module in enumerate(modules):
            bits = int(module["bits"])
            if bits not in (2, 4):
                raise RuntimeError(f"unsupported W{bits} descriptor {module['module']}")
            words = 1 + 4 * bits
            tile = module["tiles"][index % len(module["tiles"])]
            groups = int(module["input_groups"])
            blocks = int(tile["rows_per_shard"]) // 8
            group = (index * 17 + 3) % groups
            block = (index * 7 + 1) % blocks
            payload = bytearray(struct.pack("<BBH", bits, words, 0))
            for shard, handle in enumerate(handles):
                offset = int(tile["shard_offsets"][shard]) + (group * blocks + block) * words * 16
                handle.seek(offset)
                raw = handle.read(words * 16)
                if len(raw) != words * 16:
                    raise RuntimeError(f"short record for {module['module']} shard {shard}")
                payload.extend(raw)
                payload.extend(bytes((MAX_WORDS - words) * 16))
            records.append(bytes(payload))
            selections.append({
                "index": index,
                "module": module["module"],
                "bits": bits,
                "tile_index": int(tile["tile_index"]),
                "group": group,
                "block": block,
            })
            bit_counts[f"W{bits}"] += 1
    finally:
        for handle in handles:
            handle.close()

    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    with args.fixture.open("wb") as output:
        output.write(MAGIC)
        output.write(struct.pack("<II", len(records), MAX_WORDS))
        for record in records:
            output.write(record)

    result = {
        "build": "M89-Q",
        "status": "PASS_REAL_M56_FOURPORT_FIXTURE_BUILT",
        "scope": "fixture construction only; HLS CSim result is a separate gate",
        "source_manifest_sha256": hashlib.sha256(source_raw).hexdigest(),
        "source_blob_sha256": EXPECTED_SOURCE_BLOB,
        "layout_manifest_sha256": hashlib.sha256(layout_raw).hexdigest(),
        "fixture": args.fixture.as_posix(),
        "fixture_bytes": args.fixture.stat().st_size,
        "fixture_sha256": sha256(args.fixture),
        "language_descriptors": len(records),
        "bit_counts": bit_counts,
        "coverage": "one deterministic real tile/group/block record from every one of 252 language descriptors, all four output shards and all eight rows",
        "selections": selections,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "selections"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
