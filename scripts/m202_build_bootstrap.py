#!/usr/bin/env python3
"""Build the clean M202 fixed-video E2E UART bootstrap."""

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m202_video_e2e/m202_gate_v2"
RESULT = ROOT / "deployment/mage_vl4b/M202_FIXED_VIDEO_E2E_BOOTSTRAP_RESULT.json"
M198 = ROOT / "deployment/mage_vl4b/M198_M197_PS_VISION_BOARD_RESULT_01.json"
M200 = ROOT / "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json"
SOURCE = ROOT / "deployment/mage_vl4b/m200_video_e2e_overlay_source"
M198_SHA = "b05671184eddb853c30091f3f0cb4718f5a96be9080dee210387bd483cce3209"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    m198 = json.loads(M198.read_text(encoding="utf-8"))
    if sha256(M198) != M198_SHA or m198.get("status") != "PASS":
        raise RuntimeError("M202 exact M198 predecessor mismatch")
    m200 = json.loads(M200.read_text(encoding="utf-8"))
    if m200.get("status") != "PASS_SOURCE_READY" or not m200.get("m198_board_predecessor_present"):
        raise RuntimeError("M202 M200 source is not unlocked")
    board_source = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_source.read_text(encoding="utf-8-sig"))
    fixed = board.get("latest_m120_fixed_text_board_gate", {})
    optimized = board.get("latest_m198_ps_vision_optimization", {})
    if (fixed.get("status") != "PASS" or
            fixed.get("formal_result_sha256") != "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3" or
            optimized.get("status") != "PASS" or
            optimized.get("formal_result_sha256") != M198_SHA or
            board.get("stable_rollback_preserved") is not True):
        raise RuntimeError("M202 authoritative board predecessor summary mismatch")
    reduced_board = {
        "source_board_gate_sha256": sha256(board_source),
        "stable_rollback_preserved": True,
        "latest_m120_fixed_text_board_gate": {
            "status": fixed["status"],
            "candidate_build_id": fixed["candidate_build_id"],
            "fpga_execution_proved": fixed["fpga_execution_proved"],
            "cpu_linear_fallback": fixed["cpu_linear_fallback"],
            "formal_result_sha256": fixed["formal_result_sha256"],
        },
        "latest_m198_ps_vision_optimization": {
            "status": optimized["status"],
            "candidate_build_id": optimized["candidate_build_id"],
            "fp32_encoder_layers": optimized["fp32_encoder_layers"],
            "formal_result_sha256": optimized["formal_result_sha256"],
        },
    }
    reduced_path = ROOT / "tmp/m202_video_e2e/BOARD_GATE_RESULT.min.json"
    reduced_path.parent.mkdir(parents=True, exist_ok=True)
    reduced_path.write_text(json.dumps(reduced_board, indent=2) + "\n", encoding="utf-8")
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists() or partial.exists():
        raise RuntimeError("M202 clean output required")
    partial.mkdir(parents=True)
    sources = {
        "m202_fixed_video_e2e_board_gate.py": ROOT / "scripts/m202_fixed_video_e2e_board_gate.py",
        "m202_run_fixed_video_e2e.sh": ROOT / "scripts/m202_run_fixed_video_e2e.sh",
        "m202_verify_bootstrap.py": ROOT / "scripts/m202_verify_bootstrap.py",
        "video_server.py": SOURCE / "video_server.py",
        "ps_vision_runtime.py": SOURCE / "ps_vision_runtime.py",
        "BOARD_GATE_RESULT.json": reduced_path,
        "M198_M197_PS_VISION_BOARD_RESULT_01.json": M198,
        "M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json": M200,
    }
    entries = []
    for name, source in sources.items():
        destination = partial / name
        shutil.copyfile(source, destination)
        entries.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M202-M200-fixed-video-E2E-bootstrap",
        "status": "PASS",
        "build_id": "0x4D395832",
        "m198_sha256": M198_SHA,
        "m200_source_audit_sha256": sha256(M200),
        "source_board_gate_sha256": reduced_board["source_board_gate_sha256"],
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "excluded_patterns": ["__pycache__", "*.pyc", "*.log"],
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01",
        "gate": "M202-M200-fixed-video-E2E-bootstrap-build",
        "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "board_state_changed": False,
        "next_gate": "COM3 same-terminal environment preflight, then fixed four-frame E2E only.",
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M202_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
