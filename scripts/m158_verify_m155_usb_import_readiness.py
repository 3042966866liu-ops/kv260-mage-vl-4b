#!/usr/bin/env python3
"""Fail-closed offline readiness audit for the M155 USB board import."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "scripts/m155_m120_usb_board_import.py"
RUNNER = ROOT / "scripts/m155_run_m120_usb_board_import.sh"
M140 = ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json"
RESULT = ROOT / "deployment/mage_vl4b/M158_M155_USB_IMPORT_READINESS_RESULT.json"

EXPECTED_BUILD = "0x4d395832"
EXPECTED_PACKAGE = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
EXPECTED_M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"


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
    importer = IMPORTER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    ast.parse(importer, filename=str(IMPORTER))
    m140 = json.loads(M140.read_text(encoding="utf-8"))
    require(m140.get("gate") == "M140-M120-COM3-single-chain", "M140 gate mismatch")
    require(m140.get("status") == "PASS", "M140 is not PASS")
    require(str(m140.get("candidate_build_id", "")).lower() == EXPECTED_BUILD, "M140 Build ID mismatch")
    require(m140.get("package_manifest_sha256") == EXPECTED_PACKAGE, "M140 package mismatch")
    require(m140.get("fpga_transaction_executed") is True, "M140 lacks real FPGA transaction")
    require(m140.get("stable_rollback_preserved") is True, "M140 stable rollback missing")
    require(sha256(M140) == EXPECTED_M140_SHA, "M140 formal-result hash mismatch")

    for token in (
        'EXPECTED_PAYLOAD_BYTES = 2_035_472_384',
        'EXPECTED_FILE_COUNT = 10',
        'require_read_only_mount(source)',
        'if os.geteuid() != 0',
        'if destination.exists() or staging.exists()',
        'os.replace(staging, destination)',
        '"boot_dtb_cma_partitions_services_changed": False',
        '"stable_rollback_preserved": True',
        'M145 complete Layer-0 only',
    ):
        require(token in importer, f"importer policy token missing: {token}")
    require("subprocess" not in importer and "shell=True" not in importer, "importer contains shell escape")

    first_nonblank = next(line for line in runner.splitlines() if line.strip())
    require(first_nonblank == "#!/usr/bin/env bash", "runner shebang mismatch")
    for token in (
        "set -euo pipefail",
        "bootstrap=$root/m155_bootstrap",
        "lsblk -nrpo NAME,TYPE,TRAN,FSTYPE",
        'mount -o ro,nodev,nosuid,noexec',
        'trap - EXIT',
        'exit "$rc"',
        'M155_M120_USB_BOARD_IMPORT_RUNNER_PASS',
    ):
        require(token in runner, f"runner policy token missing: {token}")
    for forbidden in ("ssh ", "scp ", "systemctl", "reboot", "fw_setenv", "/boot", "fdisk", "parted"):
        require(forbidden not in runner, f"runner forbidden token present: {forbidden}")

    result = {
        "date": "2026-09-01",
        "gate": "M158-M155-USB-board-import-offline-readiness",
        "status": "PASS",
        "classification": "Offline syntax, identity and fail-closed policy audit only; no USB write, COM3 transfer, mount, board import, overlay or FPGA transaction.",
        "candidate_build_id": "0x4D395832",
        "m140_formal_result": str(M140.relative_to(ROOT)).replace("\\", "/"),
        "m140_formal_result_sha256": sha256(M140),
        "importer": str(IMPORTER.relative_to(ROOT)).replace("\\", "/"),
        "importer_sha256": sha256(IMPORTER),
        "runner": str(RUNNER.relative_to(ROOT)).replace("\\", "/"),
        "runner_sha256": sha256(RUNNER),
        "source_mount_required_read_only": True,
        "unique_usb_partition_required": True,
        "source_and_destination_hash_closure": True,
        "payload_bytes": 2_035_472_384,
        "file_count": 10,
        "atomic_destination_promotion": True,
        "root_required": True,
        "exit_code_preserved_after_unmount": True,
        "boot_dtb_cma_partitions_services_changed": False,
        "board_execution_run": False,
        "next_gate": "After M150 USB PASS, stage this fixed bootstrap over COM3, insert the USB into KV260, refresh same-terminal sudo, and execute M155 once.",
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(RESULT)
    print(json.dumps(result, indent=2))
    print("M158_M155_USB_IMPORT_READINESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
