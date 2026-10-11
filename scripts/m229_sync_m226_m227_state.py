#!/usr/bin/env python3
"""Synchronize M227 patch and M226 runtime-ready board evidence."""

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
PATCH = ROOT / "deployment/mage_vl4b/M227_RUNTIME_BASE_PATCH_BOARD_RESULT_01.json"
READY = ROOT / "deployment/mage_vl4b/M226_M223_RUNTIME_READY_BOARD_RESULT_02.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, text: str) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)


def append_once(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker not in text: atomic(path, text.rstrip() + "\n\n" + section.strip() + "\n")


def main() -> int:
    patch = json.loads(PATCH.read_text(encoding="utf-8"))
    ready = json.loads(READY.read_text(encoding="utf-8"))
    final = ready.get("final", {})
    if not (
        patch.get("status") == "PASS" and ready.get("status") == "PASS"
        and final.get("service_state") == "ready" and final.get("worker_alive") is True
        and final.get("runtime_load_count") == 1 and final.get("board_runtime_loaded") is True
        and ready.get("frames_submitted") == 0
    ): raise RuntimeError("M229 predecessor mismatch")
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    entry = {
        "date": "2026-09-01", "status": "RUNTIME_READY_FIXED_WINDOW_PENDING",
        "candidate_build_id": "0x4D395832", "service_pid": patch["service_pid"],
        "patch_manifest_sha256": patch["patch_manifest_sha256"],
        "runtime_load_count": 1, "runtime_load_ms": ready["elapsed_ms"],
        "worker_alive": True, "service_state": "ready", "frames_submitted": 0,
        "patch_result": "deployment/mage_vl4b/M227_RUNTIME_BASE_PATCH_BOARD_RESULT_01.json",
        "patch_result_sha256": sha(PATCH),
        "ready_result": "deployment/mage_vl4b/M226_M223_RUNTIME_READY_BOARD_RESULT_02.json",
        "ready_result_sha256": sha(READY),
        "rejected_attempts": [
            "M226 request attempt used an unsupported source_mode and was rejected before runtime load.",
            "M226 runtime attempt exposed an incompatible old ps_vision_runtime base; M227 packaged the accepted M197/M200 base and passed its import gate.",
        ],
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Submit exactly four deterministic frames and measure one complete HTTP/SSE E2E window against 5000 ms.",
    }
    board["latest_m226_m227_runtime_ready"] = entry
    board["next_gate"] = entry["next_gate"]
    atomic(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    section = f"""
<!-- M226_M227_RUNTIME_READY_START -->
## M226/M227：M223 真实板端运行时 ready（2026-09-01）

- 首次 M226 在加载阶段暴露 `ps_vision_runtime` 基类版本不兼容；M227 以独立、哈希封闭补丁
  加入已通过 M197/M200 的基类，导入门禁和真实 KV260 控制面均通过，服务 PID `{patch['service_pid']}`。
- 修复后无帧门禁在 `{ready['elapsed_ms']:.3f} ms` 达到 `runtime_load_count=1`、
  `worker_alive=true`、`service_state=ready`、`board_runtime_loaded=true`，窗口计数仍为 0。
- 该 PASS 证明后台 event loop、overlay/模型运行时加载和状态可见性，不等于四帧 E2E 或 5 秒目标。
  正式证据：`deployment/mage_vl4b/M226_M223_RUNTIME_READY_BOARD_RESULT_02.json`
  （SHA-256 `{sha(READY)}`）与 `deployment/mage_vl4b/M227_RUNTIME_BASE_PATCH_BOARD_RESULT_01.json`
  （SHA-256 `{sha(PATCH)}`）。
<!-- M226_M227_RUNTIME_READY_END -->
"""
    append_once(CURRENT, "<!-- M226_M227_RUNTIME_READY_START -->", section)
    append_once(MILESTONES, "<!-- M226_M227_RUNTIME_READY_START -->", section)
    print("M229_M226_M227_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__": raise SystemExit(main())
