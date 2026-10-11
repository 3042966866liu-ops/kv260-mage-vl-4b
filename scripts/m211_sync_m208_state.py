#!/usr/bin/env python3
"""Atomically synchronize the verified M208 real-board result."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
RESULT = ROOT / "deployment/mage_vl4b/M208_M207_PS_VISION_BOARD_RESULT_01.json"
LOG = ROOT / "tmp/m208_ps_vision/run_01.log"
START = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_START -->"
END = "<!-- M206_M209_OPTIMIZATION_STREAM_CORE_END -->"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def section_update(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        raise RuntimeError(f"M211 section markers invalid in {path}")
    before, tail = text.split(START, 1)
    _old, after = tail.split(END, 1)
    atomic(path, before + section + after)


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result.get("gate") != "M208-M207-fixed-four-frame-PS-vision-FP32-W4-GEMM":
        raise RuntimeError("M208 gate identity mismatch")
    if result.get("status") != "PASS" or result.get("test_exit_code") != 0:
        raise RuntimeError("M208 is not a verified PASS")
    raw = result["raw_result"]
    metrics = result["metrics_vs_same_method_CPU_PS_golden"]
    if not raw.get("finite"):
        raise RuntimeError("M208 output is not finite")
    if metrics["cosine_similarity"] < result["thresholds"]["cosine_minimum"]:
        raise RuntimeError("M208 cosine gate failed")
    if metrics["rmse"] > result["thresholds"]["rmse_maximum"]:
        raise RuntimeError("M208 RMSE gate failed")
    if result["bf16_gemm_warning_count"] != 0:
        raise RuntimeError("M208 BF16 GEMM warning gate failed")
    if result["vision_forward_ms"] >= result["thresholds"]["vision_forward_ms_maximum_exclusive"]:
        raise RuntimeError("M208 speed gate failed")

    result_sha = sha(RESULT)
    log_sha = sha(LOG)
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    board["status"] = "M208_PS_VISION_BOARD_PASS_M209_LIVE_INTEGRATION_PENDING"
    board["latest_m207_ps_vision_candidate"]["status"] = "BOARD_PASS_SELECTED_FOR_M209"
    board["latest_m207_ps_vision_candidate"]["next_gate"] = (
        "Integrate this exact M207 runtime into M209 latest-only browser-camera/RTSP plus SSE."
    )
    board["latest_m208_ps_vision_board_gate"] = {
        "date": "2026-09-01",
        "gate": result["gate"],
        "status": "PASS",
        "classification": result["classification"],
        "candidate_build_id": result["candidate_build_id"],
        "compute_policy": result["compute_policy"],
        "metrics": metrics,
        "vision_forward_ms": result["vision_forward_ms"],
        "m198_forward_ms": result["thresholds"]["vision_forward_ms_maximum_exclusive"],
        "speedup_vs_m198_forward": result["speedup_vs_m198_forward"],
        "process_max_rss_kib": result["process_max_rss_kib"],
        "bf16_gemm_warning_count": result["bf16_gemm_warning_count"],
        "fpga_language_executed": False,
        "continuous_stream_executed": False,
        "web_deployed": False,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "formal_result": "deployment/mage_vl4b/M208_M207_PS_VISION_BOARD_RESULT_01.json",
        "formal_result_sha256": result_sha,
        "uart_log": "tmp/m208_ps_vision/run_01.log",
        "uart_log_sha256": log_sha,
        "next_gate": "M209 true latest-only continuous ingress/SSE integrated with the selected M207 backend; do not rerun M204.",
    }
    board["latest_m209_continuous_stream_core"]["next_gate"] = (
        "Connect the selected M207 real-board backend to browser-camera/RTSP ingress and SSE; first run a bounded live smoke, not M204."
    )
    atomic(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    section = f"""{START}
## M206--M211：M207 实板入选，M209 真持续流进入集成（2026-09-01）

- M206 全模块 FP32 与 M207 attempt 01 均因 cosine 低于 `0.999` 被拒绝；门槛未放宽。
- M207 attempt 02 保留 M198 分层精度边界，仅将按原精度舍入后的 W4 Linear 操作数提升到
  FP32 GEMM；离线数值 PASS 后进入 M208 实板门禁。
- M208 已在真实 KV260 固定四帧上 PASS：视觉前向 `{result['vision_forward_ms'] / 1000:.3f}` 秒，
  相对 M198 `{result['thresholds']['vision_forward_ms_maximum_exclusive'] / 1000:.3f}` 秒提速
  `{(result['speedup_vs_m198_forward'] - 1.0) * 100:.2f}%`；cosine
  `{metrics['cosine_similarity']:.9f}`、RMSE `{metrics['rmse']:.9f}`、BF16 GEMM warning `0`，
  峰值 RSS `{result['process_max_rss_kib'] / 1024:.1f}` MiB。正式结果 SHA-256
  `{result_sha}`，UART 日志 SHA-256 `{log_sha}`。
- 该 PASS 只选择了 M209 要使用的真实视觉后端；M208 没有执行 FPGA 语言链、持续摄像头、
  HTTP/SSE 或 Web，不得描述为完整视频流部署。
- M209 调度核心保持 16 帧有界环形缓冲、推理时持续接收、最多一个窗口积压、每轮取最新四帧、
  覆盖过期帧、runtime 只加载一次。下一步直接接浏览器摄像头/RTSP 与 SSE，并先运行有界实时
  smoke；不再重跑旧的有限双窗口 M204。
{END}"""
    section_update(CURRENT, section)
    section_update(MILESTONES, section)
    print(f"M211_M208_STATE_SYNC_PASS result_sha256={result_sha} log_sha256={log_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
