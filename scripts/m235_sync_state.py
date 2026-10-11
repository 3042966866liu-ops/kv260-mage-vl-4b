#!/usr/bin/env python3
"""Atomically record the rejected M235 board gate and verified service recovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "deployment/mage_vl4b/M235_PARSE_LAUNCH_OVERLAP_BOARD_RESULT_01.json"
RUN_LOG = ROOT / "tmp/m235_parse_launch_overlap/attempt_01/run_uart.log"
RECOVERY_LOG = ROOT / "tmp/m235_parse_launch_overlap/service_recovery_run.log"
RECOVERY_FORMAL = ROOT / "deployment/mage_vl4b/M235_POST_FAILURE_SERVICE_RESULT_01.json"
BOARD = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
CURRENT = ROOT / "CURRENT_STATE.md"
MILESTONES = ROOT / "docsMILESTONES.md"
MISTAKES = ROOT / "DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8", newline="\n")
    os.replace(partial, path)


def extract_recovery() -> dict:
    text = RECOVERY_LOG.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"__M227_BOARD_RESULT_BEGIN__\s*(\{.*?\})\s*__M227_BOARD_RESULT_END__",
        text,
        flags=re.S,
    )
    if len(matches) != 1:
        raise RuntimeError(f"expected one M227 recovery envelope, found {len(matches)}")
    health = json.loads(matches[0])
    if health.get("status") != "PASS" or "M235_POST_FAILURE_SERVICE_PASS" not in text:
        raise RuntimeError("M235 post-failure service recovery did not pass")
    return health


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        raise RuntimeError(f"refusing duplicate state block: {marker}")
    atomic_text(path, text.rstrip() + "\n\n" + block.strip() + "\n")


def main() -> int:
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    if formal.get("gate") != "M235-real-KV260-parse-launch-overlap-acceptance":
        raise RuntimeError("M235 formal gate identity mismatch")
    if formal.get("status") != "FAIL":
        raise RuntimeError("M235 is not a rejected board result")
    family = formal["family"]
    if family.get("output_bit_exact") is not True or float(family.get("maximum_abs_error")) != 0.0:
        raise RuntimeError("M235 numerical identity evidence missing")
    if not float(family["wall_speedup"]) < float(family["required_wall_speedup"]):
        raise RuntimeError("M235 rejection reason is not the fixed performance threshold")

    health = extract_recovery()
    recovery = {
        "date": "2026-09-01",
        "gate": "M235-post-failure-realtime-service-recovery",
        "status": "PASS",
        "classification": "Real-KV260 local control-plane health after the rejected M235 family gate; no inference or candidate promotion claim.",
        "source_board_gate": FORMAL.relative_to(ROOT).as_posix(),
        "source_board_gate_sha256": sha256(FORMAL),
        "uart_log": RECOVERY_LOG.relative_to(ROOT).as_posix(),
        "uart_log_sha256": sha256(RECOVERY_LOG),
        "service_pid": health["service_pid"],
        "local_health": health["local_health"],
        "patch_manifest_sha256": health["patch_manifest_sha256"],
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    atomic_text(RECOVERY_FORMAL, json.dumps(recovery, indent=2, ensure_ascii=False) + "\n")
    recovery_hash = sha256(RECOVERY_FORMAL)

    board = json.loads(BOARD.read_text(encoding="utf-8"))
    board["latest_m235_parse_launch_overlap"] = {
        "status": "FAIL_NOT_PROMOTED",
        "classification": "Real KV260 849-token single-family T32 parse/launch-overlap gate; output bit-exact but fixed 1.10x wall-speed threshold missed. Independent of T64; not fixed-text, video, Web, or real-time evidence.",
        "candidate_build_id": family["build_id"],
        "tokens": family["tokens"],
        "t32_blocks": family["t32_blocks_per_run"],
        "m231_wall_ms": family["m231_wall_ms"],
        "m235_wall_ms": family["m235_wall_ms"],
        "wall_speedup": family["wall_speedup"],
        "required_wall_speedup": family["required_wall_speedup"],
        "output_bit_exact": family["output_bit_exact"],
        "maximum_abs_error": family["maximum_abs_error"],
        "host_calls": family["host_calls"],
        "expected_host_calls": family["expected_host_calls"],
        "pipeline_submissions": family["pipeline_submissions"],
        "pipeline_reuse_waits": family["pipeline_reuse_waits"],
        "raw_finite_precheck_ms": family["m235_phase_ms"]["finite_check"],
        "cpu_linear_fallback": family["cpu_linear_fallback"],
        "formal_result": FORMAL.relative_to(ROOT).as_posix(),
        "formal_result_sha256": sha256(FORMAL),
        "uart_log": RUN_LOG.relative_to(ROOT).as_posix(),
        "uart_log_sha256": sha256(RUN_LOG),
        "service_recovery_result": RECOVERY_FORMAL.relative_to(ROOT).as_posix(),
        "service_recovery_result_sha256": recovery_hash,
        "service_pid": health["service_pid"],
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "mainline_remains": "M231 parser plus M232 fixed-text E2E",
        "next_gate": "Do not rerun M235 unchanged. Remove the 403.978 ms Python raw-finite scan or fuse it into the existing parser, then prove bit-exactness offline before a new candidate number.",
    }
    atomic_text(BOARD, json.dumps(board, indent=2, ensure_ascii=False) + "\n")

    current_block = f"""
