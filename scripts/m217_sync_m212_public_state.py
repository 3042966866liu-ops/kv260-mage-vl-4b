#!/usr/bin/env python3
"""Synchronize the M212 public HTTPS control-plane result."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
RESULT = ROOT / "deployment/mage_vl4b/M216_M212_PUBLIC_HTTPS_RESULT.json"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def update_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError(f"M217 section markers invalid in {path}")
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    atomic(path, before + section + after)


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8-sig"))
    if result.get("status") != "PASS" or not all(result.get("checks", {}).values()):
        raise RuntimeError("M216 public HTTPS result is not a complete PASS")
    result_sha = sha(RESULT)
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    live = board.get("latest_m212_live_stream_service", {})
    if live.get("status") != "BOARD_HTTP_CONTROL_PLANE_PASS_LIVE_INFERENCE_NOT_EXECUTED":
        raise RuntimeError("M212 board HTTP predecessor is missing")
    live.update({
        "status": "PUBLIC_HTTPS_CONTROL_PLANE_PASS_LIVE_CAMERA_INFERENCE_PENDING",
        "public_url": result["public_url"],
        "cloudflared_pid": result["cloudflared_pid"],
        "public_https_checks": result["checks"],
        "web_control_plane_deployed": True,
        "web_deployed": False,
        "browser_camera_permission_verified": False,
        "continuous_stream_inference_executed": False,
        "public_https_result": "deployment/mage_vl4b/M216_M212_PUBLIC_HTTPS_RESULT.json",
        "public_https_result_sha256": result_sha,
        "next_gate": result["next_gate"],
    })
    board["latest_m212_live_stream_service"] = live
    board["status"] = "M212_PUBLIC_HTTPS_CONTROL_PLANE_PASS_LIVE_CAMERA_INFERENCE_PENDING"
    board["next_gate"] = result["next_gate"]
    atomic(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""{START}
## M212--M217：真实 KV260 latest-only 服务与公网 HTTPS 控制面通过（2026-09-01）

- M212 delta manifest `b21349e0eddac4b46ea8fe8f61a3e7f4ddbf77f406e14cb53d3ded1c39d582fc`
  已在真实板端通过完整哈希、root/XRT/PYNQ、M208/M209 前序证据与服务健康门禁；服务 PID
  `94573`，Build ID `0x4D395832`，模式 `continuous-latest-only`。
- Windows 局域网页面/API PASS；随后在用户明确授权公开摄像头/服务数据后，Cloudflare 临时
  HTTPS 控制面也 PASS：`{result['public_url']}`，tunnel PID `{result['cloudflared_pid']}`。
  公网主页和 app.js 均为 HTTP 200，`getUserMedia`、`EventSource`、Build ID、kernel、latest-only
  与 unlimited-source 合同全部通过。正式公网结果 SHA-256 `{result_sha}`。
- 边界保持严格：尚未由浏览器授权摄像头、未发送真实帧、板端 runtime 尚未加载、未完成首个
  continuous window，也没有新的 FPGA 调用、吞吐或延迟证据。因此这里是“公网 Web 控制面
  已部署”，不是“真实视频流推理已完成”。下一步必须由摄像头浏览器打开链接、允许权限并启动，
  再保留首个 FPGA-backed complete 事件。
- 本轮再次发现旧单行 UART base64 uploader 违反已有 M202 规则；已改为 manifest-first、
  1,800-byte 分块、逐块完成标志、整文件 SHA-256 和原子替换，并写入操作复盘。boot、DTB、
  CMA、分区、持久服务与稳定回滚未改动。
{END}"""
    update_section(CURRENT, section)
    update_section(MILESTONES, section)
    print(f"M217_M212_PUBLIC_STATE_SYNC_PASS sha256={result_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
