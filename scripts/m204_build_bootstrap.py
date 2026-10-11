#!/usr/bin/env python3
"""Build the hash-closed M204 bounded continuous-video UART bootstrap."""

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m204_continuous_video/m204_gate"
RESULT = ROOT / "deployment/mage_vl4b/M204_CONTINUOUS_VIDEO_BOOTSTRAP_RESULT.json"
M202 = ROOT / "deployment/mage_vl4b/M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json"
M202_SHA = "47fa5da23cde794994062979f113c4cdea224614c1277976c66d85dd3f259d98"
SOURCE = ROOT / "deployment/mage_vl4b/m200_video_e2e_overlay_source"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    m202 = json.loads(M202.read_text(encoding="utf-8"))
    if sha256(M202) != M202_SHA or m202.get("status") != "PASS":
        raise RuntimeError("M204 exact M202 predecessor mismatch")
    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8-sig"))
    fixed = board["latest_m120_fixed_text_board_gate"]
    optimized = board["latest_m198_ps_vision_optimization"]
    if board.get("latest_m202_fixed_video_e2e", {}).get("formal_result_sha256") != M202_SHA:
        raise RuntimeError("M204 authoritative M202 state mismatch")
    reduced = {
        "source_board_gate_sha256": sha256(board_path), "stable_rollback_preserved": True,
        "latest_m120_fixed_text_board_gate": {
            "status": fixed["status"], "candidate_build_id": fixed["candidate_build_id"],
            "fpga_execution_proved": fixed["fpga_execution_proved"],
            "cpu_linear_fallback": fixed["cpu_linear_fallback"],
            "formal_result_sha256": fixed["formal_result_sha256"],
        },
        "latest_m198_ps_vision_optimization": {
            "status": optimized["status"], "candidate_build_id": optimized["candidate_build_id"],
            "fp32_encoder_layers": optimized["fp32_encoder_layers"],
            "formal_result_sha256": optimized["formal_result_sha256"],
        },
    }
    reduced_path = ROOT / "tmp/m204_continuous_video/BOARD_GATE_RESULT.min.json"
    reduced_path.parent.mkdir(parents=True, exist_ok=True)
    reduced_path.write_text(json.dumps(reduced, indent=2) + "\n", encoding="utf-8")
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists() or partial.exists():
        raise RuntimeError("M204 clean output required")
    partial.mkdir(parents=True)
    sources = {
        "m204_continuous_video_board_gate.py": ROOT / "scripts/m204_continuous_video_board_gate.py",
        "m204_run_continuous_video.sh": ROOT / "scripts/m204_run_continuous_video.sh",
        "m204_verify_bootstrap.py": ROOT / "scripts/m202_verify_bootstrap.py",
        "video_server.py": SOURCE / "video_server.py", "ps_vision_runtime.py": SOURCE / "ps_vision_runtime.py",
        "BOARD_GATE_RESULT.json": reduced_path,
        "M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json": M202,
    }
    entries = []
    for name, source in sources.items():
        destination = partial / name
        shutil.copyfile(source, destination)
        entries.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    manifest = {
        "date": "2026-09-01", "gate": "M204-bounded-continuous-video-bootstrap", "status": "PASS",
        "build_id": "0x4D395832", "m202_sha256": M202_SHA,
        "source_board_gate_sha256": reduced["source_board_gate_sha256"],
        "files": entries, "file_count": len(entries), "total_bytes": sum(i["bytes"] for i in entries),
        "excluded_patterns": ["__pycache__", "*.pyc", "*.log"],
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01", "gate": "M204-bounded-continuous-video-bootstrap-build", "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(), "package_manifest_sha256": sha256(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries), "total_bytes": manifest["total_bytes"], "board_state_changed": False,
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2)); print("M204_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
