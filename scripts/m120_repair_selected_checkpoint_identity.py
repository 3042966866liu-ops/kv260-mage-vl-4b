#!/usr/bin/env python3
"""Repair M119 by byte-copying every unchanged M56 section into the new layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path


BLOCK = 8 << 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_region(path: Path, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        handle.seek(offset)
        remaining = length
        while remaining:
            block = handle.read(min(BLOCK, remaining))
            if not block:
                raise EOFError("short region while hashing")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def copy_region(source, destination, source_offset: int, destination_offset: int, length: int) -> None:
    source.seek(source_offset)
    destination.seek(destination_offset)
    remaining = length
    while remaining:
        block = source.read(min(BLOCK, remaining))
        if not block:
            raise EOFError("short source region while copying")
        destination.write(block)
        remaining -= len(block)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M120-selected-checkpoint-byte-identity-repair",
        "status": "FAIL",
        "classification": (
            "offline atomic checkpoint identity repair; not numerical quality, CSim, CoSim, "
            "FPGA, board, performance, video, or Web evidence"
        ),
    }
    started = time.perf_counter()
    temporary: Path | None = None
    try:
        source = args.source.resolve()
        candidate = args.candidate.resolve()
        output = args.output.resolve()
        if output.exists():
            raise FileExistsError(f"refusing to overwrite output: {output}")
        source_manifest_path = source / "CHECKPOINT_MANIFEST.json"
        candidate_manifest_path = candidate / "CHECKPOINT_MANIFEST.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        candidate_manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
        original_candidate_manifest = json.loads(
            candidate_manifest_path.read_text(encoding="utf-8")
        )
        if source_manifest.get("format") != candidate_manifest.get("format"):
            raise RuntimeError("source/candidate checkpoint format mismatch")
        source_entries = {entry["name"]: entry for entry in source_manifest["entries"]}
        candidate_entries = {entry["name"]: entry for entry in candidate_manifest["entries"]}
        if set(source_entries) != set(candidate_entries):
            raise RuntimeError("source/candidate parameter-name closure mismatch")

        ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
        selected = set(ranking["variants"]["top15"]["upgraded_modules"])
        selected |= {
            f"model.language_model.layers.{layer}.self_attn.{family}_proj"
            for layer in range(16)
            for family in ("k", "v")
        }
        if len(selected) != 54:
            raise RuntimeError("locked changed-module set is not 54")
        changed = {f"{name}.weight" for name in selected} | {"lm_head.weight"}
        for name in changed:
            entry = candidate_entries[name]
            if entry["kind"] != "packed" or int(entry["bits"]) != 4:
                raise RuntimeError(f"changed entry is not W4 packed: {name}")
        if int(candidate_entries["model.language_model.embed_tokens.weight"]["bits"]) != 3:
            raise RuntimeError("candidate embedding is not locked W3")

        source_blob = source / source_manifest["blob"]["path"]
        candidate_blob = candidate / candidate_manifest["blob"]["path"]
        if source_blob.stat().st_size != int(source_manifest["blob"]["bytes"]):
            raise RuntimeError("source blob size mismatch")
        if candidate_blob.stat().st_size != int(candidate_manifest["blob"]["bytes"]):
            raise RuntimeError("candidate blob size mismatch")
        if sha256_file(source_blob) != source_manifest["blob"]["sha256"]:
            raise RuntimeError("source blob hash mismatch")
        if sha256_file(candidate_blob) != candidate_manifest["blob"]["sha256"]:
            raise RuntimeError("candidate blob hash mismatch")

        temporary = output.with_name(f"{output.name}.tmp-{os.getpid()}")
        if temporary.exists():
            raise FileExistsError(f"temporary output already exists: {temporary}")
        temporary.mkdir(parents=True)
        repaired_blob = temporary / candidate_manifest["blob"]["path"]
        shutil.copyfile(candidate_blob, repaired_blob)

        copied_entry_count = 0
        copied_bytes = 0
        with source_blob.open("rb") as source_handle, repaired_blob.open("r+b") as repaired_handle:
            for name, target in candidate_entries.items():
                if name in changed:
                    continue
                origin = source_entries[name]
                if origin["kind"] != target["kind"]:
                    raise RuntimeError(f"entry kind changed unexpectedly: {name}")
                if target["kind"] == "raw":
                    if int(origin["section"]["bytes"]) != int(target["section"]["bytes"]):
                        raise RuntimeError(f"raw byte count changed: {name}")
                    copy_region(
                        source_handle,
                        repaired_handle,
                        int(origin["section"]["offset"]),
                        int(target["section"]["offset"]),
                        int(target["section"]["bytes"]),
                    )
                    target["section"]["sha256"] = origin["section"]["sha256"]
                    copied_bytes += int(target["section"]["bytes"])
                else:
                    if int(origin["bits"]) != int(target["bits"]):
                        raise RuntimeError(f"unchanged packed bit width changed: {name}")
                    for section_name in ("codes", "scales", "orientations"):
                        old_section = origin["sections"][section_name]
                        new_section = target["sections"][section_name]
                        if int(old_section["bytes"]) != int(new_section["bytes"]):
                            raise RuntimeError(f"unchanged section byte count changed: {name}/{section_name}")
                        copy_region(
                            source_handle,
                            repaired_handle,
                            int(old_section["offset"]),
                            int(new_section["offset"]),
                            int(new_section["bytes"]),
                        )
                        new_section["sha256"] = old_section["sha256"]
                        copied_bytes += int(new_section["bytes"])
                copied_entry_count += 1
            repaired_handle.flush()
            os.fsync(repaired_handle.fileno())

        unchanged_hash_drift = []
        for name, repaired_entry in candidate_entries.items():
            if name in changed:
                continue
            if repaired_entry["kind"] == "raw":
                section = repaired_entry["section"]
                observed = hash_region(repaired_blob, int(section["offset"]), int(section["bytes"]))
                if observed != source_entries[name]["section"]["sha256"]:
                    unchanged_hash_drift.append(name)
            else:
                for section_name in ("codes", "scales", "orientations"):
                    section = repaired_entry["sections"][section_name]
                    observed = hash_region(
                        repaired_blob, int(section["offset"]), int(section["bytes"])
                    )
                    if observed != source_entries[name]["sections"][section_name]["sha256"]:
                        unchanged_hash_drift.append(f"{name}/{section_name}")
                        break
        if unchanged_hash_drift:
            raise RuntimeError(f"unchanged section identity repair failed: {unchanged_hash_drift[:3]}")

        changed_hash_drift = []
        original_candidate_entries = {
            entry["name"]: entry for entry in original_candidate_manifest["entries"]
        }
        for name in sorted(changed):
            original_entry = original_candidate_entries[name]
            repaired_entry = candidate_entries[name]
            for section_name in ("codes", "scales", "orientations"):
                section = repaired_entry["sections"][section_name]
                observed = hash_region(repaired_blob, int(section["offset"]), int(section["bytes"]))
                if observed != original_entry["sections"][section_name]["sha256"]:
                    changed_hash_drift.append(f"{name}/{section_name}")
        if changed_hash_drift:
            raise RuntimeError(f"changed section drift during repair: {changed_hash_drift[:3]}")

        repaired_hash = sha256_file(repaired_blob)
        candidate_manifest["blob"]["sha256"] = repaired_hash
        candidate_manifest["derivation"] = {
            "gate": "M120-selected-checkpoint-byte-identity-repair",
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "candidate_manifest_sha256": sha256_file(candidate_manifest_path),
            "changed_parameter_count": len(changed),
            "unchanged_entry_count": copied_entry_count,
            "unchanged_copied_bytes": copied_bytes,
        }
        repaired_manifest_path = temporary / "CHECKPOINT_MANIFEST.json"
        repaired_manifest_path.write_text(
            json.dumps(candidate_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with repaired_manifest_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        temporary = None

        result.update(
            {
                "status": "PASS_UNCHANGED_M56_IDENTITY_REPAIRED",
                "source_manifest_sha256": sha256_file(source_manifest_path),
                "rejected_candidate_manifest_sha256": sha256_file(candidate_manifest_path),
                "changed_parameter_count": len(changed),
                "unchanged_entry_count": copied_entry_count,
                "unchanged_copied_bytes": copied_bytes,
                "artifact": {
                    "path": str(output),
                    "manifest_sha256": sha256_file(output / "CHECKPOINT_MANIFEST.json"),
                    "blob_sha256": repaired_hash,
                    "blob_bytes": (output / candidate_manifest["blob"]["path"]).stat().st_size,
                },
                "next_gate": (
                    "Run a fresh-process full reload, verify all declared section hashes, and rerun "
                    "the frozen text numerical/semantic gate against this exact repaired manifest."
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline repair gate; do not touch the board."
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_UNCHANGED_M56_IDENTITY_REPAIRED":
        return 1
    print("M120_UNCHANGED_IDENTITY_REPAIR_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
