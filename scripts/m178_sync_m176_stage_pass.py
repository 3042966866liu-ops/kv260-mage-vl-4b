#!/usr/bin/env python3
"""Synchronize the verified M176 host-runtime board-stage PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REL = "deployment/mage_vl4b/M176_M120_LMHEAD_OPTIONAL_LAYER_BOARD_STAGE_RESULT_01.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def replace_marker(path: Path, start: str, end: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    block = f"{start}\n{body.rstrip()}\n{end}\n\n"
    if start in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before + block + after.lstrip("\r\n")
    else:
        lines = text.splitlines(keepends=True)
        insert = 1 if lines and lines[0].startswith("# ") else 0
        text = "".join(lines[:insert]) + ("\n" if insert else "") + block + "".join(lines[insert:])
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    path = ROOT / REL
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "PASS" or value.get("candidate_build_id") != "0x4D395832":
        raise RuntimeError("M178 M176 identity/status mismatch")
    if value.get("package_manifest_sha256") != "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f" or value.get("file_count") != 18:
        raise RuntimeError("M178 M176 package mismatch")
    if value.get("changed_files") != ["SOURCE_MANIFEST.json", "runtime/board_runtime.py", "runtime/text_e2e_gate.py"]:
        raise RuntimeError("M178 M176 change closure mismatch")
    uart = Path(value["uart_log"])
    if not uart.is_absolute():
        uart = ROOT / uart
    if digest(uart) != value.get("uart_log_sha256") or "M176_LMHEAD_OPTIONAL_LAYER_STAGE_PASS" not in uart.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError("M178 M176 UART evidence mismatch")
    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M176_LMHEAD_OPTIONAL_LAYER_STAGE_PASS_FIXED_TEXT_RERUN_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m176_lmhead_optional_layer_stage"] = {**value, "formal_result": REL, "formal_result_sha256": digest(path)}
    board["next_gate"] = "Rerun only the frozen fixed-text E2E against M176 package 406dcca3; arbitrary prompt, video and Web remain locked."
    atomic_json(board_path, board)
    body = f"""## M176: LM-head optional-layer host fix is atomically staged on KV260 (2026-09-01)

- A five-member, `49,593`-byte delta was transferred over COM3 with manifest/member SHA-256 verification. The corrected 18-file candidate is `{value['output']}` with package-manifest SHA-256 `{value['package_manifest_sha256']}`.
- Only `SOURCE_MANIFEST.json`, `runtime/board_runtime.py` and `runtime/text_e2e_gate.py` changed. FPGA bitstream, contracts and all model weights remain byte-identical.
- Boot, DTB, CMA, partitions, services and stable rollback were not changed. This is staging only, not a fixed-text, full-model, performance, video or Web PASS.
- Next gate: rerun only fixed-text E2E against this exact package.

Evidence: `{REL}` (SHA-256 `{digest(path)}`), UART log SHA-256 `{value['uart_log_sha256']}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M176_STAGE_PASS_START -->", "<!-- M176_STAGE_PASS_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M176_STAGE_PASS_START -->", "<!-- M176_STAGE_PASS_END -->", body.replace("## M176:", "## M176："))
    print(json.dumps({"status": "PASS", "m176_result_sha256": digest(path), "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M178_M176_STAGE_PASS_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
