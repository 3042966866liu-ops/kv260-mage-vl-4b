#!/usr/bin/env python3
"""Atomically synchronize the verified M223 KV260 service gate."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
RESULT = ROOT / "deployment/mage_vl4b/M223_REALTIME_SERVICE_BOARD_RESULT_02.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)


def append_once(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        atomic_text(path, text.rstrip() + "\n\n" + section.strip() + "\n")


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    health = result.get("local_health", {})
    if not (
        result.get("status") == "PASS"
        and result.get("gate") == "M223-real-KV260-corrected-realtime-control-plane"
        and result.get("service_pid")
        and health.get("mode") == "continuous-latest-only"
        and health.get("build_id") == "0x4D395832"
        and result.get("stable_rollback_preserved") is True
        and result.get("persistent_boot_dtb_cma_partitions_services_changed") is False
    ):
        raise RuntimeError("M223 service evidence mismatch")

    board = json.loads(BOARD.read_text(encoding="utf-8"))
    entry = {
        "date": "2026-09-01",
        "status": "CONTROL_PLANE_PASS_RUNTIME_READY_PENDING",
        "classification": result["classification"],
        "candidate_build_id": result["candidate_build_id"],
        "package_manifest_sha256": result["package_manifest_sha256"],
        "service_pid": result["service_pid"],
        "local_health": health,
        "worker_event_loop_fix_packaged": True,
        "vectorized_vision_decoder_packaged": True,
        "runtime_load_verified": False,
        "complete_window_executed": False,
        "seconds_level_verified": False,
        "formal_result": "deployment/mage_vl4b/M223_REALTIME_SERVICE_BOARD_RESULT_02.json",
        "formal_result_sha256": sha(RESULT),
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": result["next_gate"],
    }
    board["latest_m223_realtime_service"] = entry
    board["next_gate"] = entry["next_gate"]
    atomic_text(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""
<!-- M223_REALTIME_SERVICE_PASS_START -->
## M223：真实 KV260 实时服务控制面通过（2026-09-01）

- 哈希封闭 M223 服务已通过 COM3 部署，包清单 SHA-256 为
  `{result['package_manifest_sha256']}`，服务 PID `{result['service_pid']}`，Build ID
  `{result['candidate_build_id']}`，调度模式为 `continuous-latest-only`。
- M222 的后台 event-loop 修复和 98 个视觉 W4 Linear 的向量化解码器已随服务部署；
  boot、DTB、CMA、分区和稳定回滚均未改变。
- 该证据等级只覆盖真实板端进程与空闲 HTTP 控制面；运行时尚未加载，未发送帧，未完成
  一个四帧窗口，也未验证 FPGA E2E 或 5 秒窗口目标。首次健康探测的短暂 connection-refused
  被后续同一有界探测成功覆盖，保留在原始结果的 `error` 字段中用于审计。
- 正式结果：`deployment/mage_vl4b/M223_REALTIME_SERVICE_BOARD_RESULT_02.json`
  （SHA-256 `{sha(RESULT)}`）。下一门禁只启动一次会话并要求
  `runtime_load_count=1`、`worker_alive=true`、`service_state=ready`。
<!-- M223_REALTIME_SERVICE_PASS_END -->
"""
    append_once(CURRENT, "<!-- M223_REALTIME_SERVICE_PASS_START -->", section)
    append_once(MILESTONES, "<!-- M223_REALTIME_SERVICE_PASS_START -->", section)
    print("M225_M223_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
