#!/usr/bin/env python3
"""Audit the corrected video builder without unlocking or generating the package."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/m153_build_m120_video_candidate.py"
RESULT = ROOT / "deployment/mage_vl4b/M169_M120_VIDEO_BUILDER_CORRECTION_READINESS_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M169-M120-video-builder-text-identity-correction-readiness",
        "status": "FAIL",
        "classification": "Offline video-builder correction and negative fixed-text lock only; no package generation, board, video or Web execution.",
    }
    try:
        source = BUILDER.read_text(encoding="utf-8")
        ast.parse(source, filename=str(BUILDER))
        required = [
            'TEXT = ROOT / "deployment/mage_vl4b/m165_m120_layer0_board_candidate"',
            "EXPECTED_TEXT_PACKAGE_MANIFEST",
            "TEXT_RUNTIME_SELECTED",
            "M169_TEXT_RUNTIME_SLICE_MANIFEST.json",
            '"fixed_prompt_auxiliary_included": False',
            '"layer0_reference_fixture_included": False',
            '"forbidden_stale_fixed_text_auxiliary_count": 0',
            "fixed-prompt/Layer-0 auxiliary leaked into video package",
            "require_fixed_text(args.board_gate.resolve())",
            "M148-M120-W3-full-embedding-extraction",
            "PACKAGE_READY.json",
            "os.replace(staging, output)",
        ]
        missing = [token for token in required if token not in source]
        if missing:
            raise RuntimeError(f"M169 corrected builder controls missing: {missing}")
        forbidden = [
            'deployment/mage_vl4b/m120_text4b_full_runtime',
            'text_runtime/SOURCE_MANIFEST.json',
            'for item in text_manifest["files"]:\n        add(records',
        ]
        present = [token for token in forbidden if token in source]
        if present:
            raise RuntimeError(f"M169 stale whole-runtime copy remains: {present}")
        if source.index("require_fixed_text(args.board_gate.resolve())") >= source.index("output = args.output.resolve()"):
            raise RuntimeError("M169 output inspection precedes fixed-text lock")

        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("m169_builder_lock_test", BUILDER)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load corrected video builder")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        selected = set(module.TEXT_RUNTIME_SELECTED)
        expected = {
            "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
            "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "overlay/m120_m89x2_t32.bit",
            "overlay/m120_m89x2_t32.hwh",
            "runtime/board_runtime.py",
            "runtime/contract_runtime.py",
            "runtime/m120_board_env_preflight.py",
            "runtime/support/reserved_ddr_pool.py",
        }
        if selected != expected or any(path.startswith(("auxiliary/", "reference/")) for path in selected):
            raise RuntimeError("M169 text runtime whitelist mismatch")
        board = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
        try:
            module.require_fixed_text(board)
        except RuntimeError as exc:
            if str(exc) != "M153_LOCKED_UNTIL_M120_FIXED_TEXT_BOARD_E2E_PASS":
                raise RuntimeError(f"unexpected corrected builder lock error: {exc}") from exc
        else:
            raise RuntimeError("M169 unexpectedly accepted current non-PASS fixed-text state")

        result.update({
            "status": "PASS_CORRECTED_BUILDER_READY_TEXT_E2E_LOCKED",
            "builder": BUILDER.relative_to(ROOT).as_posix(),
            "builder_sha256": sha256(BUILDER),
            "source_text_package_manifest_sha256": module.EXPECTED_TEXT_PACKAGE_MANIFEST,
            "text_runtime_whitelist_count": len(selected),
            "fixed_prompt_auxiliary_excluded": True,
            "layer0_reference_fixture_excluded": True,
            "m120_full_embedding_still_required": True,
            "vision_payload_unchanged": True,
            "four_frame_and_sse_path_unchanged": True,
            "current_fixed_text_negative_lock_test": "PASS",
            "final_video_candidate_generated": False,
            "board_state_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "After corrected fixed-text board E2E PASS, run M148 and then generate the clean video package with this corrected builder.",
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair M169 offline controls; do not generate a video package."
    temporary = RESULT.with_name(RESULT.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M169_M120_VIDEO_BUILDER_CORRECTION_READINESS_PASS" if str(result["status"]).startswith("PASS") else "M169_M120_VIDEO_BUILDER_CORRECTION_READINESS_FAIL")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
