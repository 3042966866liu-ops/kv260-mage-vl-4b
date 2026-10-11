#!/usr/bin/env python3
"""Offline policy and identity gate for the M149 COM3 sequence controller."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "deployment/mage_vl4b/M149_M120_SMALL_GATE_CONTROLLER_RESULT.json"
FILES = {
    "controller": ROOT / "scripts/m149_run_m120_small_gate_sequence.ps1",
    "synchronizer": ROOT / "scripts/m149_sync_m120_small_gate_state.py",
    "build_runner": ROOT / "scripts/m138_run_m120_build_id_uart.ps1",
    "fixture_runner": ROOT / "scripts/m139_run_m120_fixture_uart.ps1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(text: str, tokens: list[str], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(f"{label} missing required tokens: {missing}")


def main() -> int:
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M149-M120-small-gate-controller-offline-readiness",
        "status": "FAIL",
        "classification": (
            "Offline controller policy/identity verification only; no COM3 command, "
            "overlay, FPGA transaction, model inference, video, or Web execution."
        ),
    }
    try:
        texts = {name: path.read_text(encoding="utf-8") for name, path in FILES.items()}
        ast.parse(texts["synchronizer"], filename=str(FILES["synchronizer"]))

        controller = texts["controller"]
        require(
            controller,
            [
                "COM3",
                "XFL1PL5N11BJB",
                "m138_run_m120_build_id_uart.ps1",
                "m139_run_m120_fixture_uart.ps1",
                "m149_sync_m120_small_gate_state.py",
                "'build-id'",
                "'single-descriptor'",
                "'single-chain'",
                "Refusing to overwrite existing formal result",
                "no broader gate ran",
            ],
            "controller",
        )
        order = [
            controller.index("-Level 'build-id'"),
            controller.index("-Level 'single-descriptor'"),
            controller.index("-Level 'single-chain'"),
        ]
        if order != sorted(order) or len(set(order)) != 3:
            raise RuntimeError("controller gate order is not Build-ID -> descriptor -> chain")
        if "ssh" in controller.lower():
            raise RuntimeError("controller contains prohibited SSH path")

        synchronizer = texts["synchronizer"]
        require(
            synchronizer,
            [
                "0x4d395832",
                "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e",
                "formal result gate identity mismatch",
                "retained UART log SHA-256 mismatch",
                "PASS reports a prohibited persistent board change",
                'board["full_model_deployed"] = False',
                'board["web_deployed"] = False',
                "atomic_json(args.board_state, board)",
                "atomic_text(args.current_state, current)",
                "atomic_text(args.milestones, milestones)",
            ],
            "synchronizer",
        )

        require(
            texts["build_runner"],
            [
                "sudo -n bash",
                "run_m120_gate.sh",
                "build-id",
                "m138_collect_m120_build_id_uart.py",
            ],
            "Build-ID runner",
        )
        require(
            texts["fixture_runner"],
            [
                "previous-level result does not authorize",
                "single-descriptor",
                "single-chain",
                "m139_collect_m120_fixture_uart.py",
            ],
            "descriptor/chain runner",
        )
        if "sudo -v" in controller or "password" in controller.lower():
            raise RuntimeError("controller attempts to acquire or handle a password")

        result.update(
            {
                "status": "PASS",
                "candidate_build_id": "0x4D395832",
                "package_manifest_sha256": (
                    "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
                ),
                "gate_order": ["build-id", "single-descriptor", "single-chain"],
                "same_terminal_noninteractive_sudo_required": True,
                "previous_level_pass_enforced": True,
                "formal_result_overwrite_refused": True,
                "uart_log_hash_reverified_before_state_sync": True,
                "failure_stops_broader_gate": True,
                "ssh_used": False,
                "board_execution_run": False,
                "board_state_changed": False,
                "full_model_deployed": False,
                "web_deployed": False,
                "files": {
                    name: {
                        "path": path.resolve().relative_to(ROOT).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                    for name, path in FILES.items()
                },
                "next_gate": (
                    "Refresh sudo in the same COM3 tty, close PuTTY, then execute the "
                    "M149 controller; the controller stops at the first failed level."
                ),
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair and rerun M149 offline verification; do not execute COM3 gates."

    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M149_M120_SMALL_GATE_CONTROLLER_OFFLINE_PASS" if result["status"] == "PASS" else "M149_M120_SMALL_GATE_CONTROLLER_OFFLINE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
