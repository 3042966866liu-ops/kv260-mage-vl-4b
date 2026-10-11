#!/usr/bin/env python3
"""Audit the exact packed M120 W3 full embedding before any video rebase."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


EXPECTED_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
EMBEDDING_NAME = "model.language_model.embed_tokens.weight"
EXPECTED_SHAPE = [151936, 2560]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_region(handle, offset: int, size: int) -> str:
    digest = hashlib.sha256()
    handle.seek(offset)
    remaining = size
    while remaining:
        block = handle.read(min(16 << 20, remaining))
        if not block:
            raise RuntimeError("short packed-embedding section read")
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "date": "2026-09-01",
        "gate": "M147-M120-W3-full-embedding-source-audit",
        "status": "FAIL",
        "classification": "read-only packed-section audit; no embedding extraction, video package or board action",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        checkpoint = args.checkpoint.resolve()
        manifest_path = checkpoint / "CHECKPOINT_MANIFEST.json"
        if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("M120 checkpoint manifest identity mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        blob_info = manifest["blob"]
        blob_path = checkpoint / blob_info["path"]
        if blob_info.get("sha256") != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M120 declared blob identity mismatch")
        if blob_path.stat().st_size != int(blob_info["bytes"]):
            raise RuntimeError("M120 blob size mismatch")
        matches = [entry for entry in manifest["entries"] if entry["name"] == EMBEDDING_NAME]
        if len(matches) != 1:
            raise RuntimeError(f"embedding entry count mismatch: {len(matches)}")
        entry = matches[0]
        if entry.get("kind") != "packed" or entry.get("shape") != EXPECTED_SHAPE:
            raise RuntimeError("embedding kind/shape mismatch")
        if int(entry.get("bits", -1)) != 3 or int(entry.get("group_size", -1)) != 64:
            raise RuntimeError("embedding is not W3-G64")
        if int(entry.get("padded_columns", -1)) != 2560:
            raise RuntimeError("embedding padded-column mismatch")
        sections = entry.get("sections", {})
        if set(sections) != {"codes", "scales", "orientations"}:
            raise RuntimeError("embedding packed-section closure mismatch")
        verified = {}
        with blob_path.open("rb") as blob:
            for name, section in sections.items():
                observed = sha256_region(blob, int(section["offset"]), int(section["bytes"]))
                if observed != section["sha256"]:
                    raise RuntimeError(f"embedding {name} section hash mismatch")
                verified[name] = {
                    "offset": int(section["offset"]),
                    "bytes": int(section["bytes"]),
                    "sha256": observed,
                }
        output_bytes = EXPECTED_SHAPE[0] * EXPECTED_SHAPE[1] * 2
        result.update(
            {
                "status": "PASS",
                "checkpoint": str(checkpoint),
                "checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "declared_blob_sha256": EXPECTED_BLOB_SHA256,
                "declared_blob_bytes": int(blob_info["bytes"]),
                "embedding": {
                    "name": EMBEDDING_NAME,
                    "shape": EXPECTED_SHAPE,
                    "dtype": entry["dtype"],
                    "bits": 3,
                    "group_size": 64,
                    "group_count": int(entry["group_count"]),
                    "scale_search": entry.get("scale_search"),
                    "sections": verified,
                    "dequantized_fp16_rowmajor_bytes": output_bytes,
                },
                "extraction_started": False,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "After M120 fixed-text board E2E passes, stream-dequantize this exact W3 entry to a new hash-locked FP16 row-major auxiliary; do not reuse the old M79 FP16 embedding.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun this read-only source audit."
    atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M147_M120_W3_EMBEDDING_AUDIT_PASS" if result["status"] == "PASS" else "M147_M120_W3_EMBEDDING_AUDIT_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
