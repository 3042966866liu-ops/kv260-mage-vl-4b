#!/usr/bin/env python3
"""Synchronize the M212 live HTTP/SSE offline contract evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
RESULT = ROOT / "deployment/mage_vl4b/M212_LATEST_ONLY_LIVE_HTTP_SSE_OFFLINE_RESULT.json"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def replace_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError(f"M213 section markers invalid in {path}")
    before, rest = text.split(START, 1)
    _old, after = rest.split(END, 1)
    atomic(path, before + section + after)


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result.get("status") != "PASS" or not all(result.get("checks", {}).values()):
        raise RuntimeError("M212 offline contract is not a complete PASS")
    result_sha = sha(RESULT)
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    m208 = board.get("latest_m208_ps_vision_board_gate", {})
    if m208.get("status") != "PASS" or m208.get("formal_result_sha256") != "2ff1d5823b97e349613abd15199e9db37630314a2d2c9b60fb4964658d47b23a":
        raise RuntimeError("M212 exact M208 predecessor missing")
    board["status"] = "M208_PS_VISION_BOARD_PASS_M212_LIVE_HTTP_SSE_OFFLINE_PASS_BOARD_PENDING"
    board["latest_m212_live_stream_service"] = {
        "date": "2026-09-01",
        "gate": result["gate"],
        "status": "OFFLINE_PASS_BOARD_NOT_EXECUTED",
        "classification": result["classification"],
        "mode": "unbounded browser-camera ingress; capacity-16 ring; newest-four; one inference worker; SSE",
        "accepted_frames": result["snapshot"]["buffer"]["accepted_frames"],
        "overwritten_frames": result["snapshot"]["buffer"]["overwritten_frames"],
        "latest_completed_sequence": result["snapshot"]["last_completed_newest_sequence"],
        "runtime_load_count": result["snapshot"]["runtime_load_count"],
        "http_sse_endpoint_streamed": result["checks"]["http_sse_endpoint_streamed"],
        "real_runtime_selected": "M207 real-KV260 PS vision PASS plus inherited M120 FPGA language/head",
        "board_state_changed": False,
        "web_deployed": False,
        "formal_result": "deployment/mage_vl4b/M212_LATEST_ONLY_LIVE_HTTP_SSE_OFFLINE_RESULT.json",
        "formal_result_sha256": result_sha,
        "next_gate": "Build/hash M212 delta, board preflight, then start the real latest-only service; do not rerun M204.",
    }
    board["next_gate"] = board["latest_m212_live_stream_service"]["next_gate"]
    atomic(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""{START}
## M206--M213：M207 实板入选，M212 真持续流 HTTP/SSE 离线门禁通过（2026-09-01）

- M208 已在真实 KV260 固定四帧上选择 M207 后端：视觉前向 `1006.044` 秒，相对 M198
  提速 `6.62%`；cosine `0.999117311`、RMSE `0.022790040`、BF16 GEMM warning `0`。
  正式结果 SHA-256 `2ff1d5823b97e349613abd15199e9db37630314a2d2c9b60fb4964658d47b23a`。
- M212 已把该后端接入 M209 结构：浏览器摄像头持续输入、16 帧有界环形缓冲、推理忙时继续
  接收、完成后直接跳到最新四帧、最多一个窗口积压、runtime 只加载一次，并通过 HTTP/SSE
  发布 frame/window/layer/heartbeat/token/FPGA-proof 事件。
- 离线 HTTP 压力门禁接收 `64` 帧、覆盖 `48` 帧，最终完成最新序号 `63`；实际 SSE 端点返回
  event/data，全部契约 PASS。正式结果 SHA-256 `{result_sha}`。
- M212 目前仍是 FakeRuntime 离线控制面证据；摄像头权限、KV260 持续推理、公共 HTTPS 外链与
  低延迟均未宣称 PASS。下一步是构建哈希闭合小包、COM3 实板预检并启动真实 latest-only 服务；
  不再重跑旧的有限双窗口 M204。
{END}"""
    replace_section(CURRENT, section)
    replace_section(MILESTONES, section)
    print(f"M213_M212_OFFLINE_STATE_SYNC_PASS sha256={result_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
