#!/usr/bin/env python3
"""Synchronize the real M164 failure, M165 correction, and M166 control failure."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


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
    m164_path = ROOT / "deployment/mage_vl4b/M164_M120_LAYER0_BOARD_RESULT_01.json"
    m165_aux_path = ROOT / "deployment/mage_vl4b/M165_M120_SELECTED_W3_AUX_RESULT.json"
    m165_pkg_path = ROOT / "deployment/mage_vl4b/M165_M120_CORRECTED_LAYER0_PACKAGE_RESULT.json"
    m166_delta_path = ROOT / "deployment/mage_vl4b/M166_M120_CORRECTED_LAYER0_DELTA_RESULT.json"
    m164 = load(m164_path.relative_to(ROOT).as_posix())
    m165_aux = load(m165_aux_path.relative_to(ROOT).as_posix())
    m165_pkg = load(m165_pkg_path.relative_to(ROOT).as_posix())
    m166_delta = load(m166_delta_path.relative_to(ROOT).as_posix())
    if m164.get("status") != "FAIL" or m164.get("measurement", {}).get("fpga_execution_proved") is not True:
        raise RuntimeError("M164 identity/status mismatch")
    m164_log = ROOT / m164["uart_log"]
    if sha256(m164_log) != m164["uart_log_sha256"]:
        raise RuntimeError("M164 UART hash mismatch")
    if m165_aux.get("status") != "PASS" or m165_aux.get("auxiliary_sha256") != "7f2dfc14ae47cb537e148cafc9b1c6cc285e1fe546dec901275a4078a8458ffd":
        raise RuntimeError("M165 auxiliary identity mismatch")
    if m165_pkg.get("status") != "PASS" or m165_pkg.get("package_manifest_sha256") != "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97":
        raise RuntimeError("M165 package identity mismatch")
    if m166_delta.get("status") != "PASS" or m166_delta.get("delta_manifest_sha256") != "446a409b9a840487135c406773e044d4450b1c87e501bea6366a81daef774273":
        raise RuntimeError("M166 delta identity mismatch")

    logs = {
        "receiver": ROOT / "tmp/m166_layer0/receiver_03_uart.log",
        "stream": ROOT / "tmp/m166_layer0/stream_03_uart.log",
        "manifest": ROOT / "tmp/m166_layer0/manifest_03_uart.log",
        "stage": ROOT / "tmp/m166_layer0/stage_03_uart.log",
    }
    text = {name: path.read_text(encoding="utf-8", errors="replace") for name, path in logs.items()}
    if "M166_UART_FILE_RECEIVE_PASS" not in text["stream"] or "7f2dfc14ae47cb537e148cafc9b1c6cc285e1fe546dec901275a4078a8458ffd" not in text["stream"]:
        raise RuntimeError("M166 streamed binary proof missing")
    if "M75C_UART_PUT_FILE_PASS" not in text["manifest"] or "DELTA_MANIFEST.json 1233" not in text["manifest"]:
        raise RuntimeError("M166 delta manifest upload proof missing")
    if "sudo: a password is required" not in text["stage"] or "__M75C_UART_RC_1__" not in text["stage"]:
        raise RuntimeError("M166 authorization failure proof missing")

    control = {
        "date": "2026-09-01",
        "gate": "M166-M120-corrected-Layer0-board-stage",
        "status": "FAIL_CONTROL_AUTHORIZATION",
        "classification": "COM3 delta transfer completed and the large member was SHA-256 verified; sudo -n rejected before the atomic package applier executed.",
        "candidate_build_id": "0x4D395832",
        "delta_manifest_sha256": m166_delta["delta_manifest_sha256"],
        "target_package_manifest_sha256": m165_pkg["package_manifest_sha256"],
        "streamed_binary_bytes": 315138,
        "streamed_binary_sha256": m165_aux["auxiliary_sha256"],
        "streamed_binary_verified": True,
        "delta_manifest_uploaded": True,
        "atomic_applier_executed": False,
        "corrected_candidate_promoted": False,
        "error": "sudo: a password is required",
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "uart_logs": {name: path.relative_to(ROOT).as_posix() for name, path in logs.items()},
        "uart_log_sha256": {name: sha256(path) for name, path in logs.items()},
        "next_gate": "Refresh sudo in the same COM3 terminal, then rerun only the M166 atomic stage from the already verified remote delta.",
    }
    control_path = ROOT / "deployment/mage_vl4b/M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_03.json"
    atomic_json(control_path, control)

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M164_M120_LAYER0_FAIL_M165_IDENTITY_CORRECTED_M166_SUDO_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_layer0_board_gate"] = {
        "level": "complete-layer0",
        "gate": m164["gate"],
        "status": "FAIL",
        "candidate_build_id": "0x4D395832",
        "fpga_execution_proved": True,
        "logical_calls": 5,
        "expected_macros": 50462720,
        "all_boundaries_finite": True,
        "first_boundary_relative_l2": m164["measurement"]["metrics"]["layer00_q_input"]["relative_l2"],
        "first_boundary_cosine": m164["measurement"]["metrics"]["layer00_q_input"]["cosine"],
        "root_cause": "The fixed-text auxiliary used legacy M77 FP16 embedding rows instead of the accepted M120 W3-G64 selected rows; divergence occurs before the first FPGA linear call.",
        "formal_result": m164_path.relative_to(ROOT).as_posix(),
        "formal_result_sha256": sha256(m164_path),
        "uart_log": m164["uart_log"],
        "uart_log_sha256": m164["uart_log_sha256"],
        "evidence_level": m164["evidence_level"],
        "next_gate": "Rerun only complete Layer-0 against the corrected M165 package after M166 stage PASS.",
    }
    board["latest_m120_layer0_auxiliary_correction"] = {
        "status": "PASS_OFFLINE_CORRECTION",
        "source_checkpoint_manifest_sha256": m165_aux["source_checkpoint_manifest_sha256"],
        "source_blob_sha256": m165_aux["source_blob_sha256"],
        "embedding_policy": "M120 selected W3-G64 fixed-prompt rows",
        "auxiliary_sha256": m165_aux["auxiliary_sha256"],
        "first_boundary_precheck": m165_aux["first_boundary_precheck"],
        "corrected_package_manifest_sha256": m165_pkg["package_manifest_sha256"],
        "delta_manifest_sha256": m166_delta["delta_manifest_sha256"],
        "formal_results": [
            m165_aux_path.relative_to(ROOT).as_posix(),
            m165_pkg_path.relative_to(ROOT).as_posix(),
            m166_delta_path.relative_to(ROOT).as_posix(),
        ],
        "board_layer0_pass": False,
    }
    board["latest_m166_corrected_layer0_stage"] = {
        **control,
        "formal_result": control_path.relative_to(ROOT).as_posix(),
        "formal_result_sha256": sha256(control_path),
    }
    board["next_gate"] = control["next_gate"]
    rejected = board.setdefault("rejected_attempts", [])
    if not any(item.get("attempt") == "M164 M120 complete Layer-0 with stale M77 fixed-text auxiliary" for item in rejected):
        rejected.insert(0, {
            "attempt": "M164 M120 complete Layer-0 with stale M77 fixed-text auxiliary",
            "reason": "Real FPGA execution completed, but the pre-FPGA RMSNorm input used legacy M77 embedding rows. All seven boundaries failed the frozen numerical threshold; fixed-text remained locked. M165 replaces only this wrong identity with selected M120 W3-G64 rows.",
        })
    atomic_json(board_path, board)

    current_body = f"""## M164--M166: Layer-0 failure is isolated to stale embedding identity; corrected stage awaits sudo (2026-09-01)

