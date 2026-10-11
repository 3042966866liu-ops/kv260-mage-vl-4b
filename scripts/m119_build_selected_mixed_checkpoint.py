#!/usr/bin/env python3
"""Build the frozen M119 text-4B mixed-precision checkpoint, fail closed."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def packed_bytes(entry: dict) -> int:
    return sum(int(section["bytes"]) for section in entry["sections"].values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--top15-cache", type=Path, required=True)
    parser.add_argument("--early-attention-cache", type=Path, required=True)
    parser.add_argument("--mid-kv-cache", type=Path, required=True)
    parser.add_argument("--lmhead", type=Path, required=True)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M119-frozen-text4b-selected-mixed-checkpoint-build",
        "status": "FAIL",
        "classification": (
            "offline atomic checkpoint build; not CSim, CoSim, FPGA, board, "
            "performance, video, or Web evidence"
        ),
    }
    started = time.perf_counter()
    try:
        workspace = Path(__file__).resolve().parents[1]
        runtime_scripts = workspace / "deployment" / "mage_vl4b" / "scripts"
        sys.path.insert(0, str(args.deps.resolve()))
        sys.path.insert(0, str(runtime_scripts.resolve()))
        sys.path.insert(0, str((workspace / "scripts").resolve()))

        import numpy as np
        import torch
        from safetensors import safe_open
        from transformers import AutoModelForCausalLM

        from m110_mixed_precision_multitext_gate import (
            load_calibrated_cache_manifest,
            load_genuine_w4_head,
        )
        from mixed_bit_checkpoint import (
            reconstruct_full_range_rows_from_storage,
            unpack_orientation_bits,
            unpack_unsigned_codes,
        )
        from packed_checkpoint_artifact import (
            load_packed_checkpoint,
            write_packed_checkpoint,
        )

        torch.set_num_threads(args.threads)
        source_manifest_path = args.checkpoint.resolve() / "CHECKPOINT_MANIFEST.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest.get("format") != "tellme-mage-vl-mixed-bit-v1-artifact-v1":
            raise RuntimeError("unsupported M56 checkpoint format")

        ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
        top15 = set(ranking["variants"]["top15"]["upgraded_modules"])
        if len(top15) != 22:
            raise RuntimeError("locked top15 target count is not 22")
        early_kv = {
            f"model.language_model.layers.{layer}.self_attn.{family}_proj"
            for layer in range(10)
            for family in ("k", "v")
        }
        mid_kv = {
            f"model.language_model.layers.{layer}.self_attn.{family}_proj"
            for layer in range(10, 16)
            for family in ("k", "v")
        }
        selected = top15 | early_kv | mid_kv
        if len(selected) != 54:
            raise RuntimeError("selected module set is not the locked 54-module union")

        caches = (
            (args.top15_cache.resolve(), load_calibrated_cache_manifest(args.top15_cache.resolve(), 22), top15),
            (
                args.early_attention_cache.resolve(),
                load_calibrated_cache_manifest(args.early_attention_cache.resolve(), 40),
                early_kv,
            ),
            (args.mid_kv_cache.resolve(), load_calibrated_cache_manifest(args.mid_kv_cache.resolve(), 12), mid_kv),
        )
        if set(caches[0][1]["targets"]) != top15:
            raise RuntimeError("top15 cache target identity mismatch")
        if not early_kv <= set(caches[1][1]["targets"]):
            raise RuntimeError("early K/V cache target identity mismatch")
        if set(caches[2][1]["targets"]) != mid_kv:
            raise RuntimeError("mid K/V cache target identity mismatch")

        print("[M119] loading official model shell", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        modules = dict(model.named_modules())
        m56_reload = load_packed_checkpoint(
            torch, model, args.checkpoint.resolve(), verify_blob=True, row_chunk=32
        )

        copied: set[str] = set()
        for cache_root, cache_manifest, wanted in caches:
            for item in cache_manifest["files"]:
                shard = cache_root / item["path"]
                with safe_open(str(shard), framework="pt", device="cpu") as handle:
                    for tensor_name in handle.keys():
                        name = tensor_name.removesuffix(".weight")
                        if name not in wanted:
                            continue
                        if name in copied:
                            raise RuntimeError(f"duplicate selected cache tensor: {name}")
                        tensor = handle.get_tensor(tensor_name)
                        parameter = modules[name].weight
                        if tuple(tensor.shape) != tuple(parameter.shape):
                            raise RuntimeError(f"selected cache shape mismatch: {name}")
                        parameter.data.copy_(tensor.to(dtype=parameter.dtype))
                        copied.add(name)
        if copied != selected:
            raise RuntimeError(f"selected cache closure mismatch missing={sorted(selected-copied)[:3]}")

        head_info = load_genuine_w4_head(
            torch,
            np,
            model,
            args.lmhead.resolve(),
            (
                unpack_orientation_bits,
                unpack_unsigned_codes,
                reconstruct_full_range_rows_from_storage,
            ),
        )

        source_entries = {entry["name"]: entry for entry in source_manifest["entries"]}
        storage_targets = {
            entry["module"]: int(entry["bits"])
            for entry in source_manifest["entries"]
            if entry["kind"] == "packed"
        }
        for name in selected:
            if name not in storage_targets:
                raise RuntimeError(f"selected module was not packed in M56: {name}")
            storage_targets[name] = 4
        storage_targets["lm_head"] = 4

        output = args.output.resolve()
        manifest = write_packed_checkpoint(
            torch,
            model,
            storage_targets,
            output,
            source_checkpoint=str(args.model.resolve()),
            checkpoint_config_sha256=sha256_file(args.model.resolve() / "config.json"),
            checkpoint_index_sha256=sha256_file(
                args.model.resolve() / "model.safetensors.index.json"
            ),
            scale_format="fp16",
            scale_search="exhaustive",
            row_chunk=32,
            apply_reconstructed=True,
        )

        new_entries = {entry["name"]: entry for entry in manifest["entries"]}
        changed_parameters = {f"{name}.weight" for name in selected} | {"lm_head.weight"}
        unchanged_mismatches = []
        for name, old in source_entries.items():
            if old["kind"] != "packed" or name in changed_parameters:
                continue
            new = new_entries[name]
            if int(new["bits"]) != int(old["bits"]):
                unchanged_mismatches.append({"name": name, "reason": "bits"})
                continue
            for section_name in ("codes", "scales", "orientations"):
                if new["sections"][section_name]["sha256"] != old["sections"][section_name]["sha256"]:
                    unchanged_mismatches.append(
                        {"name": name, "reason": f"{section_name}_sha256"}
                    )
                    break
        if unchanged_mismatches:
            raise RuntimeError(
                f"unchanged M56 packed identity drifted: {unchanged_mismatches[:3]}"
            )

        wrong_selected = [
            name for name in sorted(selected)
            if int(new_entries[f"{name}.weight"]["bits"]) != 4
        ]
        if wrong_selected or int(new_entries["lm_head.weight"]["bits"]) != 4:
            raise RuntimeError("selected checkpoint bit policy mismatch")

        head_manifest = json.loads(
            (args.lmhead.resolve() / "LM_HEAD_MANIFEST.json").read_text(encoding="utf-8")
        )
        for section_name in ("codes", "scales", "orientations"):
            if (
                new_entries["lm_head.weight"]["sections"][section_name]["sha256"]
                != head_manifest["blob"]["sections"][section_name]["sha256"]
            ):
                raise RuntimeError(f"M109 LM-head identity drifted: {section_name}")

        source_packed_bytes = sum(
            packed_bytes(entry) for entry in source_manifest["entries"] if entry["kind"] == "packed"
        )
        new_packed_bytes = sum(
            packed_bytes(entry) for entry in manifest["entries"] if entry["kind"] == "packed"
        )
        result.update(
            {
                "status": "PASS_FROZEN_CHECKPOINT_BUILT",
                "policy": {
                    "embedding": "M56-W3",
                    "lm_head": "official-source-genuine-W4",
                    "calibrated_w4_modules": sorted(selected),
                    "calibrated_w4_module_count": len(selected),
                    "all_other_packed_modules": "unchanged-M56-bit-policy-and-section-hashes",
                },
                "source": {
                    "manifest_sha256": sha256_file(source_manifest_path),
                    "blob_sha256": source_manifest["blob"]["sha256"],
                    "reload": m56_reload,
                },
                "caches": [
                    {
                        "path": str(root),
                        "manifest_sha256": sha256_file(root / "CACHE_MANIFEST.json"),
                        "used_target_count": len(wanted),
                    }
                    for root, _manifest, wanted in caches
                ],
                "lm_head": head_info,
                "artifact": {
                    "path": str(output),
                    "manifest_sha256": sha256_file(output / "CHECKPOINT_MANIFEST.json"),
                    "blob_sha256": manifest["blob"]["sha256"],
                    "blob_bytes": manifest["blob"]["bytes"],
                    "packed_module_count": manifest["packed_module_count"],
                    "incremental_packed_bytes_over_m56": new_packed_bytes - source_packed_bytes,
                    "unchanged_packed_identity_mismatch_count": 0,
                },
                "next_gate": (
                    "Run a fresh-process reload and the frozen text semantic/numerical suite against "
                    "this exact manifest before any descriptor or board work."
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = (
            "Correct this same offline checkpoint-build gate; do not create descriptors or touch the board."
        )
    finally:
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_FROZEN_CHECKPOINT_BUILT":
        return 1
    print("M119_FROZEN_CHECKPOINT_BUILD_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
