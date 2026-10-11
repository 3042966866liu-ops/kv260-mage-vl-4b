#!/usr/bin/env python3
"""Synchronize the formal M198 result after the real COM3 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def append_once(path: Path, marker: str, block: str) -> None:
    original = path.read_text(encoding="utf-8")
    if marker not in original:
        atomic_text(path, original.rstrip() + "\n\n" + block.strip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", default="01")
    args = parser.parse_args()
    formal = ROOT / f"deployment/mage_vl4b/M198_M197_PS_VISION_BOARD_RESULT_{args.attempt}.json"
    uart = ROOT / f"tmp/m198_ps_vision/run_{args.attempt}.log"
    result = json.loads(formal.read_text(encoding="utf-8"))
    if result.get("gate") != "M198-M197-fixed-four-frame-PS-vision-FP32-block-numerical":
        raise RuntimeError("M199 M198 gate identity mismatch")
    if result.get("fp32_encoder_layers") != list(range(6, 24)):
        raise RuntimeError("M199 M198 precision policy mismatch")
    passed = result.get("status") == "PASS"
    evidence = {
        "status": result.get("status"),
        "attempt": args.attempt,
        "classification": result.get("classification"),
        "candidate_build_id": result.get("candidate_build_id"),
        "compute_policy": result.get("compute_policy"),
        "fp32_encoder_layers": result.get("fp32_encoder_layers"),
        "metrics": result.get("metrics_vs_same_method_CPU_PS_golden"),
        "vision_wall_ms": result.get("vision_wall_ms"),
        "speedup_vs_m192": result.get("speedup_vs_m192"),
        "error": result.get("error"),
        "formal_result": formal.relative_to(ROOT).as_posix(),
        "formal_result_sha256": sha256(formal),
        "uart_log": uart.relative_to(ROOT).as_posix(),
        "uart_log_sha256": sha256(uart),
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": result.get("next_gate"),
    }
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    board["latest_m198_ps_vision_optimization"] = evidence
    board["status"] = (
        "M198_M197_PS_VISION_OPTIMIZED_PASS_VIDEO_E2E_PENDING"
        if passed else "M198_M197_PS_VISION_OPTIMIZATION_FAIL"
    )
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["performance_gate_passed"] = False
    atomic_text(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    marker = f"M198/M199：分层 FP32 视觉板端门禁 attempt {args.attempt}"
    metrics = result.get("metrics_vs_same_method_CPU_PS_golden") or {}
    block = f"""
## {marker}（2026-09-01）

- 状态：`{result.get('status')}`；策略固定为视觉 encoder 0--5 层 BF16、6--23 层
  FP32，并在每个 FP32 block 边界回写 BF16；W4/FP16-scale 权重和逐 Linear 解码不变。
- cosine=`{metrics.get('cosine_similarity')}`，RMSE=`{metrics.get('rmse')}`，视觉前向
  `{result.get('vision_wall_ms')} ms`，相对 M192 原 BF16 路径加速比
  `{result.get('speedup_vs_m192')}`。
- 该证据仍只覆盖固定四帧 PS 视觉；`fpga_language_executed=false`，不是完整视频语言
  FPGA E2E、任意视频或 Web。boot、DTB、CMA、分区、服务和稳定回滚未改动。
- 正式结果：`{formal.relative_to(ROOT).as_posix()}`，SHA-256
  `{sha256(formal)}`；UART SHA-256 `{sha256(uart)}`。
- 下一步：{result.get('next_gate')}
"""
    append_once(CURRENT, marker, block)
    append_once(MILESTONES, marker, block)
    print("M199_M198_AUTHORITATIVE_STATE_SYNC_PASS" if passed else "M199_M198_AUTHORITATIVE_STATE_SYNC_FAIL_RECORDED")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
