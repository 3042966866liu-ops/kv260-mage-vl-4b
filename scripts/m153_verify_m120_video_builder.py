#!/usr/bin/env python3
"""Offline policy and negative-lock gate for the M153 video package builder."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/m153_build_m120_video_candidate.py"
OUTPUT = ROOT / "deployment/mage_vl4b/M153_M120_VIDEO_BUILDER_READINESS_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result: dict[str, object] = {"date": "2026-09-01", "gate": "M153-M120-video-builder-offline-readiness", "status": "FAIL", "classification": "Offline builder source/policy plus negative fixed-text lock test; no package generation, board, video or Web execution."}
    try:
        source = BUILDER.read_text(encoding="utf-8")
        ast.parse(source, filename=str(BUILDER))
        required = [
            "M153_LOCKED_UNTIL_M120_FIXED_TEXT_BOARD_E2E_PASS",
            "require_fixed_text(args.board_gate.resolve())",
            "M148-M120-W3-full-embedding-extraction",
            "M151_M120_TEXT_AUX_MANIFEST.json",
            "PACKAGE_MANIFEST.json",
            "PACKAGE_READY.json",
            "os.replace(staging, output)",
            "forbidden_cache_path_count",
            "frozen_849_token_prefill_calls",
            "decode_calls_per_subsequent_token",
            "vision_layout/SIXPORT_LAYOUT_MANIFEST.json",
            "text_runtime/SOURCE_MANIFEST.json",
            "M153-M120-PS-high-precision-vision-payload",
            "PS BF16 visual tower + M120/M89X2 FPGA language/head",
        ]
        missing = [token for token in required if token not in source]
        if missing:
            raise RuntimeError(f"M153 builder controls missing: {missing}")
        forbidden = ["m89y_language_fourport", "m89z2_lmhead_w4_fourport", "M79_FULL_TEXT_AUX_MANIFEST.json\" / embedding"]
        present = [token for token in forbidden if token in source]
        if present:
            raise RuntimeError(f"M153 builder contains stale payload route: {present}")
        if source.index("require_fixed_text(args.board_gate.resolve())") >= source.index("output = args.output.resolve()"):
            raise RuntimeError("M153 output inspection precedes fixed-text lock")

        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("m153_builder_lock_test", BUILDER)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load M153 builder")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        board = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
        try:
            module.require_fixed_text(board)
        except RuntimeError as exc:
            if str(exc) != "M153_LOCKED_UNTIL_M120_FIXED_TEXT_BOARD_E2E_PASS":
                raise RuntimeError(f"unexpected M153 lock error: {exc}") from exc
        else:
            raise RuntimeError("M153 unexpectedly accepted current non-PASS fixed-text state")

        result.update({
            "status": "PASS_BUILDER_READY_TEXT_E2E_LOCKED",
            "builder": "scripts/m153_build_m120_video_candidate.py",
            "builder_sha256": sha256(BUILDER),
            "current_fixed_text_negative_lock_test": "PASS",
            "fixed_text_gate_precedes_output_inspection": True,
            "m148_embedding_required": True,
            "m120_text_runtime_required": True,
            "immutable_vision_files_rehashed": True,
            "clean_whitelist_and_cache_rejection": True,
            "external_package_ready_hash": True,
            "old_m90_candidate_modified": False,
            "stale_visual_payload_route_rewritten_for_m120": True,
            "final_video_candidate_generated": False,
            "board_state_changed": False,
            "next_gate": "Complete fixed-text board E2E, run M148, then execute M153 once to generate the clean candidate."
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair M153 offline controls; do not generate a video package."
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M153_M120_VIDEO_BUILDER_READINESS_PASS" if str(result["status"]).startswith("PASS") else "M153_M120_VIDEO_BUILDER_READINESS_FAIL")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
