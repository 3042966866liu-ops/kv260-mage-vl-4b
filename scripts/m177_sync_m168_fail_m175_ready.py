#!/usr/bin/env python3
"""Retain M168 attempt-01 failure and synchronize the M175 correction readiness."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    log = ROOT / "tmp/m168_fixed_text/run_01_uart.log"
    text = log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r'\{\s*"gate":\s*"M120-fixed-text-E2E".*?\n\}', text, re.S)
    if len(matches) != 1:
        raise RuntimeError(f"M177 expected one M168 result, observed={len(matches)}")
    raw = json.loads(matches[0])
    expected_error = "TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'"
    if raw.get("status") != "FAIL" or raw.get("error") != expected_error or "M120_FIXED_TEXT_E2E_FAIL" not in text:
        raise RuntimeError("M177 M168 failure identity mismatch")
    m167_path = ROOT / "deployment/mage_vl4b/M167_M120_CORRECTED_LAYER0_BOARD_RESULT_01.json"
    m167 = json.loads(m167_path.read_text(encoding="utf-8"))
    if m167.get("status") != "PASS" or m167.get("board_acceptance_sha256") != "8906034715c94b00d8a437b134e4e69c27020fa62dd4cb89e615c2dc05580e1d":
        raise RuntimeError("M177 M167 predecessor mismatch")
    m175_path = ROOT / "deployment/mage_vl4b/M175_M120_LMHEAD_OPTIONAL_LAYER_FIX_RESULT.json"
    m175 = json.loads(m175_path.read_text(encoding="utf-8"))
    if m175.get("status") != "PASS" or m175.get("package_manifest_sha256") != "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f":
        raise RuntimeError("M177 M175 fix identity mismatch")
    formal = {
        "date": "2026-09-01",
        "gate": "M120-fixed-text-E2E",
        "status": "FAIL",
        "classification": "Real-board fixed-text attempt rejected by a host bookkeeping exception after language execution; not a numerical, full-model, performance, video or Web PASS.",
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97",
        "m167_predecessor_result": m167_path.relative_to(ROOT).as_posix(),
        "m167_predecessor_result_sha256": digest(m167_path),
        "environment_preflight_pass": "M136_M120_BOARD_ENV_PASS" in text,
        "predecessor_gate_pass": "M168_M167_LAYER0_PREDECESSOR_PASS" in text,
        "error": raw["error"],
        "total_ms": raw["total_ms"],
        "root_cause": "All eight LM-head chains declare layer=null, while two success/failure bookkeeping paths unconditionally called int(chain['layer']) whenever the key existed.",
        "fpga_arithmetic_changed_by_fix": False,
        "weights_changed_by_fix": False,
        "contracts_changed_by_fix": False,
        "cpu_linear_fallback": False,
        "fixed_text_pass": False,
        "full_model_deployed": False,
        "video_deployed": False,
        "web_deployed": False,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "uart_log": log.relative_to(ROOT).as_posix(),
        "uart_log_sha256": digest(log),
        "next_gate": "Stage M175 host-runtime fix as a new hash-locked candidate, then rerun only fixed-text E2E.",
    }
    formal_path = ROOT / "deployment/mage_vl4b/M168_M120_FIXED_TEXT_BOARD_RESULT_01.json"
    atomic_json(formal_path, formal)

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M168_FIXED_TEXT_HOST_RUNTIME_FAIL_M175_FIX_READY"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_fixed_text_board_gate"] = {**formal, "formal_result": formal_path.relative_to(ROOT).as_posix(), "formal_result_sha256": digest(formal_path)}
    board["latest_m175_lmhead_optional_layer_fix"] = {**m175, "formal_result": m175_path.relative_to(ROOT).as_posix(), "formal_result_sha256": digest(m175_path)}
    board["next_gate"] = formal["next_gate"]
    atomic_json(board_path, board)

    body = f"""## M168 attempt 01 / M175: fixed-text host bookkeeping failure is corrected offline (2026-09-01)

- M168 passed the exact package/environment preflight and exact M167 predecessor check, then stopped after `{raw['total_ms']:.3f}` ms with `{expected_error}`. It is formally retained as FAIL, not hidden by the collector failure.
- Contract inspection proves all eight LM-head chains use a valid JSON `layer: null`. The shared board runtime had two bookkeeping expressions that tested only key presence and then evaluated `int(null)`. This defect is reached at LM-head execution; it is not a weight, descriptor, FPGA arithmetic or numerical-accuracy change.
- M175 builds a new clean 18-file candidate with package-manifest SHA-256 `{m175['package_manifest_sha256']}`. Both bookkeeping sites now convert only non-null layers. The failure path also preserves traceback and partial hardware counters. Python compilation and exact two-site regression checks pass.
- The video runtime reuses this board runtime, so it must inherit M175 rather than the earlier M165 slice; the visual W4/BF16 path itself remains unchanged.
- No boot, DTB, CMA, partition, service or rollback state changed. Next gate: stage M175 over COM3, then rerun fixed-text E2E only.

Evidence: `{formal_path.relative_to(ROOT).as_posix()}` (SHA-256 `{digest(formal_path)}`), `{m175_path.relative_to(ROOT).as_posix()}` (SHA-256 `{digest(m175_path)}`)."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M168_M175_HOST_FIX_START -->", "<!-- M168_M175_HOST_FIX_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M168_M175_HOST_FIX_START -->", "<!-- M168_M175_HOST_FIX_END -->", body.replace("## M168 attempt 01 / M175:", "## M168 attempt 01 / M175："))
    print(json.dumps({"status": "PASS", "m168_fail_sha256": digest(formal_path), "m175_fix_sha256": digest(m175_path), "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M177_M168_FAIL_M175_READY_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
