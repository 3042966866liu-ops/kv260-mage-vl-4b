#!/usr/bin/env python3
"""Synchronize the authoritative M202 fixed-video board PASS and rejected upload attempt."""

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
FORMAL = ROOT / "deployment/mage_vl4b/M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json"
UART = ROOT / "tmp/m202_video_e2e/run_01.log"
M200 = ROOT / "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
REVIEW = ROOT / "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def replace_marker(path: Path, start: str, end: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    block = f"{start}\n{body.strip()}\n{end}"
    if start in text and end in text:
        before, tail = text.split(start, 1)
        _, after = tail.split(end, 1)
        text = before.rstrip() + "\n\n" + block + after
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    atomic(path, text)


def main() -> int:
    value = json.loads(FORMAL.read_text(encoding="utf-8"))
    proof = value.get("fpga_proof", {})
    if (value.get("status") != "PASS" or value.get("prompt_tokens") != 849 or
            value.get("generated_token_id") != 32 or
            str(proof.get("build_id", "")).lower() != "0x4d395832" or
            proof.get("pl_logical_chain_calls") != 4166 or
            proof.get("expected_pl_logical_chain_calls") != 4166 or
            proof.get("language_cpu_linear_fallback") is not False):
        raise RuntimeError("M203 M202 formal PASS proof mismatch")
    uart_text = UART.read_text(encoding="utf-8", errors="replace")
    for marker in ("M202_FIXED_VIDEO_E2E_PASS", "M202_FIXED_VIDEO_E2E_RUNNER_PASS", "__M202_FIXED_VIDEO_RUNNER_RC_0__"):
        if marker not in uart_text:
            raise RuntimeError(f"M203 UART marker missing: {marker}")
    formal_sha, uart_sha, m200_sha = sha256(FORMAL), sha256(UART), sha256(M200)
    m200 = json.loads(M200.read_text(encoding="utf-8"))
    if m200.get("status") != "PASS_SOURCE_READY":
        raise RuntimeError("M203 M200 source result mismatch")
    board = json.loads(BOARD.read_text(encoding="utf-8-sig"))
    board["status"] = "M202_FIXED_FOUR_FRAME_VIDEO_FPGA_E2E_PASS_CONTINUOUS_VIDEO_PENDING"
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m200_video_service_overlay_source"] = {
        **m200,
        "formal_result": "deployment/mage_vl4b/M200_VIDEO_E2E_OVERLAY_SOURCE_AUDIT_RESULT.json",
        "formal_result_sha256": m200_sha,
    }
    board["latest_m202_fixed_video_e2e"] = {
        "status": "PASS",
        "attempt": "01",
        "classification": value["classification"],
        "candidate_build_id": value["candidate_build_id"],
        "input_contract": value["input_contract"],
        "vision_compute_policy": value["vision_compute_policy"],
        "prompt_tokens": value["prompt_tokens"],
        "generated_tokens": value["generated_tokens"],
        "generated_token_id": value["generated_token_id"],
        "generated_text": value["generated_text"],
        "first_token_ms": value["first_token_ms"],
        "stream_total_ms": value["stream_total_ms"],
        "wall_ms": value["wall_ms"],
        "fpga_proof": proof,
        "web_deployed": False,
        "formal_result": "deployment/mage_vl4b/M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json",
        "formal_result_sha256": formal_sha,
        "uart_log": "tmp/m202_video_e2e/run_01.log",
        "uart_log_sha256": uart_sha,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Bounded two-window continuous-video runtime reuse gate, then HTTP/SSE continuous stream.",
    }
    rejected = board.setdefault("rejected_attempts", [])
    attempt_name = "M202 initial monolithic BOARD_GATE_RESULT UART upload"
    if not any(item.get("attempt") == attempt_name for item in rejected if isinstance(item, dict)):
        rejected.append({
            "attempt": attempt_name,
            "reason": "A full historical BOARD_GATE_RESULT was embedded in one UART base64 command; it timed out and left bash at a continuation prompt before any gate or overlay load.",
            "resolution": "Ctrl+C prompt recovery, then a hash-locked reduced predecessor summary; M202 v2 bootstrap passed.",
            "board_compute_executed": False,
        })
    board["next_gate"] = "Run a bounded two-window continuous-video reuse gate; only then expose continuous HTTP/SSE/Web input."
    atomic(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    minutes = float(value["first_token_ms"]) / 60000.0
    wall_minutes = float(value["wall_ms"]) / 60000.0
    body = f"""
## M202：固定四帧 4B 视频—语言 FPGA E2E 实板通过（2026-09-01）

- 真实 KV260 输入 4 帧 `448x448x3` RGB，PS 运行 W4 视觉塔（L0--5 BF16、L6--23 FP32、层间回 BF16），随后将 784 个视觉 token 拼入 849-token 提示并由 M120 FPGA 完成语言层和 LM Head。
- FPGA 证据：Build ID `0x4D395832`；逻辑链调用 `4166/4166`；expected macros `{proof['pl_expected_macros']}`；CPU Linear fallback `false`；生成首 token `A`（ID 32）。
- 首 token（含预处理、视觉和 Prefill，不含一次性 runtime load）`{value['first_token_ms']:.3f} ms`（{minutes:.2f} 分钟）；完整门禁墙钟 `{value['wall_ms']:.3f} ms`（{wall_minutes:.2f} 分钟）。该结果是固定四帧 L5 E2E，不是任意视频、连续实时视频或 Web PASS。
- 正式结果：`deployment/mage_vl4b/M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json`，SHA-256 `{formal_sha}`；UART：`tmp/m202_video_e2e/run_01.log`，SHA-256 `{uart_sha}`。
- 被拒绝的操作：首次把整份历史 BOARD JSON 放进单条 UART base64 命令，超时并留下 `>` 续行提示符；未加载 overlay。已用 Ctrl+C 恢复，并改为哈希锁定的最小前置摘要后通过。
- Boot、DTB、CMA、分区、服务均未修改，稳定回滚保留。下一步只做 2 个连续滑动窗口的 runtime/overlay 复用门禁，再接 HTTP/SSE 网页连续流。
"""
    replace_marker(CURRENT, "<!-- M202_FIXED_VIDEO_PASS_START -->", "<!-- M202_FIXED_VIDEO_PASS_END -->", body)
    replace_marker(MILESTONES, "<!-- M202_FIXED_VIDEO_PASS_START -->", "<!-- M202_FIXED_VIDEO_PASS_END -->", body)
    review = """
## M202 UART 大状态文件与续行提示符（2026-09-01）

- 错误：将完整历史 `BOARD_GATE_RESULT.json` 通过单条 base64/Python UART 命令上传；命令过长后超时，并把 shell 留在 `>` 续行状态。
- 后果：后续 `sudo -n true` 被拼入未结束命令，控制器超时；FPGA 门禁和 overlay 均未启动。
- 固定规则：UART 控制包只携带当前门禁所需的最小前置摘要，并在主机端锁定其来源文件 SHA-256；大文件必须使用分块协议，不得再次拼成一条 shell 命令。
- 恢复规则：观察到 `>` 时不得继续发送普通命令；先核对 FTDI 身份、发送一次 Ctrl+C、确认恢复 `ubuntu@kria:~$`，再从失败的传输层重跑。
- 同时修复：M200 必须读取权威字段 `latest_m120_fixed_text_board_gate`，并核对 M179 正式结果 SHA；不得引用不存在的别名字段。
"""
    text = REVIEW.read_text(encoding="utf-8")
    if "## M202 UART 大状态文件与续行提示符" not in text:
        atomic(REVIEW, text.rstrip() + "\n\n" + review.strip() + "\n")
    print(f"M203_M202_AUTHORITATIVE_STATE_SYNC_PASS formal_sha256={formal_sha} uart_sha256={uart_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
