#!/usr/bin/env python3
"""Verify the clean M159 M155-bootstrap archive and COM3 staging policy."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_RESULT = ROOT / "deployment/mage_vl4b/M159_M155_BOOTSTRAP_UART_ARCHIVE_RESULT.json"
STAGER = ROOT / "scripts/m159_uart_m155_bootstrap_stager.py"
WRAPPER = ROOT / "scripts/m159_stage_m155_bootstrap_uart.ps1"
RESULT = ROOT / "deployment/mage_vl4b/M159_M155_BOOTSTRAP_UART_READINESS_RESULT.json"


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
    archive_result = json.loads(ARCHIVE_RESULT.read_text(encoding="utf-8"))
    require(archive_result.get("gate") == "M159-M155-bootstrap-UART-archive", "archive gate mismatch")
    require(archive_result.get("status") == "PASS", "archive is not PASS")
    archive = ROOT / archive_result["archive"]
    require(sha256(archive) == archive_result["archive_sha256"], "archive hash mismatch")
    stager = STAGER.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    ast.parse(stager, filename=str(STAGER))
    for token in (
        'sha256(Path(__file__)) != args.self_sha256',
        'output.parent != allowed_parent',
        'if output.exists() or staging.exists()',
        'base64.b64decode("".join(encoded), validate=True)',
        'os.replace(staging, output)',
        'M159_M155_BOOTSTRAP_UART_STAGE_PASS',
    ):
        require(token in stager, f"stager policy token missing: {token}")
    for token in (
        "M159_LOCKED_UNTIL_EXACT_M140_PASS",
        "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb",
        "ExpectedFtdiSerial = 'XFL1PL5N11BJB'",
        "M159_COM3_IDENTITY_FAIL",
        "__M159_M155_BOOTSTRAP_EOF__",
        "M159_M155_BOOTSTRAP_UART_STAGE_CLIENT_PASS",
    ):
        require(token in wrapper, f"wrapper policy token missing: {token}")
    require("ssh" not in wrapper.lower() and "scp" not in wrapper.lower(), "SSH path present")
    result = {
        "date": "2026-09-01",
        "gate": "M159-M155-bootstrap-UART-readiness",
        "status": "PASS",
        "classification": "Offline deterministic bootstrap archive and COM3 stager readiness only; no COM3 transfer, USB mount, board import, overlay or FPGA transaction.",
        "candidate_build_id": "0x4D395832",
        "archive_result": str(ARCHIVE_RESULT.relative_to(ROOT)).replace("\\", "/"),
        "archive_result_sha256": sha256(ARCHIVE_RESULT),
        "archive_sha256": archive_result["archive_sha256"],
        "archive_bytes": archive_result["archive_bytes"],
        "package_manifest_sha256": archive_result["package_manifest_sha256"],
        "member_count": archive_result["member_count"],
        "stager_sha256": sha256(STAGER),
        "wrapper_sha256": sha256(WRAPPER),
        "exact_m140_predecessor_required": True,
        "fixed_com3_ftdi_identity": True,
        "self_archive_manifest_and_member_hashes_verified": True,
        "existing_destination_refused": True,
        "atomic_board_promotion": True,
        "ssh_used": False,
        "transfer_run": False,
        "board_state_changed": False,
        "next_gate": "Wait for M150 USB PASS, then run M159 over COM3 before M155 board import.",
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(RESULT)
    print(json.dumps(result, indent=2))
    print("M159_M155_BOOTSTRAP_UART_READINESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
