#!/usr/bin/env python3
"""Freeze the exact M120 changes required for the stale M90 video candidate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "deployment" / "mage_vl4b" / "m90_video_board_candidate"
VIDEO_MANIFEST = VIDEO / "CANDIDATE_MANIFEST.json"
VISION = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m90_vision_w4_fourport"
BOARD = ROOT / "deployment" / "mage_vl4b" / "BOARD_GATE_RESULT.json"
M122 = ROOT / "deployment" / "mage_vl4b" / "M122_FROZEN_CHECKPOINT_VIDEO_RELOAD_RESULT.json"
M135 = ROOT / "deployment" / "mage_vl4b" / "M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json"
M141 = ROOT / "deployment" / "mage_vl4b" / "M141_M120_FULLTEXT_USB_SOURCE_AUDIT_RESULT.json"
M142 = ROOT / "deployment" / "mage_vl4b" / "M142_M120_FULL_RUNTIME_SOURCE_RESULT.json"
RESULT = ROOT / "deployment" / "mage_vl4b" / "M146_M120_VIDEO_REBASE_AUDIT_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result = {
        "date": "2026-09-01",
        "gate": "M146-M120-video-rebase-scope-audit",
        "status": "FAIL",
        "classification": "offline rebase-scope audit; no video package is generated or deployed",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        old = json.loads(VIDEO_MANIFEST.read_text(encoding="utf-8"))
        board = json.loads(BOARD.read_text(encoding="utf-8"))
        m122 = json.loads(M122.read_text(encoding="utf-8"))
        m135 = json.loads(M135.read_text(encoding="utf-8"))
        m141 = json.loads(M141.read_text(encoding="utf-8"))
        m142 = json.loads(M142.read_text(encoding="utf-8"))
        if m122.get("status") != "PASS_SEMANTIC_TOKEN_CHANGED":
            raise RuntimeError("M122 retained video semantic gate is not accepted")
        suite = m122.get("multi_video_suite", {})
        if suite.get("case_count") != 3 or suite.get("all_semantic_contracts_passed") is not True:
            raise RuntimeError("M122 three-case video suite closure failed")
        if m135.get("status") != "PASS" or m135.get("build_id") != "0x4D395832":
            raise RuntimeError("M135 M120 implementation identity mismatch")
        if m141.get("status") != "PASS" or not m141.get("language") or not m141.get("lm_head"):
            raise RuntimeError("M141 full-text payload audit mismatch")
        if m142.get("status") != "PASS" or m142.get("build_id") != "0x4D395832":
            raise RuntimeError("M142 runtime identity mismatch")

        vision_manifest_path = VISION / "SIXPORT_LAYOUT_MANIFEST.json"
        vision_manifest = json.loads(vision_manifest_path.read_text(encoding="utf-8"))
        if vision_manifest.get("module_count") != 98 or len(vision_manifest.get("files", [])) != 4:
            raise RuntimeError("vision layout geometry mismatch")
        verified_vision_files = []
        for item in vision_manifest["files"]:
            path = VISION / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"vision layout identity mismatch: {path}")
            verified_vision_files.append({
                "path": item["path"], "bytes": int(item["bytes"]), "sha256": item["sha256"]
            })

        declared_files = {item["path"]: item for item in old.get("candidate_files", [])}
        mismatches = []
        for relative, item in declared_files.items():
            path = VIDEO / relative
            observed = None if not path.is_file() else {
                "bytes": path.stat().st_size, "sha256": sha256(path)
            }
            if observed is None or observed["bytes"] != int(item["bytes"]) or observed["sha256"] != item["sha256"]:
                mismatches.append({"path": relative, "declared": item, "observed": observed})
        cache_paths = sorted(
            path.relative_to(VIDEO).as_posix()
            for path in VIDEO.rglob("*")
            if path.name == "__pycache__" or path.suffix == ".pyc"
        )

        prompt_tokens = 849
        batches = (prompt_tokens + 31) // 32
        old_prefill_calls = batches * 144 + 8
        new_prefill_calls = batches * 154 + 8
        old_decode_calls = 144 + 8
        new_decode_calls = 154 + 8
        text_fixed_pass = bool(
            board.get("latest_m120_fixed_text_e2e", {}).get("status") == "PASS"
        )

        result.update(
            {
                "status": "PASS_REBASE_SCOPE_FROZEN_TEXT_GATE_REQUIRED",
                "old_candidate": {
                    "manifest_sha256": sha256(VIDEO_MANIFEST),
                    "declared_build_id": old.get("fpga_build_id"),
                    "declared_language_manifest_sha256": old.get("layouts", {}).get("language", {}).get("manifest_sha256"),
                    "declared_lm_head_manifest_sha256": old.get("layouts", {}).get("lm_head", {}).get("manifest_sha256"),
                    "declared_text_auxiliary_manifest_sha256": old.get("text_auxiliary", {}).get("manifest_sha256"),
                    "manifest_file_mismatch_count": len(mismatches),
                    "manifest_file_mismatches": mismatches,
                    "forbidden_cache_path_count": len(cache_paths),
                    "forbidden_cache_paths": cache_paths,
                    "deployable": False,
                },
                "accepted_m120_text_identity": {
                    "build_id": "0x4D395832",
                    "kernel": "mage_m120_m89x2_0",
                    "runtime_source_manifest_sha256": m142["source_manifest_sha256"],
                    "language_manifest_sha256": m141["language"]["manifest_sha256"],
                    "language_files": m141["language"]["files"],
                    "lm_head_manifest_sha256": m141["lm_head"]["manifest_sha256"],
                    "lm_head_files": m141["lm_head"]["files"],
                    "embedding_policy": "M120 W3 embedding; old M79 FP16 full-text embedding may not be reused as the accepted model identity",
                    "language_chain_count": 154,
                    "lm_head_chain_count": 8,
                },
                "schedule_delta": {
                    "fixed_video_prompt_tokens": prompt_tokens,
                    "t32_batches": batches,
                    "old_prefill_calls": old_prefill_calls,
                    "m120_prefill_calls": new_prefill_calls,
                    "old_decode_calls_per_token": old_decode_calls,
                    "m120_decode_calls_per_token": new_decode_calls,
                    "reason": "M120 splits q and kv into separate chains for layers 0..9; old 144-language-chain accounting is invalid",
                },
                "immutable_vision_identity": {
                    "decision": "retain byte-for-byte",
                    "reason": "M122 passes the fixed and retained three-case video semantic suite with the immutable M120 checkpoint; M120 language precision changes do not alter visual W4 sections or PS BF16 visual activations",
                    "vision_layout_manifest_sha256": sha256(vision_manifest_path),
                    "module_count": vision_manifest["module_count"],
                    "files": verified_vision_files,
                    "retain_components": [
                        "official four-frame preprocessing fixture and binary request envelope",
                        "PS BF16 vision model code and vision_bf16.safetensors",
                        "M56-derived W4 visual packed weights and raw visual auxiliary",
                        "SSE framing and browser frame capture",
                    ],
                },
                "required_video_changes": [
                    "Generate a new clean candidate; never edit or promote the stale M90 directory/manifest.",
                    "Bind Build ID 0x4D395832, kernel mage_m120_m89x2_0, M126 language/head contracts and staged-low-cma runtime.",
                    "Replace old M89Y language and M89Z2 head layouts with the exact M141 M120 eight-shard identities.",
                    "Generate and hash-lock the full M120 W3 embedding auxiliary; retain text norms/tokenizer only after independent byte identity checks.",
                    "Update video language prefill/decode to split q and kv for layers 0..9 and merge qkv for layers 10..35.",
                    "Update proof accounting to 4166 prefill calls for the frozen 849-token request and 162 calls per subsequent token.",
                    "Use M120BoardRuntime and M120 package/environment preflight; remove all M89-X1 path and manifest assumptions.",
                    "Rebuild from a clean whitelist with zero __pycache__/.pyc and recursive SHA-256 closure.",
                    "Inherit the text gate order through fixed-text E2E before fixed-four-frame video, retained three-video suite, arbitrary video and Web.",
                ],
                "text_fixed_e2e_pass_now": text_fixed_pass,
                "video_rebase_generation_unlocked": text_fixed_pass,
                "video_candidate_generated": False,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": (
                    "Generate clean M120 video candidate"
                    if text_fixed_pass
                    else "Complete M138 -> M139 -> M140 -> M144 -> fixed-text M120 E2E; only then generate the clean video candidate"
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun this offline audit; do not modify or deploy M90."
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("M146_M120_VIDEO_REBASE_AUDIT_PASS" if result["status"].startswith("PASS_") else "M146_M120_VIDEO_REBASE_AUDIT_FAIL")
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
