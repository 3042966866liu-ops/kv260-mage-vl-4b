#!/usr/bin/env python3
"""Record and synchronize the fail-closed M186 board environment result."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
LOG_REL = "tmp/m186_ps_vision/run_01_uart.log"
RESULT_REL = "deployment/mage_vl4b/M186_M181_PS_VISION_BOARD_RESULT_01.json"
LOG_SHA = "d93d3948632443d58ca9a6d09c58a3f843167e39c0c73359d79395755fde4d11"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M184_SHA = "790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84"


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
    log_path = ROOT / LOG_REL
    result_path = ROOT / RESULT_REL
    if digest(log_path) != LOG_SHA:
        raise RuntimeError("M187 exact M186 UART log mismatch")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    if text.count("ModuleNotFoundError: No module named 'torch'") != 3:
        raise RuntimeError("M187 expected three fixed-environment torch failures")
    for marker in ("M186_AARCH64_TORCH_ENVIRONMENT_NOT_FOUND", "__M186_PS_VISION_RUNNER_RC_1__", "__M75C_UART_RC_1__"):
        if text.count(marker) != 1:
            raise RuntimeError(f"M187 missing/duplicate marker: {marker}")
    if "M186_M181_PS_VISION_BOARD_PASS" in text or "__M186_PS_VISION_RESULT_BEGIN__" in text:
        raise RuntimeError("M187 contradictory numerical execution marker")
    if result_path.exists():
        raise RuntimeError("M187 requires absent formal M186 result")
    result = {
        "date": "2026-09-01",
        "gate": "M186-M181-fixed-four-frame-PS-vision-board-environment-preflight",
        "status": "FAIL_ENVIRONMENT_PREFLIGHT",
        "classification": "Real-KV260 environment failure before any PS vision or FPGA language computation.",
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": PACKAGE_SHA,
        "m184_formal_result_sha256": M184_SHA,
        "checked_python_environments": [
            "/usr/bin/python3",
            "/usr/local/share/pynq-venv/bin/python3",
            "/usr/local/share/pynq-venv/bin/python",
        ],
        "observed_error": "ModuleNotFoundError: No module named 'torch'",
        "ps_vision_executed": False,
        "fpga_language_executed": False,
        "web_deployed": False,
        "board_package_remains_hash_verified": True,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "uart_log": LOG_REL,
        "uart_log_sha256": LOG_SHA,
        "next_gate": "Inventory existing ARM64 inference runtimes and local offline ARM64 packages once; repair only the PS-vision runtime dependency before rerunning M186.",
        "scope_boundary": "This does not reject M120 FPGA text language/head or M181 weights; it rejects only the current board PyTorch assumption.",
    }
    atomic_json(result_path, result)
    result_sha = digest(result_path)
    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    imported = board.get("latest_m120_video_board_import", {})
    if imported.get("formal_result_sha256") != M184_SHA or imported.get("package_manifest_sha256") != PACKAGE_SHA:
        raise RuntimeError("M187 authoritative M184 predecessor mismatch")
    board["status"] = "M186_M120_VIDEO_PS_VISION_BLOCKED_MISSING_ARM64_TORCH"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_video_ps_vision_board_gate"] = {**result, "formal_result": RESULT_REL, "formal_result_sha256": result_sha}
    board["next_gate"] = result["next_gate"]
    atomic_json(board_path, board)
    body = f"""## M186/M187: fixed four-frame PS vision stops at board environment preflight (2026-09-01)

- The exact M181 package remains atomically present and hash-verified on the KV260. M186 did not reach weight decode, visual arithmetic, FPGA language execution or Web startup.
- A single versioned preflight checked `/usr/bin/python3`, `/usr/local/share/pynq-venv/bin/python3` and `/usr/local/share/pynq-venv/bin/python`; each failed with `ModuleNotFoundError: No module named 'torch'`.
- Therefore the current video assumption—PS BF16/W4 visual tower implemented with board-side PyTorch—is not executable on this Linux image. This is an environment/runtime dependency failure, not evidence that the 4B weights, M120 text FPGA path or board hardware are wrong.
- The run failed closed with no boot, DTB, CMA, partition, service or stable rollback change. `full_model_deployed=false` and `web_deployed=false` remain authoritative.
- Next: perform one bounded ARM64 runtime/offline-package inventory, then either stage a compatible local ARM64 runtime or replace only the visual execution backend; do not rerun M186 unchanged.

Evidence: `{RESULT_REL}` (SHA-256 `{result_sha}`), UART log SHA-256 `{LOG_SHA}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M186_PS_VISION_ENV_FAIL_START -->", "<!-- M186_PS_VISION_ENV_FAIL_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M186_PS_VISION_ENV_FAIL_START -->", "<!-- M186_PS_VISION_ENV_FAIL_END -->", body.replace("## M186/M187:", "## M186/M187："))
    print(json.dumps({"status": "PASS", "m186_result_sha256": result_sha, "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M187_M186_ENVIRONMENT_FAILURE_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
