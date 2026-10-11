#!/usr/bin/env python3
"""Build a clean hash-closed M218 dual-source board service delta."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m218_dual_source/m218_dual_source_delta"
RESULT = ROOT / "deployment/mage_vl4b/M218_DUAL_SOURCE_BOARD_DELTA_RESULT.json"
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
OFFLINE = ROOT / "deployment/mage_vl4b/M218_DUAL_SOURCE_FILE_REPLAY_OFFLINE_RESULT.json"
SOURCE = ROOT / "deployment/mage_vl4b/m218_file_replay_source"
EXPECTED_OFFLINE_SHA256 = "990c39fc9b8a1e62c195c8203b863d5c0bc5ff9429d8e94899a277b2b037bfbd"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    offline = json.loads(OFFLINE.read_text(encoding="utf-8"))
    if offline.get("status") != "PASS" or sha(OFFLINE) != EXPECTED_OFFLINE_SHA256:
        raise RuntimeError("M218 offline predecessor mismatch")
    m179 = board.get("latest_m120_fixed_text_board_gate", {})
    m198 = board.get("latest_m198_ps_vision_optimization", {})
    m208 = board.get("latest_m208_ps_vision_board_gate", {})
    m209 = board.get("latest_m209_continuous_stream_core", {})
    m212 = board.get("latest_m212_live_stream_service", {})
    if not (
        m179.get("status") == "PASS"
        and m179.get("formal_result_sha256") == "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"
        and m198.get("status") == "PASS"
        and m208.get("status") == "PASS"
        and m208.get("formal_result_sha256") == "2ff1d5823b97e349613abd15199e9db37630314a2d2c9b60fb4964658d47b23a"
        and str(m209.get("status", "")).startswith("OFFLINE_PASS")
        and str(m212.get("status", "")).startswith("PUBLIC_HTTPS_CONTROL_PLANE_PASS")
        and m212.get("formal_result_sha256") == "60b739b83ab1730132a0517142164113e8ceb53b4508045d55c294a1bda0fafc"
        and board.get("stable_rollback_preserved") is True
    ):
        raise RuntimeError("M218 board predecessor closure mismatch")
    summary = {
        "date": "2026-09-01",
        "gate": "M218-dual-source-predecessor-summary",
        "status": "PASS",
        "source_board_gate_sha256": sha(BOARD),
        "stable_rollback_preserved": True,
        "m179": {key: m179[key] for key in (
            "status", "candidate_build_id", "fpga_execution_proved",
            "cpu_linear_fallback", "formal_result_sha256",
        )},
        "m198": {key: m198[key] for key in (
            "status", "candidate_build_id", "fp32_encoder_layers", "formal_result_sha256",
        )},
        "m208": {key: m208[key] for key in (
            "status", "candidate_build_id", "metrics", "bf16_gemm_warning_count",
            "formal_result_sha256",
        )},
        "m209": {key: m209[key] for key in (
            "status", "runtime_load_count", "last_window_sequences", "formal_result_sha256",
        )},
        "m212": {
            "status": m212["status"],
            "package_manifest_sha256": m212["package_manifest_sha256"],
            "formal_result_sha256": m212["formal_result_sha256"],
            "public_https_result_sha256": m212["public_https_result_sha256"],
        },
        "m218_offline_result_sha256": sha(OFFLINE),
    }
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists():
        shutil.rmtree(OUT)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    (partial / "M218_PREDECESSOR_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sources = {
        "video_server.py": SOURCE / "video_server.py",
        "live_stream_core.py": SOURCE / "live_stream_core.py",
        "m206_ps_vision_runtime.py": SOURCE / "m206_ps_vision_runtime.py",
        "m207_ps_vision_runtime.py": SOURCE / "m207_ps_vision_runtime.py",
        "static/index.html": SOURCE / "static/index.html",
        "static/app.js": SOURCE / "static/app.js",
        "static/style.css": SOURCE / "static/style.css",
        "m218_verify_board_delta.py": ROOT / "scripts/m218_verify_board_delta.py",
        "m218_health_probe.py": ROOT / "scripts/m218_health_probe.py",
        "m218_board_preflight_and_restart.sh": ROOT / "scripts/m218_board_preflight_and_restart.sh",
        "M218_DUAL_SOURCE_FILE_REPLAY_OFFLINE_RESULT.json": OFFLINE,
    }
    for name, source in sources.items():
        destination = partial / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    entries = []
    for path in sorted(item for item in partial.rglob("*") if item.is_file()):
        name = path.relative_to(partial).as_posix()
        entries.append({"path": name, "bytes": path.stat().st_size, "sha256": sha(path)})
    if any(
        "__pycache__" in item["path"]
        or item["path"].endswith((".pyc", ".log", ".partial"))
        for item in entries
    ):
        raise RuntimeError("M218 forbidden package member")
    manifest = {
        "date": "2026-09-01",
        "gate": "M218-dual-source-service-board-delta",
        "status": "PASS",
        "build_id": "0x4D395832",
        "input_modes": ["browser-camera", "uploaded-file-loop"],
        "m208_formal_result_sha256": m208["formal_result_sha256"],
        "m212_formal_result_sha256": m212["formal_result_sha256"],
        "m218_offline_result_sha256": sha(OFFLINE),
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "excluded_patterns": ["__pycache__", "*.pyc", "*.log", "*.partial"],
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01",
        "gate": "M218-dual-source-service-board-delta-build",
        "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "board_state_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "COM3 same-terminal sudo preflight, manifest-first chunked upload, exact board preflight, transient M212-to-M218 service restart with automatic M212 rollback on failure.",
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("M218_BOARD_DELTA_BUILD_PASS")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
