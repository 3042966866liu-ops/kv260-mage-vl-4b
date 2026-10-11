#!/usr/bin/env python3
"""Build clean M223 service delta after M222 ARM64 decoder PASS."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m223_realtime/m223_realtime_delta"
RESULT = ROOT / "deployment/mage_vl4b/M223_REALTIME_BOARD_DELTA_RESULT.json"
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
ARM = ROOT / "deployment/mage_vl4b/M222_ARM64_DECODER_BOARD_RESULT_02.json"
OFFLINE = ROOT / "deployment/mage_vl4b/M222_PS_VISION_OFFLINE_RESULT.json"
WORKER = ROOT / "deployment/mage_vl4b/M222_LIVE_WORKER_EVENT_LOOP_OFFLINE_RESULT.json"
TARGET = ROOT / "deployment/mage_vl4b/M222_SECONDS_LEVEL_TARGET.md"
SOURCE = ROOT / "deployment/mage_vl4b/m222_realtime_vision_source"
M218 = ROOT / "deployment/mage_vl4b/m218_file_replay_source"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    board = load(BOARD)
    arm = load(ARM)
    offline = load(OFFLINE)
    worker = load(WORKER)
    if not (
        arm.get("gate") == "M222-ARM64-vectorized-visual-W4-decoder"
        and arm.get("status") == "PASS"
        and arm.get("bit_exact") is True
        and float(arm.get("arm64_decode_speedup", 0.0)) > 1.0
    ):
        raise RuntimeError("M223 requires M222 ARM64 bit-exact speed PASS")
    offline_metrics = offline.get("metrics_vs_M56_W4_BF16_golden", {})
    if not (
        offline.get("status") == "PASS"
        and float(offline_metrics.get("cosine_similarity", 0.0)) >= 0.999
        and float(offline_metrics.get("rmse", 1.0)) <= 0.05
    ):
        raise RuntimeError("M223 M222 fixed-four-frame offline predecessor mismatch")
    if worker.get("status") != "PASS" or not all(worker.get("checks", {}).values()):
        raise RuntimeError("M223 event-loop regression predecessor mismatch")
    live = board.get("latest_m218_dual_source_service", {})
    if not (
        str(live.get("status", "")).startswith("PUBLIC_HTTPS_CONTROL_PLANE_PASS")
        and board.get("stable_rollback_preserved") is True
    ):
        raise RuntimeError("M223 stable M218 predecessor mismatch")

    summary = {
        "date": "2026-09-01",
        # Keep this identity for the accepted M218 offline_preflight parser.
        "gate": "M218-dual-source-predecessor-summary",
        "status": "PASS",
        "source_board_gate_sha256": sha(BOARD),
        "stable_rollback_preserved": True,
        "m179": board["latest_m120_fixed_text_board_gate"],
        "m198": board["latest_m198_ps_vision_optimization"],
        "m208": board["latest_m208_ps_vision_board_gate"],
        "m209": board["latest_m209_continuous_stream_core"],
        "m212": {
            "status": live["status"],
            "package_manifest_sha256": live["package_manifest_sha256"],
            "formal_result_sha256": live["board_result_sha256"],
            "public_https_result_sha256": live["http_result_sha256"],
        },
        "m222_arm64_decoder_result_sha256": sha(ARM),
        "m222_offline_vision_result_sha256": sha(OFFLINE),
        "m222_worker_result_sha256": sha(WORKER),
    }
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists():
        shutil.rmtree(OUT)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    (partial / "M223_PREDECESSOR_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sources = {
        "m222_video_server.py": SOURCE / "m222_video_server.py",
        "m222_live_stream_core.py": SOURCE / "m222_live_stream_core.py",
        "m222_vectorized_w4_runtime.py": SOURCE / "m222_vectorized_w4_runtime.py",
        "video_server.py": M218 / "video_server.py",
        "live_stream_core.py": M218 / "live_stream_core.py",
        "m206_ps_vision_runtime.py": M218 / "m206_ps_vision_runtime.py",
        "m207_ps_vision_runtime.py": M218 / "m207_ps_vision_runtime.py",
        "static/index.html": M218 / "static/index.html",
        "static/style.css": M218 / "static/style.css",
        "static/app.js": SOURCE / "static/app.js",
        "m223_verify_board_delta.py": ROOT / "scripts/m223_verify_board_delta.py",
        "m223_health_probe.py": ROOT / "scripts/m223_health_probe.py",
        "m223_board_preflight_and_restart.sh": ROOT / "scripts/m223_board_preflight_and_restart.sh",
        "M222_ARM64_DECODER_BOARD_RESULT_02.json": ARM,
        "M222_PS_VISION_OFFLINE_RESULT.json": OFFLINE,
        "M222_LIVE_WORKER_EVENT_LOOP_OFFLINE_RESULT.json": WORKER,
        "M222_SECONDS_LEVEL_TARGET.md": TARGET,
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
        raise RuntimeError("M223 forbidden package member")
    manifest = {
        "date": "2026-09-01",
        "gate": "M223-realtime-service-board-delta",
        "status": "PASS",
        "build_id": "0x4D395832",
        "kernel": "mage_m120_m89x2_0",
        "input_modes": ["browser-camera", "uploaded-file-loop"],
        "arm64_decoder_result_sha256": sha(ARM),
        "offline_vision_result_sha256": sha(OFFLINE),
        "worker_regression_result_sha256": sha(WORKER),
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "excluded_patterns": ["__pycache__", "*.pyc", "*.log", "*.partial"],
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01",
        "gate": "M223-realtime-service-board-delta-build",
        "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "COM3 sudo preflight, manifest-first upload, exact verification, "
            "then transient M218-to-M223 restart with automatic M218 rollback."
        ),
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("M223_BOARD_DELTA_BUILD_PASS")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
