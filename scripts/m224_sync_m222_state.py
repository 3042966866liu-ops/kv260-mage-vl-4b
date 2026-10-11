#!/usr/bin/env python3
"""Atomically synchronize the verified M222 ARM64 decoder result."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
ARM = ROOT / "deployment/mage_vl4b/M222_ARM64_DECODER_BOARD_RESULT_02.json"
OFFLINE = ROOT / "deployment/mage_vl4b/M222_PS_VISION_OFFLINE_RESULT.json"
WORKER = ROOT / "deployment/mage_vl4b/M222_LIVE_WORKER_EVENT_LOOP_OFFLINE_RESULT.json"
DELTA = ROOT / "deployment/mage_vl4b/M223_REALTIME_BOARD_DELTA_RESULT.json"
UART = ROOT / "tmp/m222_decoder/run_02.log"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def append_once(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        atomic_text(path, text.rstrip() + "\n\n" + section.strip() + "\n")


def main() -> int:
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    offline = json.loads(OFFLINE.read_text(encoding="utf-8"))
    worker = json.loads(WORKER.read_text(encoding="utf-8"))
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    if not (
        arm.get("status") == "PASS"
        and arm.get("bit_exact") is True
        and arm.get("module_count") == 98
        and arm.get("total_elements") == 329252864
        and float(arm.get("arm64_decode_speedup", 0.0)) > 1.0
        and offline.get("status") == "PASS"
        and worker.get("status") == "PASS"
        and delta.get("status") == "PASS"
        and "M222_ARM64_DECODER_RUNNER_PASS" in UART.read_text(encoding="utf-8", errors="replace")
    ):
        raise RuntimeError("M224 predecessor closure mismatch")
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    board["latest_m222_visual_w4_decoder"] = {
        "date": "2026-09-01",
        "status": "ARM64_DECODER_PASS_M223_SERVICE_READY_SUDO_PENDING",
        "classification": (
            "Real-KV260 ARM64 bit-exact/timing gate for all 98 visual W4 decoder "
            "modules; not full vision, complete-window FPGA E2E or seconds-level evidence."
        ),
        "candidate_build_id": "0x4D395832",
        "module_count": arm["module_count"],
        "total_elements": arm["total_elements"],
        "bit_exact": True,
        "legacy_decode_ms": arm["legacy_decode_ms"],
        "vectorized_decode_ms": arm["vectorized_decode_ms"],
        "arm64_decode_speedup": arm["arm64_decode_speedup"],
        "model_math_changed": False,
        "quantization_changed": False,
        "formal_result": "deployment/mage_vl4b/M222_ARM64_DECODER_BOARD_RESULT_02.json",
        "formal_result_sha256": sha(ARM),
        "uart_log": "tmp/m222_decoder/run_02.log",
        "uart_log_sha256": sha(UART),
        "offline_fixed_four_frame_result": "deployment/mage_vl4b/M222_PS_VISION_OFFLINE_RESULT.json",
        "offline_fixed_four_frame_result_sha256": sha(OFFLINE),
        "worker_regression_result": "deployment/mage_vl4b/M222_LIVE_WORKER_EVENT_LOOP_OFFLINE_RESULT.json",
        "worker_regression_result_sha256": sha(WORKER),
        "m223_delta_result": "deployment/mage_vl4b/M223_REALTIME_BOARD_DELTA_RESULT.json",
        "m223_delta_result_sha256": sha(DELTA),
        "m223_package_manifest_sha256": delta["package_manifest_sha256"],
        "m223_uploaded": False,
        "m223_service_deployed": False,
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "rejected_attempts": [
            "M222 attempt 01 completed computation but could not write into the root-owned results directory; no persistent board state changed.",
            "M223 deploy attempt 01 stopped at sudo -n before upload because the terminal-scoped sudo timestamp had expired."
        ],
        "next_gate": (
            "Refresh sudo in PuTTY and close it; then deploy M223 over COM3 with "
            "automatic M218 rollback, require worker ready, and run fixed-four-frame timing."
        ),
    }
    board["next_gate"] = board["latest_m222_visual_w4_decoder"]["next_gate"]
    atomic_text(BOARD, json.dumps(board, ensure_ascii=False, indent=2) + "\n")

    section = f"""
<!-- M222_ARM64_DECODER_PASS_START -->
## M222：视觉 W4 向量化解码 ARM64 门禁通过（2026-09-01）

- 真实 KV260/AArch64 对全部 98 个视觉 Linear、`329252864` 个恢复后 FP32 元素逐项比较，
  新旧解码结果位精确一致；模型数学、W4 量化、FP16 scale、M198/M207 精度边界均未改变。
- 旧 Python lane 解码耗时 `{arm['legacy_decode_ms']:.3f} ms`，NumPy 记录级向量化解码
  `{arm['vectorized_decode_ms']:.3f} ms`，解码阶段真实板端加速 `{arm['arm64_decode_speedup']:.3f}x`。
- 该 PASS 只证明解码器，不是固定四帧完整视觉、语言 FPGA E2E、连续视频或 5 秒窗口 PASS。
  M208 的视觉 GEMM 和 M202 的语言 Prefill 仍是下一阶段主要瓶颈。
- M218 会话未进入窗口的根因已定位为后台 `m209-live-inference` 线程缺少 asyncio event loop；
  M222 回归门禁已证明显式 event loop 与 `worker-failed` 状态可见。M223 哈希封闭服务候选已构建，
  但首次部署在上传前因 `sudo -n` 过期安全停止，当前仍运行旧 M218 临时服务。
- attempt 01 的板端计算只因 root 所有结果目录不可写而未落盘；attempt 02 改写到候选可写目录后通过。
  boot、DTB、CMA、分区和稳定回滚均未改变。
- 正式结果：`deployment/mage_vl4b/M222_ARM64_DECODER_BOARD_RESULT_02.json`
  （SHA-256 `{sha(ARM)}`）；UART：`tmp/m222_decoder/run_02.log`
  （SHA-256 `{sha(UART)}`）。下一步只部署 M223，再做固定四帧完整板端计时。
<!-- M222_ARM64_DECODER_PASS_END -->
"""
    append_once(CURRENT, "<!-- M222_ARM64_DECODER_PASS_START -->", section)
    append_once(MILESTONES, "<!-- M222_ARM64_DECODER_PASS_START -->", section)
    print("M224_M222_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

