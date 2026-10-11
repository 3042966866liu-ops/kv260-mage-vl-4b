#!/usr/bin/env python3
"""Synchronize the verified M179 fixed-reference full-text E2E PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REL = "deployment/mage_vl4b/M179_M120_FIXED_TEXT_BOARD_RESULT_01.json"


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
    evidence = value.get("evidence", {})
    timing = value.get("timing", {})
    if value.get("status") != "PASS" or value.get("generated_token_id") != 17 or value.get("expected_token_id") != 17:
        raise RuntimeError("M180 M179 token/status mismatch")
    if value.get("reference_match") is not True or value.get("fpga_execution_proved") is not True or value.get("cpu_linear_fallback") is not False:
        raise RuntimeError("M180 M179 FPGA proof mismatch")
    if value.get("package_manifest_sha256") != "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f":
        raise RuntimeError("M180 M179 package mismatch")
    if value.get("expected_calls") != 162 or evidence.get("logical_calls") != 162 or evidence.get("logical_expected_macros") != 2011136000:
        raise RuntimeError("M180 M179 call/macro mismatch")
    if str(evidence.get("build_id", "")).lower() != "0x4d395832" or evidence.get("weight_mode") != "staged-low-cma":
        raise RuntimeError("M180 M179 build/mode mismatch")
    uart = Path(value["uart_log"])
    if not uart.is_absolute():
        uart = ROOT / uart
    uart_text = uart.read_text(encoding="utf-8", errors="replace")
    if digest(uart) != value.get("uart_log_sha256") or "M120_FIXED_TEXT_E2E_PASS" not in uart_text or "M179_M120_FIXED_TEXT_E2E_RUNNER_PASS" not in uart_text:
        raise RuntimeError("M180 M179 UART evidence mismatch")

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M179_M120_FIXED_TEXT_E2E_PASS_ARBITRARY_TEXT_AND_VIDEO_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_fixed_text_board_gate"] = {
        **value,
        "formal_result": REL,
        "formal_result_sha256": digest(path),
        "scope_boundary": "L5 fixed-reference complete 36-layer plus LM-head E2E; not arbitrary prompt, general deployment, video or Web evidence.",
    }
    board["next_gate"] = "Unlock M148 full W3 embedding extraction and clean video package generation; arbitrary-prompt text/Web remains a separate next level."
    atomic_json(board_path, board)

    body = f"""## M179: fixed-reference complete M120 text E2E passes on the real KV260 (2026-09-01)

- The frozen 30-token prompt generated token `17`, exactly matching the official reference. Build ID is `0x4D395832`; `cpu_linear_fallback=false` and FPGA execution proof is true.
- The complete 36-layer language path plus eight LM-head slices executed `162` logical FPGA calls and `2,011,136,000` logical expected macros. Three additional physical calls were finite-retry attempts, giving `165` host calls and `2,048,491,520` physical expected macros.
- Staged-low-CMA moved `{evidence['stage_bytes']}` weight bytes in `{evidence['stage_ms']:.3f}` ms. Total E2E time was `{timing['total_ms']:.3f}` ms; the 36-layer language portion was `{timing['language_ms']:.3f}` ms. This is a measured fixed-reference result, not a CPU comparison or speed superiority claim.
- The M175 null-safe LM-head bookkeeping is exercised by all eight `layer=null` head chains. All complete and appear in the retained hardware evidence.
- Scope remains L5 fixed-reference E2E. Arbitrary prompt, general chat/Web and video are not yet proven, so `full_model_deployed` and `web_deployed` remain false.
- M179 unlocks the exact M148 full-W3 embedding extraction and corrected clean video-package path. Video must inherit the M175 host runtime; its visual W4/BF16 bytes remain unchanged.

Evidence: `{REL}` (SHA-256 `{digest(path)}`), UART log SHA-256 `{value['uart_log_sha256']}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M179_FIXED_TEXT_PASS_START -->", "<!-- M179_FIXED_TEXT_PASS_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M179_FIXED_TEXT_PASS_START -->", "<!-- M179_FIXED_TEXT_PASS_END -->", body.replace("## M179:", "## M179："))
    print(json.dumps({"status": "PASS", "m179_result_sha256": digest(path), "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M180_M179_FIXED_TEXT_PASS_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
