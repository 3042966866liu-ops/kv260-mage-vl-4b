#!/usr/bin/env python3
"""Synchronize authoritative state after the real M192 KV260 PS-vision gate."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment" / "mage_vl4b" / "BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
REVIEW = ROOT / "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md"
MARKER = "M188--M194：ARM64 视觉运行时与 M192 板端门禁"


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def append_once(path: Path, marker: str, block: str) -> None:
    original = path.read_text(encoding="utf-8")
    if marker not in original:
        atomic_text(path, original.rstrip() + "\n\n" + block.strip() + "\n")


def main() -> int:
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    board["status"] = "M192_M181_FIXED_FOUR_FRAME_PS_VISION_PASS_VIDEO_E2E_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["performance_gate_passed"] = False
    board["latest_m193_arm64_runtime"] = {
        "status": "PASS",
        "classification": "Isolated ARM64 Python runtime and exact Mage-VL import/BF16 smoke only; not PS-vision or video E2E evidence.",
        "runtime": "/home/ubuntu/tellme_m120_m89x2_20260901/m190_mage_runtime",
        "torch": "2.12.1+cpu",
        "transformers": "5.7.0",
        "numpy": "1.26.4",
        "pillow": "12.1.0",
        "pynq": "3.0.1",
        "a53_native_bf16": False,
        "formal_result": "deployment/mage_vl4b/M193_PILLOW_RUNTIME_REPAIR_RESULT_01.json",
        "formal_result_sha256": "80cee9d8a23f84424c3d69c6ceb354d7e5e8ba07e9078970227ca5609eee3906",
        "stable_rollback_preserved": True,
    }
    board["latest_m192_ps_vision"] = {
        "status": "PASS",
        "attempt": "02",
        "classification": "Real KV260 fixed-four-frame PS vision numerical PASS only; FPGA language/video E2E, arbitrary video, performance acceptance and Web remain unproved.",
        "candidate_build_id": "0x4D395832",
        "cosine_similarity": 0.999029355073355,
        "rmse": 0.023895628590924547,
        "max_abs_error": 0.67578125,
        "vision_wall_ms": 1836084.0372140082,
        "vision_wall_minutes": 30.60140062023347,
        "fpga_language_executed": False,
        "formal_result": "deployment/mage_vl4b/M192_M181_PS_VISION_BOARD_RESULT_02.json",
        "formal_result_sha256": "bc506174b9148d565b2f258b99417845347355f4572d0245db8e32d1d24401bf",
        "uart_log": "tmp/m192_ps_vision/run_02.log",
        "uart_log_sha256": "27d1e950cd08c677ded5ad311e0c67e905d31fa56623d128760ddb0dc02aeee5",
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Run the hash-locked M197 FP32-block/BF16-boundary PS-vision candidate; only a numerical PASS may advance to fixed video-language FPGA E2E.",
    }
    atomic_text(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    state_block = """
## M188--M194：ARM64 视觉运行时与 M192 板端门禁（2026-09-01）

- 已在独立目录安装 ARM64 `torch 2.12.1+cpu`、Transformers 5.7.0、NumPy 1.26.4、
  Pillow 12.1.0 等固定依赖；Mage-VL 源码导入与小型 BF16 Linear smoke PASS。没有修改
  boot、DTB、CMA、分区、服务或稳定回滚。
- M190 首次运行时因遗漏 Pillow 依赖闭包而 FAIL；M193 只修复该依赖并通过完整导入 smoke。
- M192 attempt 01 因混用板端原始 JSON 与 Windows 换行规范化后的哈希而在计算前 FAIL；
  attempt 02 改为随引导包传输并校验完全相同的前置证据字节。
- M192 attempt 02 在真实 KV260 Cortex-A53 上完成固定四帧视觉塔：cosine
  `0.999029355073355`、RMSE `0.023895628590924547`，严格门槛 PASS；但视觉前向耗时
  `1,836,084.037 ms`（约 `30.60 min`）。日志同时证明 A53 无原生 BF16，PyTorch
  BF16 matmul 回退到 BLAS，这是视频路径的首要性能瓶颈。
- 该 PASS 只到 PS 视觉数值层，不是视频语言 FPGA E2E、任意视频、性能验收或 Web。
  文字 4B 既有固定文本 L5 PASS 未被本轮独立运行时安装改变。
- 正式证据：`deployment/mage_vl4b/M192_M181_PS_VISION_BOARD_RESULT_02.json`
  （SHA-256 `bc506174...401bf`）；UART 日志 SHA-256 `27d1e950...aeee5`。
- 下一步：只上板 M197“0--5 层 BF16、6--23 层 FP32、层间回写 BF16”候选；其离线
  固定四帧结果 cosine=`0.9996929471208194`、RMSE=`0.013442605435745035`。板端数值
  PASS 后才能进入固定视频语言 FPGA E2E。
"""
    append_once(CURRENT, MARKER, state_block)
    append_once(MILESTONES, MARKER, state_block)

    review_block = """
## M188--M192 操作错误复盘（2026-09-01）

1. M188 初次结果路径落在 root 所有目录，普通用户无法原子写回。以后引导阶段先创建并
   验证用户可写结果目录，正式 runner 再以 root 运行。
2. M186 在选择 Python 解释器时就退出，未进入正式结果 envelope。以后环境依赖失败也必须
   由外层固定 runner 原子写入 PASS/FAIL 结果。
3. M190 只按基础包依赖收集 wheel，漏掉 Mage-VL/Transformers 视觉导入实际需要的 Pillow。
   以后“运行时完整”必须以 exact model-source import 加最小算术 smoke 为闭包门禁。
4. M192 attempt 01 比较了板端原始 JSON 与被 Windows 换行规范化后的同内容文件哈希。
   以后前置证据必须随引导包传输 exact bytes 并在板端重哈希，不能混用跨平台重写副本。
5. PowerShell 失败分支曾写成 `throw"..."`，语法解析未报错但运行时把它当命令名。
   以后控制器除 parser check 外，还要执行一次故意失败分支的单元 smoke。
"""
    append_once(REVIEW, "M188--M192 操作错误复盘", review_block)
    print("M194_M192_AUTHORITATIVE_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