- M164 executed all five real Layer-0 FPGA chains on Build `0x4D395832` (`50,462,720` expected macros); all outputs were finite, but the frozen Layer-0 acceptance failed. The first `layer00_q_input` was already at relative-L2 `{m164['measurement']['metrics']['layer00_q_input']['relative_l2']:.9f}` and cosine `{m164['measurement']['metrics']['layer00_q_input']['cosine']:.9f}` before the first FPGA linear call.
- Root cause: the M145 package reused legacy M77 FP16 fixed-prompt embedding rows, while the accepted M120 checkpoint uses W3-G64 embedding. This is an auxiliary identity error, not a T32 descriptor, DMA, weight or arithmetic failure.
- M165 extracted the exact 23 selected M120 W3-G64 rows. Its offline first-boundary precheck is relative-L2 `{m165_aux['first_boundary_precheck']['relative_l2']:.9f}`, cosine `{m165_aux['first_boundary_precheck']['cosine']:.9f}`. Corrected package manifest: `{m165_pkg['package_manifest_sha256']}`.
- M166 attempt 03 streamed the 315,138-byte replacement over COM3 and verified SHA-256 `{m165_aux['auxiliary_sha256']}`, then uploaded the complete delta manifest. `sudo -n` expired before the atomic applier ran, so no corrected candidate was promoted. Boot/DTB/CMA/partitions/services and stable rollback are unchanged.
- Next gate: refresh `sudo -v` in PuTTY/COM3, close PuTTY, finish M166 atomic staging, then rerun only the complete Layer-0 gate. Fixed-text, arbitrary prompt, video and Web remain locked.

Evidence: `{m164_path.relative_to(ROOT).as_posix()}`, `{m165_aux_path.relative_to(ROOT).as_posix()}`, `{m165_pkg_path.relative_to(ROOT).as_posix()}`, `{control_path.relative_to(ROOT).as_posix()}`."""
    milestone_body = current_body.replace("## M164--M166:", "## M164--M166：")
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M164_M166_SYNC_START -->", "<!-- M164_M166_SYNC_END -->", current_body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M164_M166_SYNC_START -->", "<!-- M164_M166_SYNC_END -->", milestone_body)
    print(json.dumps({
        "status": "PASS",
        "m164_formal_sha256": sha256(m164_path),
        "m166_control_failure_sha256": sha256(control_path),
        "board_gate_result_sha256": sha256(board_path),
    }, indent=2))
    print("M166_PREDECESSOR_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