<!-- M235_PARSE_LAUNCH_OVERLAP_START -->
## M235 — T32 parse/launch overlap：REAL_KV260_FAIL_NOT_PROMOTED（2026-09-01）

- 真实 KV260、849-token、27 个 T32 block 的双输出 DMA 缓冲流水已执行；27 次提交、25 次缓冲复用等待、54/54 host calls，无 CPU Linear fallback。
- 输出与 M231 位精确一致，FP32 SHA-256 均为 `{family['m235_output_sha256_fp32']}`，最大绝对误差为 0。
- 墙钟 `{family['m231_wall_ms']:.3f} -> {family['m235_wall_ms']:.3f} ms`，加速 `{family['wall_speedup']:.6f}x`，略低于预先固定的 `{family['required_wall_speedup']:.2f}x` 晋级线，因此 FAIL_NOT_PROMOTED；没有继续 fixed-text 或 Web。
- 实测新开销是逐 block 的 raw FP16 finite 预检，共 `{family['m235_phase_ms']['finite_check']:.3f} ms`；它抵消了 parse/launch 重叠收益。不得原样重跑 M235，下一候选必须把有限性检查融合进已有解析，或以不新增第二遍 Python 扫描的方式保留异常检测。
- 原始门禁失败路径虽由 trap 恢复服务，但未留下健康标记；随后使用哈希一致的版本化脚本确认服务 PID `{health['service_pid']}`、本机 health PASS。Boot、DTB、CMA、分区与稳定回滚均未改变。
- 正式门禁：`{FORMAL.relative_to(ROOT).as_posix()}`（SHA-256 `{sha256(FORMAL)}`）；服务恢复：`{RECOVERY_FORMAL.relative_to(ROOT).as_posix()}`（SHA-256 `{recovery_hash}`）。主线仍为 M231 + M232。
<!-- M235_PARSE_LAUNCH_OVERLAP_END -->
"""
    append_once(CURRENT, "<!-- M235_PARSE_LAUNCH_OVERLAP_START -->", current_block)
    append_once(MILESTONES, "<!-- M235_PARSE_LAUNCH_OVERLAP_START -->", current_block)

    mistake_block = """
## M235 失败收尾必须保留原门禁返回码并单独证明服务恢复（2026-09-01）

- 错误一：候选 Python 因性能门槛返回非零后，`set -e` 直接跳入 EXIT trap。trap 确实重新启动了服务，但旧 runner 没有在失败分支执行有界 health probe，导致正式结果只能记录 `service_restore_marker=false`。
- 错误二：PowerShell 收集器的失败分支写成 `throw\"...\"`，解析器未报错，运行时却将拼接后的字符串当成命令名；这重复了 M188--M192 已记录的错误类别。
- 影响边界：M235 输出位精确，未达性能线而未晋级；稳定 Web 服务已由独立、哈希核验的版本化脚本确认恢复，boot/DTB/CMA/分区均未改变。
- 固定规则：所有会停止服务的 runner，其 EXIT trap 在失败时也必须执行有界 health probe，同时保存原始门禁返回码；控制器的 `throw` 必须有空格并执行故意失败分支 smoke，不能只做 AST 解析。已有 M235 源 runner 和控制器已按此修正，旧哈希封闭候选保持不可变。
"""
    append_once(MISTAKES, "## M235 失败收尾必须保留原门禁返回码", mistake_block)

    print(json.dumps({
        "gate": "M235-state-sync",
        "status": "PASS",
        "formal_sha256": sha256(FORMAL),
        "run_uart_sha256": sha256(RUN_LOG),
        "recovery_result_sha256": recovery_hash,
        "service_pid": health["service_pid"],
        "mainline": "M231+M232",
    }, indent=2))
    print("M235_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
