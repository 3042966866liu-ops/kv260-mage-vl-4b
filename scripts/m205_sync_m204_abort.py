#!/usr/bin/env python3
"""Synchronize the user-requested M204 abort without weakening M202."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "deployment/mage_vl4b/M204_CONTINUOUS_VIDEO_BOARD_RESULT_01.json"
UART = ROOT / "tmp/m204_continuous_video/abort_recover.log"
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
REVIEW = ROOT / "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md"
START = "<!-- M204_ABORTED_FOR_OPTIMIZATION_START -->"
END = "<!-- M204_ABORTED_FOR_OPTIMIZATION_END -->"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def replace_or_prepend(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if START in text and END in text:
        before, tail = text.split(START, 1)
        _old, after = tail.split(END, 1)
        text = before + section + after
    else:
        if text.startswith("# "):
            first, rest = text.split("\n", 1)
            text = first + "\n\n" + section + "\n" + rest
        else:
            text = section + "\n" + text
    atomic_text(path, text)


def main() -> int:
    result = json.loads(FORMAL.read_text(encoding="utf-8"))
    if (result.get("gate") != "M204-bounded-continuous-video-two-window-reuse"
            or result.get("status") != "FAIL"
            or not str(result.get("error", "")).startswith("KeyboardInterrupt")):
        raise RuntimeError("M205 requires the formal user-requested M204 abort")
    formal_sha = sha256(FORMAL)
    uart_sha = sha256(UART)
    board = json.loads(BOARD.read_text(encoding="utf-8"))
    if board.get("latest_m202_fixed_video_e2e", {}).get("status") != "PASS":
        raise RuntimeError("M205 exact stable M202 predecessor missing")
    board["status"] = "M204_CONTINUOUS_GATE_ABORTED_FOR_OPTIMIZATION_M202_STABLE"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m204_continuous_video"] = {
        "status": "FAIL",
        "attempt": "01",
        "classification": (
            "User-requested KeyboardInterrupt after 1631.840 s during window 0; "
            "the inherited M198/M202 visual path is too slow. This is not a numerical, "
            "FPGA, boot or hardware failure."
        ),
        "candidate_build_id": result.get("candidate_build_id"),
        "processed_window_count": 0,
        "error": result.get("error"),
        "wall_ms": result.get("wall_ms"),
        "formal_result": "deployment/mage_vl4b/M204_CONTINUOUS_VIDEO_BOARD_RESULT_01.json",
        "formal_result_sha256": formal_sha,
        "uart_log": "tmp/m204_continuous_video/abort_recover.log",
        "uart_log_sha256": uart_sha,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "M206 progress-visible all-FP32-compute/BF16-boundary fixed-four-frame "
            "PS-vision comparison; do not rerun M204 unchanged."
        ),
    }
    atomic_text(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")
    section = f"""{START}
## M204：过慢连续视频门禁按用户要求中止，M202 稳定基线保留（2026-09-01）

- M204 在窗口 0 执行 `1631840.223 ms` 后由用户要求停止；板端捕获
  `KeyboardInterrupt`、原子写出正式 FAIL，并返回普通 `ubuntu@kria:~$` 提示符。
- 该 FAIL 不是数值、FPGA、权重、overlay 或板卡故障，只说明沿用 M198/M202 的视觉路径
  逐窗口执行过慢；没有资格证明连续窗口复用。
- boot、DTB、CMA、分区和服务未改动，M202 固定四帧 PASS 继续作为稳定回滚。
- 下一步改为 M206：先加入 24 层进度和 30 秒心跳，再只测“全层 FP32 计算、层间
  BF16”固定四帧候选；通过速度、精度、RSS、warning 四项比较后才重启连续窗口门禁。
- 正式证据：`deployment/mage_vl4b/M204_CONTINUOUS_VIDEO_BOARD_RESULT_01.json`
  （SHA-256 `{formal_sha}`）；中止/恢复日志 SHA-256 `{uart_sha}`。
{END}"""
    replace_or_prepend(CURRENT, section)
    replace_or_prepend(MILESTONES, section)
    review_section = f"""{START}
## M204 连续门禁过慢时的中止与收束（2026-09-01）

- 错误模式：在已知单窗口约 40 分钟时，直接运行两个窗口，只能验证复用，不能改善性能。
- 本次处理：用户要求改方案后，停止 Windows 控制器，再通过已验证 COM3 Ctrl+C 恢复脚本
  中止板端 Python；板端写出正式 FAIL 后确认普通 shell 提示符，未断电或改启动配置。
- 以后：性能结构未改变时，不用完整双窗口门禁探索速度；先做固定四帧候选比较。长阶段必须
  输出层级进度和 30 秒心跳。只有固定四帧速度、精度和内存同时通过，才进入连续窗口。
- 证据：`deployment/mage_vl4b/M204_CONTINUOUS_VIDEO_BOARD_RESULT_01.json`
  （SHA-256 `{formal_sha}`）。
{END}"""
    replace_or_prepend(REVIEW, review_section)
    print("M205_M204_ABORT_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
