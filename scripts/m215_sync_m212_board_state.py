#!/usr/bin/env python3
"""Atomically synchronize M212 real-board control-plane evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
BOARD_RESULT = ROOT / "deployment/mage_vl4b/M212_LIVE_SERVICE_BOARD_RESULT_01.json"
HTTP_RESULT = ROOT / "deployment/mage_vl4b/M214_M212_WINDOWS_HTTP_RESULT.json"
UART_LOG = ROOT / "tmp/m212_live_service/run_01.log"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"
EXPECTED_PACKAGE = "b21349e0eddac4b46ea8fe8f61a3e7f4ddbf77f406e14cb53d3ded1c39d582fc"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def replace_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError(f"M215 section markers invalid in {path}")
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    atomic(path, before + section + after)


def main() -> int:
    board_result = json.loads(BOARD_RESULT.read_text(encoding="utf-8-sig"))
    http_result = json.loads(HTTP_RESULT.read_text(encoding="utf-8-sig"))
    if board_result.get("status") != "PASS":
        raise RuntimeError("M212 board control-plane is not PASS")
    if board_result.get("package_manifest_sha256") != EXPECTED_PACKAGE:
        raise RuntimeError("M212 board package identity mismatch")
    if http_result.get("status") != "PASS" or not all(http_result.get("checks", {}).values()):
        raise RuntimeError("M214 Windows HTTP gate is not a complete PASS")
    if http_result.get("health", {}).get("build_id") != "0x4D395832":
        raise RuntimeError("M214 build identity mismatch")

    board_sha = sha(BOARD_RESULT)
    http_sha = sha(HTTP_RESULT)
    log_sha = sha(UART_LOG)
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    board["status"] = "M212_REAL_BOARD_HTTP_CONTROL_PLANE_PASS_LIVE_CAMERA_AND_PUBLIC_HTTPS_PENDING"
    board["latest_m212_live_stream_service"] = {
        "date": "2026-09-01",
        "gate": board_result["gate"],
        "status": "BOARD_HTTP_CONTROL_PLANE_PASS_LIVE_INFERENCE_NOT_EXECUTED",
        "classification": board_result["classification"],
        "candidate_build_id": board_result["candidate_build_id"],
        "package_manifest_sha256": board_result["package_manifest_sha256"],
        "service_pid": board_result["service_pid"],
        "local_health": board_result["local_health"],
        "windows_http_checks": http_result["checks"],
        "board_url": http_result["board_url"],
        "temporary_runtime_state_changed": True,
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "continuous_stream_inference_executed": False,
        "web_deployed": False,
        "public_https_status": "AWAITING_EXPLICIT_CAMERA_AND_SERVICE_EXPOSURE_AUTHORIZATION",
        "stable_rollback_preserved": True,
        "transient_startup_note": board_result.get("error"),
        "formal_result": "deployment/mage_vl4b/M212_LIVE_SERVICE_BOARD_RESULT_01.json",
        "formal_result_sha256": board_sha,
        "windows_http_result": "deployment/mage_vl4b/M214_M212_WINDOWS_HTTP_RESULT.json",
        "windows_http_result_sha256": http_sha,
        "uart_log": "tmp/m212_live_service/run_01.log",
        "uart_log_sha256": log_sha,
        "next_gate": "With explicit public exposure authorization, start the independent HTTPS tunnel, then submit a real continuous camera stream and retain the first complete FPGA-backed window.",
    }
    board["next_gate"] = board["latest_m212_live_stream_service"]["next_gate"]
    atomic(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""{START}
## M212--M215：真实 KV260 视频流服务控制面与 Windows HTTP 已通过（2026-09-01）

- M212 delta manifest SHA-256 为 `{EXPECTED_PACKAGE}`；板端逐文件闭包、root/XRT/PYNQ
  环境、M208/M209 前序证据和服务健康门禁均 PASS。临时服务 PID `{board_result['service_pid']}`，
  Build ID `0x4D395832`，模式 `continuous-latest-only`，无限输入合同为 true。
- Windows 已直接访问 `{http_result['board_url']}`：页面 HTTP 200、摄像头 UI 存在、health/status
  API 一致。板端正式结果 SHA-256 `{board_sha}`，UART SHA-256 `{log_sha}`，Windows HTTP
  结果 SHA-256 `{http_sha}`。
- 本阶段只证明真实板端服务进程与局域网 HTTP 控制面；尚未提交摄像头帧，runtime 尚未加载，
  未执行持续视觉/FPGA 语言推理，未证明首个窗口、吞吐、延迟或公网 Web。
- 一次操作链失败被 fail-closed 保留：旧单行 base64 uploader 在 23,451-byte
  `video_server.py` 上超过串口行长，shell 落入 `>`；manifest 又排在载荷之后，导致门禁先报缺失。
  已用 Ctrl+C 恢复并改成 manifest-first、每块 1,800 bytes、逐块确认、整文件 SHA-256 与原子替换；
  之后完整包哈希和 `bash -n` 均 PASS。不得再次对大 UART 文件使用单行 base64。
- 临时进程和临时网口地址属于易失运行态；boot、DTB、CMA、分区、持久服务与稳定回滚未改变。
  下一门禁需要用户明确授权将摄像头与服务暴露到 Cloudflare 公网 HTTPS；授权后再执行真实持续
  摄像头首窗口并保存 FPGA-backed complete 事件。
{END}"""
    replace_section(CURRENT, section)
    replace_section(MILESTONES, section)
    print(f"M215_M212_BOARD_STATE_SYNC_PASS board_sha256={board_sha} http_sha256={http_sha} log_sha256={log_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
