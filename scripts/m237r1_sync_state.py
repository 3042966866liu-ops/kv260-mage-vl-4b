#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT_PATH = ROOT / "CURRENT_STATE.md"
MILESTONES_PATH = ROOT / "docsMILESTONES.md"
MISTAKES_PATH = ROOT / "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md"
M237_PATH = ROOT / "deployment/mage_vl4b/M237_M236_FIXED_TEXT_BOARD_RESULT_01.json"
M237R1_PATH = ROOT / "deployment/mage_vl4b/M237R1_ACCEPTANCE_REPAIR_BOARD_RESULT_02.json"
M237_LOG = ROOT / "tmp/m237_fixed_text/attempt_01/run_uart.log"
M237R1_LOG = ROOT / "tmp/m237r1_acceptance_repair/attempt_02/run_uart.log"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, text: str) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)


def insert_after_heading(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        raise RuntimeError(f"duplicate sync marker in {path.name}: {marker}")
    heading = "# Current verified state\n"
    if not text.startswith(heading):
        raise RuntimeError("CURRENT_STATE heading mismatch")
    write_atomic(path, heading + "\n" + section.rstrip() + "\n\n" + text[len(heading) :].lstrip("\n"))


def append_section(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        raise RuntimeError(f"duplicate sync marker in {path.name}: {marker}")
    write_atomic(path, text.rstrip() + "\n\n" + section.rstrip() + "\n")


def main() -> int:
    m237 = json.loads(M237_PATH.read_text())
    repaired = json.loads(M237R1_PATH.read_text())
    if m237.get("status") != "FAIL":
        raise RuntimeError("M237 initial outer acceptance must remain recorded as FAIL")
    if repaired.get("status") != "PASS":
        raise RuntimeError("M237R1 board acceptance repair is not PASS")
    acceptance = repaired["acceptance"]
    if not all(acceptance["checks"].values()):
        raise RuntimeError("M237R1 contains a failed acceptance check")
    fixed = acceptance["fixed_text"]
    evidence = fixed["evidence"]
    timing = fixed["timing"]
    if fixed.get("generated_token_id") != fixed.get("expected_token_id") or fixed.get("generated_token_id") != 17:
        raise RuntimeError("M237 fixed token mismatch")

    m237_sha = sha(M237_PATH)
    repaired_sha = sha(M237R1_PATH)
    m237_log_sha = sha(M237_LOG)
    repaired_log_sha = sha(M237R1_LOG)
    m232_language_ms = 34989.99732499942
    m232_total_ms = 50693.557545004296
    language_ratio = m232_language_ms / float(timing["language_ms"])
    total_ratio = m232_total_ms / float(timing["total_ms"])

    board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    board["latest_m237r1_m236_fixed_text"] = {
        "date": "2026-09-01",
        "status": "PASS_SERVICE_HEALTH_CONFIRMED",
        "classification": (
            "Frozen fixed-text complete 4B FPGA E2E through M236, accepted by an "
            "acceptance-only repair over the immutable M237 board measurement; not "
            "Web integration, video, arbitrary prompt, or real-time evidence."
        ),
        "candidate_build_id": evidence["build_id"],
        "kernel": "mage_m120_m89x2_0",
        "generated_token_id": fixed["generated_token_id"],
        "expected_token_id": fixed["expected_token_id"],
        "reference_match": fixed["reference_match"],
        "fpga_execution_proved": fixed["fpga_execution_proved"],
        "cpu_linear_fallback": fixed["cpu_linear_fallback"],
        "logical_calls": evidence["logical_calls"],
        "host_calls": evidence["host_calls"],
        "pipeline_retry_launches": evidence["pipeline_retry_launches"],
        "fused_nonfinite_detections": evidence["fused_nonfinite_detections"],
        "scale_retry_count": evidence["scale_retry_count"],
        "retry_bookkeeping_consistent_and_resolved": True,
        "standalone_raw_finite_scan": evidence["standalone_raw_finite_scan"],
        "adaptive_scale_retry_preserved": evidence["adaptive_scale_retry_preserved"],
        "language_ms": timing["language_ms"],
        "total_ms": timing["total_ms"],
        "m232_language_ratio": language_ratio,
        "m232_total_ratio": total_ratio,
        "performance_interpretation": (
            "M236 is correctness-safe at complete fixed text, but the 30-token prompt "
            "has one T32 block per family and therefore cannot exercise cross-block "
            "parse/launch overlap; its fixed-text time is effectively unchanged from M232."
        ),
        "m237_initial_outer_status": "FAIL_FALSE_NEGATIVE_ACCEPTANCE_RULE",
        "m237_initial_formal_result": "deployment/mage_vl4b/M237_M236_FIXED_TEXT_BOARD_RESULT_01.json",
        "m237_initial_formal_result_sha256": m237_sha,
        "m237_initial_uart_log": "tmp/m237_fixed_text/attempt_01/run_uart.log",
        "m237_initial_uart_log_sha256": m237_log_sha,
        "acceptance_repair_result": "deployment/mage_vl4b/M237R1_ACCEPTANCE_REPAIR_BOARD_RESULT_02.json",
        "acceptance_repair_result_sha256": repaired_sha,
        "acceptance_repair_uart_log": "tmp/m237r1_acceptance_repair/attempt_02/run_uart.log",
        "acceptance_repair_uart_log_sha256": repaired_log_sha,
        "service_pid": repaired["service_pid"],
        "service_health_marker": repaired["service_health_marker"],
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Integrate M236 into a hash-locked Web runtime and measure the fixed "
            "849-token language Prefill before any full visual window."
        ),
    }
    write_atomic(BOARD_PATH, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    current_section = f"""<!-- M237R1_M236_FIXED_TEXT_START -->
## M237/M237R1：M236 完整 4B 固定文本 E2E 已通过（2026-09-01）

- M237 在真实 KV260 上完成全部 36 层与 LM Head：Token `17` 与冻结参考精确一致，
  `fpga_execution_proved=true`、`cpu_linear_fallback=false`，共 `162` 次逻辑调用、
  `165` 次物理调用；语言阶段 `{timing['language_ms']:.3f} ms`，总计
  `{timing['total_ms']:.3f} ms`。
- 运行中 3 个 chain 首次输出非有限；融合解析器检测后按既有 activation-scale 策略降档，
  `pipeline_retry_launches=fused_nonfinite_detections=scale_retry_count=3`，三次均选择最终尝试并
  成功生成正确 Token。没有独立 raw finite 二次扫描，模型数学与 FPGA 事务合同未改变。
- M237 初版验收器错误要求 `pipeline_retry_launches==0`，因此将内层 PASS 误报为外层 FAIL。
  M237R1 未重跑 E2E，而是在板端先证明原测量与哈希锁定副本完全一致，再用正确的“检测数、
  重试数、物理/逻辑调用数一致且最终收敛”规则完成 13 项验收；服务 PID `{repaired['service_pid']}`
  仍通过 health。
- M236 在 30-token fixed-text 上每个 family 只有一个 T32 block，无法产生跨 block overlap；
  相对 M232 的语言/总耗时比例分别为 `{language_ratio:.6f}x`、`{total_ratio:.6f}x`，应视为持平，
  不能把 849-token q-family 的 `1.42347x` 直接宣传成完整模型同等加速。
- 原始误判证据：`deployment/mage_vl4b/M237_M236_FIXED_TEXT_BOARD_RESULT_01.json`
  （SHA-256 `{m237_sha}`）；修复验收：
  `deployment/mage_vl4b/M237R1_ACCEPTANCE_REPAIR_BOARD_RESULT_02.json`
  （SHA-256 `{repaired_sha}`）。boot、DTB、CMA、分区和稳定回滚未改变。
- 下一门禁：把 M236 接入 hash-locked Web runtime，只测固定 849-token language Prefill；
  通过后再进入完整视觉窗口，T64 继续由另一任务独立验证。
<!-- M237R1_M236_FIXED_TEXT_END -->"""
    insert_after_heading(CURRENT_PATH, "M237R1_M236_FIXED_TEXT_START", current_section)
    append_section(MILESTONES_PATH, "M237R1_M236_FIXED_TEXT_START", current_section)

    mistake_section = """## M237 验收器不得把“成功收敛的保护性重试”当成失败（2026-09-01）

- 错误：M237 初版外层验收器硬编码 `pipeline_retry_launches==0`，与已经明确保留的
  `adaptive-power-of-two-finite-retry-v1` 策略矛盾。内层完整 4B E2E 已 PASS、Token 17 精确、
  FPGA 证据成立，但外层仍产生假阴性 FAIL。
- 固定规则：对具备重试语义的运行时，验收必须区分“重试后收敛”与“重试耗尽”。应要求
  `pipeline_retry_launches == fused_nonfinite_detections == scale_retry_count`，每条重试记录的
  `selected_shift` 是最后一次尝试，`host_calls == logical_calls + retry_launches`，并同时要求最终
  输出/Token 门禁 PASS。只有不一致、耗尽或最终非有限才是失败。
- 修复边界：M237R1 只对已锁定的 M237 板端测量进行身份核验和验收重算，没有重跑 E2E，
  没有修改模型、bitstream、权重、boot、DTB、CMA、分区或服务。原始 M237 FAIL 证据必须保留，
  不得覆盖或伪装成当时的 PASS。
"""
    append_section(MISTAKES_PATH, "M237 验收器不得", mistake_section)

    print(
        json.dumps(
            {
                "status": "PASS",
                "board_result_sha256": repaired_sha,
                "m237_result_sha256": m237_sha,
                "current_state_updated": True,
                "milestones_updated": True,
                "mistakes_review_updated": True,
            },
            indent=2,
        )
    )
    print("M237R1_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
