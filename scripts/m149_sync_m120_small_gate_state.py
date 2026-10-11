#!/usr/bin/env python3
"""Fail-closed synchronization for the M120 real-board small-gate sequence.

This script accepts only a collected M138/M139/M140 board result.  It verifies
the result identity and retained UART log before atomically updating the
authoritative JSON and Markdown state.  It never promotes Layer-0, fixed-text,
full-model, performance, video, or Web status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BUILD_ID = "0x4d395832"
EXPECTED_PACKAGE_MANIFEST = (
    "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
)
LEVELS = {
    "build-id": {
        "gate": "M138-M120-COM3-build-id",
        "milestone": "M138",
        "pass_status": "M138_M120_BUILD_ID_BOARD_PASS_DESCRIPTOR_PENDING_STABLE_PRESERVED",
        "fail_status": "M138_M120_BUILD_ID_BOARD_FAIL_REMAIN_AT_BUILD_ID_STABLE_PRESERVED",
        "pass_next": "Run one real M120 single-descriptor gate over COM3 only.",
        "evidence": "L4 Build-ID subgate",
    },
    "single-descriptor": {
        "gate": "M139-M120-COM3-single-descriptor",
        "milestone": "M139",
        "pass_status": "M139_M120_SINGLE_DESCRIPTOR_BOARD_PASS_SINGLE_CHAIN_PENDING_STABLE_PRESERVED",
        "fail_status": "M139_M120_SINGLE_DESCRIPTOR_BOARD_FAIL_REMAIN_AT_DESCRIPTOR_STABLE_PRESERVED",
        "pass_next": "Run one real M120 single-chain gate over COM3 only.",
        "evidence": "L4.1 real single-descriptor numerical subgate",
    },
    "single-chain": {
        "gate": "M140-M120-COM3-single-chain",
        "milestone": "M140",
        "pass_status": "M140_M120_SINGLE_CHAIN_BOARD_PASS_FULL_USB_STAGE_UNLOCKED_STABLE_PRESERVED",
        "fail_status": "M140_M120_SINGLE_CHAIN_BOARD_FAIL_REMAIN_AT_CHAIN_STABLE_PRESERVED",
        "pass_next": (
            "Stage and hash-verify the complete M120 language/head payload via USB, "
            "then run the M145 Layer-0 gate; fixed-text remains locked."
        ),
        "evidence": "L4.2 real single-chain numerical subgate",
    },
}
START = "<!-- M149_M120_SMALL_GATE_SYNC_START -->"
END = "<!-- M149_M120_SMALL_GATE_SYNC_END -->"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.m149.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def update_block(text: str, block: str, *, anchor: str) -> str:
    wrapped = f"{START}\n{block.rstrip()}\n{END}"
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise RuntimeError("M149 Markdown markers are incomplete or duplicated")
        prefix, remainder = text.split(START, 1)
        _, suffix = remainder.split(END, 1)
        return prefix + wrapped + suffix
    index = text.find(anchor)
    if index < 0:
        raise RuntimeError(f"Markdown insertion anchor absent: {anchor!r}")
    insertion = index + len(anchor)
    return text[:insertion] + "\n\n" + wrapped + text[insertion:]


def checked_result(path: Path, level: str) -> tuple[dict[str, Any], str]:
    contract = LEVELS[level]
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("gate") != contract["gate"]:
        raise RuntimeError("formal result gate identity mismatch")
    if value.get("status") not in {"PASS", "FAIL"}:
        raise RuntimeError("formal result status is neither PASS nor FAIL")
    if str(value.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID:
        raise RuntimeError("formal result Build ID mismatch")

    uart_value = value.get("uart_log")
    if not isinstance(uart_value, str) or not uart_value:
        raise RuntimeError("formal result has no retained UART log")
    uart_path = Path(uart_value)
    if not uart_path.is_absolute():
        uart_path = ROOT / uart_path
    if not uart_path.is_file():
        raise RuntimeError(f"retained UART log is absent: {uart_path}")
    observed_uart_sha = sha256(uart_path)
    if observed_uart_sha != value.get("uart_log_sha256"):
        raise RuntimeError("retained UART log SHA-256 mismatch")

    if value["status"] == "PASS":
        if value.get("package_manifest_sha256") != EXPECTED_PACKAGE_MANIFEST:
            raise RuntimeError("PASS package manifest mismatch")
        if value.get("fpga_transaction_executed") is not True:
            raise RuntimeError("PASS does not prove one real FPGA transaction")
        if value.get("overlay_loaded") is not True:
            raise RuntimeError("PASS does not prove overlay load")
        if value.get("stable_rollback_preserved") is not True:
            raise RuntimeError("PASS does not preserve stable rollback")
        if value.get("boot_dtb_cma_partitions_services_changed") is not False:
            raise RuntimeError("PASS reports a prohibited persistent board change")
    return value, sha256(path)


def markdown_block(
    *, level: str, result: dict[str, Any], result_path: Path, result_sha: str, now: str
) -> str:
    contract = LEVELS[level]
    status = result["status"]
    next_gate = contract["pass_next"] if status == "PASS" else result.get("next_gate", "Remain at this level.")
    error = ""
    if status == "FAIL":
        error = f"\n- 失败原因：`{result.get('error', 'unspecified')}`。"
    return (
        f"## M149：M120 实板小门禁自动同步（{now}）\n\n"
        f"- 当前完成级别：`{contract['milestone']} / {level}`；正式状态：`{status}`；"
        f"证据等级仅为 `{contract['evidence']}`。\n"
        f"- 候选 Build ID：`0x4D395832`；包清单：`{EXPECTED_PACKAGE_MANIFEST}`。\n"
        f"- 正式结果：`{relative(result_path)}`，SHA-256=`{result_sha}`；"
        f"UART 日志 SHA-256=`{result['uart_log_sha256']}`。"
        f"{error}\n"
        f"- 下一步：{next_gate}\n"
        "- 本记录不代表 Layer-0、固定文本、完整 4B、性能、视频或 Web PASS；"
        "boot/DTB/CMA/分区/服务未修改，稳定回滚保持不变。"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=tuple(LEVELS), required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument(
        "--board-state", type=Path, default=ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    )
    parser.add_argument("--current-state", type=Path, default=ROOT / "CURRENT_STATE.md")
    parser.add_argument("--milestones", type=Path, default=ROOT / "docsMILESTONES.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result_path = args.result.resolve()
    result, result_sha = checked_result(result_path, args.level)
    contract = LEVELS[args.level]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    status = result["status"]
    next_gate = contract["pass_next"] if status == "PASS" else result.get("next_gate")

    board = json.loads(args.board_state.read_text(encoding="utf-8"))
    board["status"] = contract["pass_status"] if status == "PASS" else contract["fail_status"]
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["next_gate"] = next_gate
    board["stable_rollback_preserved"] = True
    board["latest_m120_board_gate"] = {
        "level": args.level,
        "gate": result["gate"],
        "status": status,
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": result.get(
            "package_manifest_sha256", EXPECTED_PACKAGE_MANIFEST
        ),
        "formal_result": relative(result_path),
        "formal_result_sha256": result_sha,
        "uart_log": result["uart_log"],
        "uart_log_sha256": result["uart_log_sha256"],
        "evidence_level": result.get("evidence_level", contract["evidence"]),
        "error": result.get("error"),
        "next_gate": next_gate,
        "synchronized_at": now,
    }
    sequence = board.setdefault("m120_small_gate_sequence", {})
    sequence[args.level] = board["latest_m120_board_gate"]

    block = markdown_block(
        level=args.level,
        result=result,
        result_path=result_path,
        result_sha=result_sha,
        now=now,
    )
    current = update_block(
        args.current_state.read_text(encoding="utf-8"),
        block,
        anchor="Updated: 2026-09-01",
    )
    milestones = update_block(
        args.milestones.read_text(encoding="utf-8"),
        block,
        anchor="# TeLLMe / Qwen KV260 优化里程碑",
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "gate": "M149-M120-small-gate-state-sync",
                    "status": "DRY_RUN_PASS",
                    "level": args.level,
                    "source_status": status,
                    "would_set_board_status": board["status"],
                    "would_set_next_gate": next_gate,
                    "formal_result_sha256": result_sha,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    atomic_json(args.board_state, board)
    atomic_text(args.current_state, current)
    atomic_text(args.milestones, milestones)
    print(
        json.dumps(
            {
                "gate": "M149-M120-small-gate-state-sync",
                "status": "PASS",
                "level": args.level,
                "source_status": status,
                "board_status": board["status"],
                "next_gate": next_gate,
                "formal_result_sha256": result_sha,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print("M149_M120_SMALL_GATE_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
