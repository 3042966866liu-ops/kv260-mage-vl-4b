#!/usr/bin/env python3
"""Audit M200 video-service source while keeping package creation locked to M198."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m200_video_e2e_overlay_source"
M197 = ROOT / "deployment/mage_vl4b/m197_ps_vision_fp32_block_candidate/M197_OFFLINE_FP32_LAYERS_06_23.json"
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
RESULT = ROOT / "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json"
M197_SHA = "c0321dff2a1e1401eebe0741cde7758befc1672d0aa29963df7af9b9df0b7bb9"
LAYERS = list(range(6, 24))


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def main() -> int:
    files = [SOURCE / "video_server.py", SOURCE / "ps_vision_runtime.py"]
    for path in files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offline = json.loads(M197.read_text(encoding="utf-8"))
    if sha256(M197) != M197_SHA or offline.get("status") != "PASS":
        raise RuntimeError("M200 exact M197 offline result mismatch")
    if offline.get("fp32_encoder_layers") != LAYERS:
        raise RuntimeError("M200 M197 layer policy mismatch")
    server = files[0].read_text(encoding="utf-8")
    required_contracts = (
        'compute="bf16"',
        "fp32_layers=range(6, 24)",
        'board_gate.get("latest_m120_fixed_text_board_gate")',
        'fixed.get("formal_result_sha256") == FIXED_TEXT_RESULT_SHA',
        'board_gate.get("latest_m198_ps_vision_optimization")',
        'optimized_vision.get("status") == "PASS"',
        'optimized_vision.get("fp32_encoder_layers") == list(range(6, 24))',
        '"language_cpu_linear_fallback": False',
    )
    missing = [item for item in required_contracts if item not in server]
    if missing:
        raise RuntimeError(f"M200 source contract missing: {missing}")
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    m198 = board.get("latest_m198_ps_vision_optimization")
    unlocked = (
        isinstance(m198, dict)
        and m198.get("status") == "PASS"
        and m198.get("fp32_encoder_layers") == LAYERS
    )
    package = ROOT / "deployment/mage_vl4b/m200_video_e2e_overlay"
    if not unlocked and package.exists():
        raise RuntimeError("M200 package exists while M198 predecessor is absent")
    result = {
        "date": "2026-09-01",
        "gate": "M200-M197-video-service-overlay-source-audit",
        "status": "PASS_SOURCE_READY" if unlocked else "PASS_SOURCE_READY_M198_LOCKED",
        "source_files": [
            {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
        "m197_offline_result_sha256": M197_SHA,
        "fp32_encoder_layers": LAYERS,
        "m198_board_predecessor_present": unlocked,
        "overlay_package_generated": False,
        "video_language_fpga_e2e_executed": False,
        "web_deployed": False,
        "board_state_changed": False,
        "next_gate": (
            "Build the clean M200 overlay only after exact M198 real-board PASS."
            if not unlocked else "Build the clean M200 overlay, then run fixed video-language FPGA E2E."
        ),
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M200_VIDEO_OVERLAY_SOURCE_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
