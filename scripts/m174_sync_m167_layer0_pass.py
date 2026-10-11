#!/usr/bin/env python3
"""Synchronize the verified M167 corrected real-board Layer-0 PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_REL = "deployment/mage_vl4b/M167_M120_CORRECTED_LAYER0_BOARD_RESULT_01.json"


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
    path = ROOT / RESULT_REL
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("status") != "PASS" or result.get("candidate_build_id") != "0x4D395832":
        raise RuntimeError("M167 result identity/status mismatch")
    if result.get("package_manifest_sha256") != "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97":
        raise RuntimeError("M167 package identity mismatch")
    measurement = result.get("measurement", {})
    evidence = measurement.get("evidence", {})
    metrics = measurement.get("metrics", {})
    if measurement.get("fpga_execution_proved") is not True or evidence.get("logical_calls") != 5 or evidence.get("logical_expected_macros") != 50462720:
        raise RuntimeError("M167 FPGA execution proof mismatch")
    if set(metrics) != {
        "layer00_q_input", "layer00_kv_input", "layer00_attention_out_input",
        "layer00_gate_up_input", "layer00_mlp_down_input", "layer01_q_input", "layer01_kv_input",
    }:
        raise RuntimeError("M167 boundary closure mismatch")
    for name, metric in metrics.items():
        if metric.get("finite") is not True or metric["relative_l2"] > 0.05 or metric["cosine"] < 0.998:
            raise RuntimeError(f"M167 boundary acceptance mismatch: {name}")
    uart = Path(result["uart_log"])
    if not uart.is_absolute():
        uart = ROOT / uart
    if digest(uart) != result.get("uart_log_sha256"):
        raise RuntimeError("M167 UART log hash mismatch")
    text = uart.read_text(encoding="utf-8", errors="replace")
    for marker in ("M144_M120_LAYER0_ACCEPTANCE_PASS", "M144_M120_LAYER0_RUNNER_PASS"):
        if marker not in text:
            raise RuntimeError(f"M167 UART marker missing: {marker}")

    worst_rel_name, worst_rel = max(metrics.items(), key=lambda item: item[1]["relative_l2"])
    worst_cos_name, worst_cos = min(metrics.items(), key=lambda item: item[1]["cosine"])
    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M167_M120_CORRECTED_LAYER0_PASS_M168_FIXED_TEXT_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_layer0_board_gate"] = {
        "level": "complete-layer0",
        "gate": result["gate"],
        "status": "PASS",
        "candidate_build_id": result["candidate_build_id"],
        "package_manifest_sha256": result["package_manifest_sha256"],
        "fpga_execution_proved": True,
        "logical_calls": evidence["logical_calls"],
        "expected_macros": evidence["logical_expected_macros"],
        "all_boundaries_finite": measurement["all_boundaries_finite"],
        "thresholds": result["thresholds"],
        "worst_relative_l2": {"boundary": worst_rel_name, "value": worst_rel["relative_l2"]},
        "lowest_cosine": {"boundary": worst_cos_name, "value": worst_cos["cosine"]},
        "stage_bytes": evidence["stage_bytes"],
        "stage_ms": evidence["stage_ms"],
        "scale_retry_count": evidence["scale_retry_count"],
        "formal_result": RESULT_REL,
        "formal_result_sha256": digest(path),
        "board_acceptance_sha256": result["board_acceptance_sha256"],
        "uart_log": result["uart_log"],
        "uart_log_sha256": result["uart_log_sha256"],
        "evidence_level": result["evidence_level"],
        "next_gate": "Run only the frozen M168 30-token/one-token fixed-text E2E gate.",
    }
    if "latest_m120_layer0_auxiliary_correction" in board:
        board["latest_m120_layer0_auxiliary_correction"]["board_layer0_pass"] = True
    board["next_gate"] = "Run only the frozen M168 30-token/one-token fixed-text E2E gate; arbitrary prompt, video and Web remain locked."
    atomic_json(board_path, board)

    body = f"""## M167: corrected M120 complete Layer-0 passes on the real KV260 (2026-09-01)

- Build ID `0x4D395832` executed all five Layer-0 logical FPGA chains with `50,462,720` expected macros in `staged-low-cma` mode; no CPU linear fallback is involved in this gate.
- All seven frozen boundaries are finite and pass the predeclared `relative-L2 <= 0.05`, cosine `>= 0.998` policy. Worst relative-L2 is `{worst_rel['relative_l2']:.9f}` at `{worst_rel_name}`; lowest cosine is `{worst_cos['cosine']:.9f}` at `{worst_cos_name}`.
- The corrected first boundary is relative-L2 `{metrics['layer00_q_input']['relative_l2']:.9f}`, cosine `{metrics['layer00_q_input']['cosine']:.9f}`, confirming the stale M77 embedding identity was the M164 failure cause.
- Weight staging moved `{evidence['stage_bytes']}` bytes in `{evidence['stage_ms']:.6f}` ms; all five chains selected scale shift 6 with zero retry.
- This is L4.3 complete-Layer0 evidence, not fixed-text E2E, complete model, performance, arbitrary prompt, video or Web proof. Boot/DTB/CMA/partitions/services and stable rollback remain unchanged.
- Next gate: the frozen M168 30-token/one-token fixed-text E2E only.

Evidence: `{RESULT_REL}` (SHA-256 `{digest(path)}`), board acceptance SHA-256 `{result['board_acceptance_sha256']}`, UART log SHA-256 `{result['uart_log_sha256']}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M167_LAYER0_PASS_START -->", "<!-- M167_LAYER0_PASS_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M167_LAYER0_PASS_START -->", "<!-- M167_LAYER0_PASS_END -->", body.replace("## M167:", "## M167："))
    print(json.dumps({"status": "PASS", "m167_result_sha256": digest(path), "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M174_M167_LAYER0_PASS_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
