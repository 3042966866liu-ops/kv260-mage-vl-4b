#!/usr/bin/env python3
"""Audit the M160 fixed-text gate and prove its Layer-0 negative lock."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = ROOT / "scripts/m160_verify_m120_layer0_predecessor.py"
RUNNER = ROOT / "scripts/m160_run_m120_fixed_text_e2e.sh"
TEXT_GATE = ROOT / "deployment/mage_vl4b/m120_text4b_layer0_board_candidate/runtime/text_e2e_gate.py"
PACKAGE_RESULT = ROOT / "deployment/mage_vl4b/M145_M120_LAYER0_BOARD_PACKAGE_RESULT.json"
RESULT = ROOT / "deployment/mage_vl4b/M160_M120_FIXED_TEXT_READINESS_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    predecessor = PREDECESSOR.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    text_gate = TEXT_GATE.read_text(encoding="utf-8")
    ast.parse(predecessor, filename=str(PREDECESSOR))
    ast.parse(text_gate, filename=str(TEXT_GATE))
    package = json.loads(PACKAGE_RESULT.read_text(encoding="utf-8"))
    require(package.get("gate") == "M145-M120-layer0-board-package" and package.get("status") == "PASS", "M145 package not ready")
    for token in (
        "M160_LOCKED_UNTIL_EXACT_M145_LAYER0_BOARD_PASS",
        'M144-M120-complete-layer0-boundary-acceptance',
        'measurement.get("build_id") != "0x4d395832"',
        'measurement.get("fpga_execution_proved") is not True',
    ):
        require(token in predecessor, f"predecessor token missing: {token}")
    for token in (
        "set -euo pipefail",
        "XILINX_XRT=/usr",
        "TMPDIR=/dev/shm",
        "/usr/local/share/pynq-venv/bin",
        "m120_board_env_preflight.py",
        "m160_verify_m120_layer0_predecessor.py",
        "text_e2e_gate.py",
        "M160_M120_FIXED_TEXT_E2E_RUNNER_PASS",
    ):
        require(token in runner, f"runner token missing: {token}")
    for forbidden in ("ssh ", "scp ", "systemctl", "reboot", "/boot", "fdisk", "parted"):
        require(forbidden not in runner, f"runner forbidden token: {forbidden}")
    require("expected_calls = 154 + 8" in text_gate, "M120 162-call contract missing")
    require('"cpu_linear_fallback": False' in text_gate, "CPU fallback prohibition missing")
    require("M120_FIXED_TEXT_E2E_PASS" in text_gate, "fixed-text PASS marker missing")

    with tempfile.TemporaryDirectory(prefix="m160_negative_") as temporary:
        absent = Path(temporary) / "absent_layer0.json"
        completed = subprocess.run(
            [
                str(Path(__import__("sys").executable)), str(PREDECESSOR),
                "--layer0-acceptance", str(absent),
                "--expected-sha256", "0" * 64,
            ],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, "M160 absent-Layer0 negative lock returned success")
        require("M160_LOCKED_UNTIL_EXACT_M145_LAYER0_BOARD_PASS" in completed.stdout, "M160 negative-lock marker missing")

    result = {
        "date": "2026-09-01",
        "gate": "M160-M120-fixed-text-offline-readiness",
        "status": "PASS",
        "classification": "Offline fixed-text source/policy audit and absent-Layer0 negative-lock PASS only; no board E2E, performance, arbitrary prompt, video or Web execution.",
        "candidate_build_id": "0x4D395832",
        "layer0_package_result_sha256": sha256(PACKAGE_RESULT),
        "predecessor_verifier_sha256": sha256(PREDECESSOR),
        "runner_sha256": sha256(RUNNER),
        "text_gate_sha256": sha256(TEXT_GATE),
        "absent_layer0_negative_lock_test": "PASS",
        "layer0_gate_precedes_overlay_execution": True,
        "fixed_prompt_tokens": 30,
        "generated_tokens": 1,
        "expected_logical_calls": 162,
        "cpu_linear_fallback": False,
        "weight_mode": "staged-low-cma",
        "board_execution_run": False,
        "next_gate": "Execute only after exact M145 Layer-0 real-board PASS; on failure debug and rerun fixed text only.",
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(RESULT)
    print(json.dumps(result, indent=2))
    print("M160_M120_FIXED_TEXT_READINESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
