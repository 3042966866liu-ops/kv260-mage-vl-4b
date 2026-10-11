#!/usr/bin/env python3
"""Record the M200 source-only readiness without unlocking board execution."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
RESULT = ROOT / "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json"
MARKER = "M200/M201：视频服务已重绑 M197，仍锁在 M198 板端门禁"


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result.get("status") != "PASS_SOURCE_READY_M198_LOCKED":
        raise RuntimeError("M201 M200 locked source result mismatch")
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    board["latest_m200_video_service_overlay_source"] = {
        **result,
        "formal_result": "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json",
        "formal_result_sha256": "7441a08b31481355e2b849b2bb1bbba43bfcd7c986a34e4fc1d6ad793529412b",
    }
    atomic(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")
    block = """
## M200/M201：视频服务已重绑 M197，仍锁在 M198 板端门禁（2026-09-01）

- 视频服务源码不再硬编码全 BF16 视觉塔；运行时、健康信息、流式阶段和 FPGA proof
  已统一为“0--5 层 BF16、6--23 层 FP32 block、层间 BF16、W4 权重不变”。
- `offline_preflight` 新增精确 M198 板端 PASS 与层列表检查；M198 尚未执行，因此状态为
  `PASS_SOURCE_READY_M198_LOCKED`，没有生成上板包、没有启动服务、没有执行视频语言 FPGA
  E2E 或 Web。
- 源文件语法/AST 与合同审计通过。正式证据：
  `deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json`，SHA-256
  `7441a08b31481355e2b849b2bb1bbba43bfcd7c986a34e4fc1d6ad793529412b`。
"""
    for relative in ("CURRENT_STATE.md", "docsMILESTONES.md"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        if MARKER not in text:
            atomic(path, text.rstrip() + "\n\n" + block.strip() + "\n")
    print("M201_M200_SOURCE_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
