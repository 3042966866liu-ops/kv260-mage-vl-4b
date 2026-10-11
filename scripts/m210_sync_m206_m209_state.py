#!/usr/bin/env python3
"""Synchronize M206/M207 offline selection and M209 stream-core evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
M206 = ROOT / "deployment/mage_vl4b/M206_OFFLINE_ALL_FP32_BF16_BOUNDARY_RESULT.json"
M207R1 = ROOT / "deployment/mage_vl4b/M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT01_REJECTED.json"
M207R2 = ROOT / "deployment/mage_vl4b/M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT02.json"
M209 = ROOT / "deployment/mage_vl4b/M209_CONTINUOUS_LATEST_ONLY_CORE_RESULT.json"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"


def sha(path: Path) -> str:
    digest = hashlib.sha256(); digest.update(path.read_bytes()); return digest.hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def section_update(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if START in text and END in text:
        before, tail = text.split(START, 1); _old, after = tail.split(END, 1)
        text = before + section + after
    elif text.startswith("# "):
        first, rest = text.split("\n", 1); text = first + "\n\n" + section + "\n" + rest
    else:
        text = section + "\n" + text
    atomic(path, text)


def main() -> int:
    m206 = json.loads(M206.read_text())
    m207r1 = json.loads(M207R1.read_text())
    m207r2 = json.loads(M207R2.read_text())
    m209 = json.loads(M209.read_text())
    if m206.get("status") != "FAIL" or m207r1.get("status") != "FAIL":
        raise RuntimeError("M210 rejected candidate identities missing")
    if (m207r2.get("status") != "PASS" or m207r2.get("bf16_gemm_warning_count") != 0
            or m209.get("status") != "PASS"):
        raise RuntimeError("M210 accepted offline identities missing")
    hashes = {name: sha(path) for name, path in {
        "m206": M206, "m207_attempt01": M207R1,
        "m207_attempt02": M207R2, "m209": M209,
    }.items()}
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    board["status"] = "M207_OFFLINE_PASS_M208_BOARD_SUDO_REQUIRED_M209_STREAM_CORE_OFFLINE_PASS"
    board["latest_m207_ps_vision_candidate"] = {
        "status": "OFFLINE_PASS_BOARD_NOT_EXECUTED",
        "policy": "M198 topology; all W4 Linear GEMMs FP32; BF16-block operands rounded to BF16 before FP32 GEMM",
        "cosine_similarity": m207r2["metrics_vs_M56_W4_BF16_golden"]["cosine_similarity"],
        "rmse": m207r2["metrics_vs_M56_W4_BF16_golden"]["rmse"],
        "bf16_gemm_warning_count": 0,
        "formal_result": "deployment/mage_vl4b/M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT02.json",
        "formal_result_sha256": hashes["m207_attempt02"],
        "next_gate": "Refresh terminal-scoped sudo and run M208 fixed-four-frame real-KV260 comparison.",
    }
    board["latest_m209_continuous_stream_core"] = {
        "status": "OFFLINE_PASS_BOARD_NOT_EXECUTED",
        "mode": "unbounded input; capacity-16 ring; newest-four selection; one-window backlog; stale frames overwritten",
        "accepted_frames": 64,
        "overwritten_frames": 48,
        "last_window_sequences": [60, 61, 62, 63],
        "runtime_load_count": 1,
        "formal_result": "deployment/mage_vl4b/M209_CONTINUOUS_LATEST_ONLY_CORE_RESULT.json",
        "formal_result_sha256": hashes["m209"],
        "classification": m209["classification"],
        "next_gate": "Integrate with browser-camera/RTSP ingress and SSE only after M208 board selection.",
    }
    atomic(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")
    section = f"""{START}
## M206--M210：A53 FP32 Linear 候选与真正连续流核心（2026-09-01）

- M206“全模块 FP32、层间 BF16”被严格拒绝：cosine `0.998708926` 低于 `0.999`；
  M207 attempt 01 直接使用完整 FP32 解码权重同样被拒绝（cosine `0.998683638`）。
- M207 attempt 02 保留 M198 分层精度，只把按原精度舍入后的 W4 Linear 输入/权重提升到
  FP32 做 GEMM。离线固定四帧 cosine `0.999256548`、RMSE `0.020916586`、有限，
  BF16 GEMM warning `0`，门槛未放宽。正式 SHA-256 `{hashes['m207_attempt02']}`。
- M208 54,918-byte/9-file 上板包已通过 Python、PowerShell、bash 与哈希闭包；同终端
  `sudo -n true` 因时间戳过期停止在上传前，板端未改变。
- M209 已实现真正持续源所需调度核心：16 帧固定环形缓冲、推理时继续采集、最多一个待处理
  窗口、完成后跳到最新四帧、覆盖旧帧、runtime 只加载一次。64 帧压力测试接收全部输入，
  覆盖 48 帧，只做 4 次推理并最终处理 `[60,61,62,63]`；这仍是离线调度证据，不是摄像头、
  KV260、HTTP/SSE 或低延迟 PASS。正式 SHA-256 `{hashes['m209']}`。
- 下一步：刷新 terminal-scoped sudo 后只跑 M208；其速度/精度/RSS通过，才把 M209 接到
  浏览器摄像头或 RTSP 输入以及 SSE 状态/结果流。
{END}"""
    section_update(CURRENT, section)
    section_update(MILESTONES, section)
    print("M210_M206_M209_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
