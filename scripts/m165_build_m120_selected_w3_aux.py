#!/usr/bin/env python3
"""Replace the stale fixed-prompt embedding rows with exact M120 W3 rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


EXPECTED_MANIFEST_SHA = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
EXPECTED_M147_SHA = "2a0c2068190bb50f569850838bae1d975e56104047257dc93c1c975f9bcabfb3"
EMBEDDING = "model.language_model.embed_tokens.weight"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def boundary_metrics(actual, reference) -> dict:
    import numpy as np
    lhs = np.asarray(actual, dtype=np.float64)
    rhs = np.asarray(reference, dtype=np.float64)
    delta = lhs - rhs
    lhs_norm = float(np.linalg.norm(lhs))
    rhs_norm = float(np.linalg.norm(rhs))
    return {
        "finite": bool(np.isfinite(lhs).all() and np.isfinite(rhs).all()),
        "max_abs": float(np.max(np.abs(delta))),
        "relative_l2": float(np.linalg.norm(delta) / max(rhs_norm, 1.0e-30)),
        "cosine": float(np.vdot(lhs.ravel(), rhs.ravel()) / max(lhs_norm * rhs_norm, 1.0e-30)),
        "actual_sha256_fp32": hashlib.sha256(lhs.astype("<f4").tobytes()).hexdigest(),
        "reference_sha256_fp32": hashlib.sha256(rhs.astype("<f4").tobytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--m147", type=Path, required=True)
    parser.add_argument("--old-aux", type=Path, required=True)
    parser.add_argument("--old-manifest", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "date": "2026-09-01",
        "gate": "M165-M120-selected-W3-fixed-text-auxiliary",
        "status": "FAIL",
        "classification": "Offline correction of the fixed-prompt embedding identity only; not CSim, board, Layer-0 or E2E evidence.",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    output_partial = args.output.with_name(args.output.name + f".partial-{os.getpid()}")
    try:
        import numpy as np
        import torch
        scripts_root = args.repo.resolve() / "deployment/mage_vl4b/scripts"
        sys.path.insert(0, str(scripts_root))
        from mixed_bit_checkpoint import reconstruct_full_range_rows_from_storage, unpack_orientation_bits, unpack_unsigned_codes

        if args.output.exists() or args.manifest.exists() or output_partial.exists():
            raise RuntimeError("M165 clean outputs required")
        m147 = json.loads(args.m147.read_text(encoding="utf-8"))
        if sha256(args.m147) != EXPECTED_M147_SHA or m147.get("status") != "PASS":
            raise RuntimeError("M165 M147 predecessor mismatch")
        checkpoint = args.checkpoint.resolve()
        checkpoint_manifest = checkpoint / "CHECKPOINT_MANIFEST.json"
        if sha256(checkpoint_manifest) != EXPECTED_MANIFEST_SHA:
            raise RuntimeError("M165 checkpoint manifest mismatch")
        packed = json.loads(checkpoint_manifest.read_text(encoding="utf-8"))
        blob_info = packed["blob"]
        if blob_info.get("sha256") != EXPECTED_BLOB_SHA:
            raise RuntimeError("M165 blob declaration mismatch")
        blob_path = checkpoint / blob_info["path"]
        if blob_path.stat().st_size != int(blob_info["bytes"]):
            raise RuntimeError("M165 blob byte count mismatch")
        matches = [entry for entry in packed["entries"] if entry["name"] == EMBEDDING]
        if len(matches) != 1:
            raise RuntimeError("M165 embedding closure mismatch")
        entry = matches[0]
        if entry.get("shape") != [151936, 2560] or int(entry.get("bits", -1)) != 3 or int(entry.get("group_size", -1)) != 64:
            raise RuntimeError("M165 embedding policy mismatch")

        old_manifest = json.loads(args.old_manifest.read_text(encoding="utf-8"))
        selected = [int(value) for value in old_manifest["selected_embedding_ids"]]
        prompt = [int(value) for value in old_manifest["prompt_token_ids"]]
        if selected != sorted(set(selected)) or len(selected) != 23 or len(prompt) != 30:
            raise RuntimeError("M165 fixed prompt identity mismatch")
        with np.load(args.old_aux, allow_pickle=False) as old:
            arrays = {name: np.asarray(old[name]) for name in old.files}
        if set(arrays) != set(old_manifest["tensors"]):
            raise RuntimeError("M165 old auxiliary closure mismatch")

        groups_per_row = int(entry["padded_columns"]) // int(entry["group_size"])
        sections = entry["sections"]
        with blob_path.open("rb") as blob:
            blob.seek(int(sections["orientations"]["offset"]))
            orientations = unpack_orientation_bits(blob.read(int(sections["orientations"]["bytes"])), int(entry["group_count"]))
            restored_rows = []
            for row in selected:
                code_count = int(entry["padded_columns"])
                code_offset = row * int(entry["padded_columns"]) * int(entry["bits"]) // 8
                code_bytes = code_count * int(entry["bits"]) // 8
                scale_offset = row * groups_per_row * 2
                blob.seek(int(sections["codes"]["offset"]) + code_offset)
                codes = unpack_unsigned_codes(blob.read(code_bytes), int(entry["bits"]), code_count)
                blob.seek(int(sections["scales"]["offset"]) + scale_offset)
                scale_bits = np.frombuffer(blob.read(groups_per_row * 2), dtype=np.uint16)
                orientation_start = row * groups_per_row
                restored = reconstruct_full_range_rows_from_storage(
                    torch, codes, scale_bits,
                    orientations[orientation_start:orientation_start + groups_per_row],
                    3, 1, 2560, 64, output_dtype=torch.bfloat16,
                    scale_format=packed["scale_format"],
                )
                restored_rows.append(restored.to(torch.float16).cpu().numpy()[0])
        arrays[EMBEDDING] = np.stack(restored_rows).astype(np.float16, copy=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with output_partial.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(output_partial, args.output)

        mapping = {token: arrays[EMBEDDING][index].astype(np.float32) for index, token in enumerate(selected)}
        hidden = np.stack([mapping[token] for token in prompt]).astype(np.float32)
        weight = arrays["model.language_model.layers.0.input_layernorm.weight"].astype(np.float32)
        variance = np.mean(np.square(hidden), axis=-1, keepdims=True)
        normed = (hidden * (1.0 / np.sqrt(variance + 1.0e-6)) * weight).astype(np.float32)
        with np.load(args.boundaries, allow_pickle=False) as golden:
            first = boundary_metrics(normed, np.asarray(golden["layer00_q"], dtype=np.float32))
        if not first["finite"] or first["relative_l2"] > 0.05 or first["cosine"] < 0.998:
            raise RuntimeError(f"M165 corrected first boundary still fails: {first}")

        new_manifest = dict(old_manifest)
        new_manifest.update({
            "result": "PASS",
            "format": "tellme-m165-m120-w3-fixed-text-aux-fp16-v1",
            "classification": "fixed-prompt M120 W3 embedding rows plus identity-retained FP16 norms; not a general-chat embedding table",
            "source_model": str(checkpoint),
            "source_checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA,
            "source_blob_sha256": EXPECTED_BLOB_SHA,
            "embedding_source_bits": 3,
            "embedding_source_group_size": 64,
            "payload": args.output.name,
            "payload_bytes": args.output.stat().st_size,
            "payload_sha256": sha256(args.output),
        })
        atomic_json(args.manifest, new_manifest)
        result.update({
            "status": "PASS",
            "source_checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA,
            "source_blob_sha256": EXPECTED_BLOB_SHA,
            "selected_embedding_rows": len(selected),
            "embedding_source_bits": 3,
            "embedding_source_group_size": 64,
            "auxiliary": str(args.output.resolve()),
            "auxiliary_bytes": args.output.stat().st_size,
            "auxiliary_sha256": sha256(args.output),
            "auxiliary_manifest": str(args.manifest.resolve()),
            "auxiliary_manifest_sha256": sha256(args.manifest),
            "first_boundary_precheck": first,
            "next_gate": "Build a new clean Layer-0 package and rerun only Layer-0 on KV260.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M165 offline only; do not touch the board."
    finally:
        if output_partial.exists():
            output_partial.unlink()
    atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M165_M120_SELECTED_W3_AUX_PASS" if result["status"] == "PASS" else "M165_M120_SELECTED_W3_AUX_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
