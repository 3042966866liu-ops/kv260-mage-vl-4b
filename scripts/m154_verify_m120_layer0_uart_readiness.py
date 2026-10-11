#!/usr/bin/env python3
"""Independently verify the fail-closed M154 Layer-0 UART staging path."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_RESULT = ROOT / "deployment/mage_vl4b/M154_M120_LAYER0_UART_ARCHIVE_RESULT.json"
M145_MANIFEST = ROOT / "deployment/mage_vl4b/m120_text4b_layer0_board_candidate/PACKAGE_MANIFEST.json"
WRAPPER = ROOT / "scripts/m154_stage_m120_layer0_uart.ps1"
STAGER = ROOT / "scripts/m154_uart_layer0_package_stager.py"
M140 = ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json"
RESULT = ROOT / "deployment/mage_vl4b/M154_M120_LAYER0_UART_READINESS_RESULT.json"
EXPECTED_MANIFEST = "732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13"
TOP = "m120_text4b_layer0_board_candidate"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    archive_result = json.loads(ARCHIVE_RESULT.read_text(encoding="utf-8"))
    manifest = json.loads(M145_MANIFEST.read_text(encoding="utf-8"))
    archive = ROOT / archive_result["archive"]
    require(archive_result["status"] == "PASS", "archive result is not PASS")
    require(archive_result["build_id"] == "0x4D395832", "archive Build ID mismatch")
    require(archive_result["package_manifest_sha256"] == EXPECTED_MANIFEST, "archive manifest identity mismatch")
    require(sha256(M145_MANIFEST) == EXPECTED_MANIFEST, "M145 manifest drift")
    require(archive.stat().st_size == archive_result["archive_bytes"], "archive byte count mismatch")
    require(sha256(archive) == archive_result["archive_sha256"], "archive hash mismatch")

    expected = {f"{TOP}/PACKAGE_MANIFEST.json", *(f"{TOP}/{item['path']}" for item in manifest["files"])}
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        actual = {member.name for member in members}
        require(len(actual) == len(members), "archive contains duplicate member names")
        require(actual == expected, "archive member closure mismatch")
        for member in members:
            parts = PurePosixPath(member.name).parts
            require(member.isfile(), f"non-file archive member: {member.name}")
            require(parts and parts[0] == TOP and ".." not in parts, f"unsafe archive member: {member.name}")

    wrapper = WRAPPER.read_text(encoding="utf-8")
    stager = STAGER.read_text(encoding="utf-8")
    m140_guard = wrapper.index("if (-not (Test-Path -LiteralPath $m140Path))")
    first_serial_access = min(wrapper.index("Get-CimInstance"), wrapper.index("[IO.Ports.SerialPort]"))
    require(m140_guard < first_serial_access, "M140 guard does not precede COM3 access")
    require("M154_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS" in wrapper, "missing M140 fail-closed marker")
    require("M140-M120-COM3-single-chain" in wrapper and "0x4d395832" in wrapper, "M140 identity check missing")
    require("XFL1PL5N11BJB" in wrapper and "COM3" in wrapper, "fixed COM3/FTDI identity missing")
    require(not re.search(r"\bssh(?:\.exe)?\b|\bscp(?:\.exe)?\b", wrapper, re.IGNORECASE), "SSH/SCP is prohibited")
    require("if (Test-Path -LiteralPath $log)" in wrapper, "UART log overwrite guard missing")
    require("output.exists() or staging.exists()" in stager, "board destination overwrite guard missing")
    require("os.replace(staging, output)" in stager, "atomic board promotion missing")
    require("base64.b64decode" in stager and "validate=True" in stager, "strict base64 validation missing")
    require("archive hash mismatch" in stager and "manifest hash mismatch" in stager, "payload identity checks missing")

    negative_lock_observed = None
    if not M140.exists():
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WRAPPER),
                "-Attempt",
                "01",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        require(completed.returncode != 0, "M154 negative lock unexpectedly returned success")
        require(
            "M154_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS" in completed.stdout,
            "M154 negative lock marker was not observed",
        )
        negative_lock_observed = True

    result = {
        "date": "2026-09-01",
        "gate": "M154-M120-Layer0-UART-readiness",
        "status": "PASS",
        "classification": "Offline archive and fail-closed UART staging readiness only; not a transfer or board gate.",
        "build_id": "0x4D395832",
        "package_manifest_sha256": EXPECTED_MANIFEST,
        "archive_sha256": archive_result["archive_sha256"],
        "archive_bytes": archive_result["archive_bytes"],
        "archive_member_count": len(expected),
        "m140_real_board_result_present": M140.exists(),
        "negative_lock_expected_now": not M140.exists(),
        "negative_lock_observed": negative_lock_observed,
        "checks": {
            "archive_hash_and_closure": "PASS",
            "safe_regular_members_only": "PASS",
            "m140_gate_precedes_com3": "PASS",
            "fixed_com3_ftdi": "PASS",
            "no_ssh_or_scp": "PASS",
            "no_overwrite": "PASS",
            "strict_payload_and_manifest_hashes": "PASS",
            "atomic_board_promotion": "PASS",
        },
        "board_state_changed": False,
        "next_action": "Run M149 after same-COM3 sudo refresh; M154 remains locked until M140 PASS.",
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M154_M120_LAYER0_UART_READINESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
