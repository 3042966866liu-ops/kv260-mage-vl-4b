#!/usr/bin/env python3
"""Verify the first clean M120 video-language rebase source slice."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m151_m120_video_rebase_source"
RUNTIME = SOURCE / "video_language_runtime.py"
TEST = SOURCE / "test_video_language_schedule.py"
M146 = ROOT / "deployment/mage_vl4b/M146_M120_VIDEO_REBASE_AUDIT_RESULT.json"
OUTPUT = ROOT / "deployment/mage_vl4b/M151_M120_VIDEO_LANGUAGE_REBASE_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M151-M120-video-language-runtime-rebase",
        "status": "FAIL",
        "classification": "Offline rebased language-runtime source and deterministic scheduling test only; no final video package, board, video, or Web execution.",
    }
    try:
        audit = json.loads(M146.read_text(encoding="utf-8"))
        if audit.get("status") != "PASS_REBASE_SCOPE_FROZEN_TEXT_GATE_REQUIRED":
            raise RuntimeError("M146 rebase scope is not accepted")
        if audit.get("video_candidate_generated") is not False:
            raise RuntimeError("M146 unexpectedly reports an existing clean video candidate")
        runtime_source = RUNTIME.read_text(encoding="utf-8")
        test_source = TEST.read_text(encoding="utf-8")
        ast.parse(runtime_source, filename=str(RUNTIME))
        ast.parse(test_source, filename=str(TEST))
        required = [
            'BUILD_ID = "0x4D395832"',
            "EARLY_SPLIT_LAYERS = 10",
            "LANGUAGE_CHAIN_CALLS_PER_T32_BATCH = 154",
            "LM_HEAD_CHAIN_CALLS = 8",
            "DECODE_CHAIN_CALLS_PER_TOKEN = 162",
            'self._family(layer, "q", values)',
            'self._family(layer, "kv", values)',
            'self._family(layer, "qkv", values)',
            "M151_M120_TEXT_AUX_MANIFEST.json",
            "source_bits",
            "source_group_size",
        ]
        missing = [token for token in required if token not in runtime_source]
        if missing:
            raise RuntimeError(f"M151 runtime controls missing: {missing}")
        forbidden = ["M89XBoardRuntime", "0x4d395831", "M79_FULL_TEXT_AUX_MANIFEST.json"]
        present = [token for token in forbidden if token in runtime_source]
        if present:
            raise RuntimeError(f"M151 runtime retains stale text identity: {present}")

        sys.dont_write_bytecode = True
        sys.path.insert(0, str(SOURCE))
        spec = importlib.util.spec_from_file_location("m151_schedule_test", TEST)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load M151 scheduling test")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.main() != 0:
            raise RuntimeError("M151 scheduling test returned nonzero")

        result.update(
            {
                "status": "PASS_RUNTIME_SOURCE_ONLY_TEXT_E2E_LOCKED",
                "build_id": "0x4D395832",
                "kernel": "mage_m120_m89x2_0",
                "runtime": {
                    "path": RUNTIME.relative_to(ROOT).as_posix(),
                    "bytes": RUNTIME.stat().st_size,
                    "sha256": sha256(RUNTIME),
                },
                "test": {
                    "path": TEST.relative_to(ROOT).as_posix(),
                    "bytes": TEST.stat().st_size,
                    "sha256": sha256(TEST),
                    "status": "PASS",
                },
                "early_layers": {"range": "0..9", "families": ["q", "kv", "attention_out", "gate_up", "mlp_down"]},
                "late_layers": {"range": "10..35", "families": ["qkv", "attention_out", "gate_up", "mlp_down"]},
                "language_chain_calls_per_t32_batch": 154,
                "lm_head_chain_calls": 8,
                "frozen_849_token_prefill_calls": 4166,
                "decode_calls_per_subsequent_token": 162,
                "m120_w3_embedding_manifest_required": True,
                "immutable_vision_layout_manifest_sha256": audit["immutable_vision_identity"]["vision_layout_manifest_sha256"],
                "vision_redesign_required": False,
                "video_language_rebase_required": True,
                "final_video_candidate_generated": False,
                "board_state_changed": False,
                "next_gate": "Complete M120 fixed-text board E2E; then finish the M120 server/preflight rebase, generate the M148 embedding, and build a clean whitelisted video package.",
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair this same offline video-language source gate; do not generate or deploy a video package."
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M151_M120_VIDEO_LANGUAGE_REBASE_PASS" if str(result["status"]).startswith("PASS") else "M151_M120_VIDEO_LANGUAGE_REBASE_FAIL")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
