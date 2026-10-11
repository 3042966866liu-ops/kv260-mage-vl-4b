#!/usr/bin/env python3
"""Offline identity/proof-accounting gate for the M120 video SSE server."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "deployment/mage_vl4b/m151_m120_video_rebase_source/video_server.py"
OUTPUT = ROOT / "deployment/mage_vl4b/M152_M120_VIDEO_SERVER_REBASE_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M152-M120-video-SSE-server-rebase",
        "status": "FAIL",
        "classification": "Offline server source identity/proof-accounting gate only; no server, board, video, or Web execution.",
    }
    try:
        source = SERVER.read_text(encoding="utf-8")
        ast.parse(source, filename=str(SERVER))
        required = [
            'BUILD_ID = "0x4D395832"',
            'KERNEL = "mage_m120_m89x2_0"',
            "latest_m120_fixed_text_e2e",
            "M120BoardRuntime",
            "PACKAGE_READY.json",
            "candidate_manifest_external_hash",
            'weight_mode="staged-low-cma"',
            "M120VideoLanguageModel",
            "expected_physical_calls(len(ids), len(generated))",
            'after["logical_calls"]',
            'after["logical_expected_macros"]',
            '"language_cpu_linear_fallback": False',
            '"/api/4b/video/stream"',
            '"text/event-stream; charset=utf-8"',
            '"vision_backend": "PS BF16 activation + immutable exact W4 weights; visual A8 disabled"',
        ]
        missing = [token for token in required if token not in source]
        if missing:
            raise RuntimeError(f"M152 server controls missing: {missing}")
        forbidden = [
            "0x4d395831",
            "M89XBoardRuntime",
            "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
            "M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "M79_FULL_TEXT_AUX_MANIFEST.json",
            "resident-high-ddr",
            "3896 + 152",
            "candidate_manifest_self_hash",
            "candidate_manifest.get(\"self_sha256\")",
        ]
        present = [token for token in forbidden if token in source]
        if present:
            raise RuntimeError(f"M152 server retains stale identity: {present}")
        fixed_index = source.index('fixed = board_gate.get("latest_m120_fixed_text_e2e")')
        load_index = source.index("board = M120BoardRuntime(")
        if fixed_index >= load_index:
            raise RuntimeError("fixed-text preflight is not evaluated before overlay construction")

        result.update(
            {
                "status": "PASS_SERVER_SOURCE_ONLY_TEXT_E2E_LOCKED",
                "server": {
                    "path": SERVER.relative_to(ROOT).as_posix(),
                    "bytes": SERVER.stat().st_size,
                    "sha256": sha256(SERVER),
                },
                "build_id": "0x4D395832",
                "kernel": "mage_m120_m89x2_0",
                "fixed_text_board_e2e_required_before_load": True,
                "package_manifest_hash_source": "external PACKAGE_READY.json; no self-referential hash",
                "weight_mode": "staged-low-cma",
                "proof_counter": "logical_calls/logical_expected_macros",
                "prompt_length_aware_call_accounting": True,
                "language_cpu_linear_fallback": False,
                "transport": "bounded binary four-frame request plus SSE token stream",
                "final_video_candidate_generated": False,
                "server_started": False,
                "board_state_changed": False,
                "next_gate": "After fixed-text board PASS, generate the M148 embedding, assemble a clean whitelist package, then run offline preflight and video gates before Web.",
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair this same M152 source gate; do not start or deploy the video service."
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M152_M120_VIDEO_SERVER_REBASE_PASS" if str(result["status"]).startswith("PASS") else "M152_M120_VIDEO_SERVER_REBASE_FAIL")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
