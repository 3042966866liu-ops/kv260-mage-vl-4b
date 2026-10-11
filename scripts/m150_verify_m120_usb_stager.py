#!/usr/bin/env python3
"""Offline fail-closed verification for the M150 removable-drive stager."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGER = ROOT / "scripts/m150_stage_m120_fulltext_usb.py"
OUTPUT = ROOT / "deployment/mage_vl4b/M150_M120_USB_STAGER_READINESS_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M150-M120-fulltext-USB-stager-offline-readiness",
        "status": "FAIL",
        "classification": "Offline source/policy inspection plus negative lock test; no USB write or board action.",
    }
    try:
        source = STAGER.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(STAGER))
        required = [
            "M150_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS",
            "M140-M120-COM3-single-chain",
            "0x4d395832",
            "Ubuntu-24.04",
            "DRIVE_REMOVABLE=2",
            "workspace/system drive is prohibited",
            "insufficient USB free bytes",
            "source SHA-256 mismatch during copy",
            "destination SHA-256 mismatch after copy",
            "refusing existing path",
            "USB_PAYLOAD_MANIFEST.json",
            "USB_READY.json",
            "os.replace(staging, final)",
        ]
        missing = [token for token in required if token not in source]
        if missing:
            raise RuntimeError(f"required fail-closed controls missing: {missing}")
        if "ssh" in source.lower() or "remove(" in source or "rmtree" in source:
            raise RuntimeError("prohibited SSH or destructive cleanup path present")
        if source.index("m140, m140_sha = require_m140") >= source.index(
            "drive_root, drive_type, free_before = removable_root"
        ):
            raise RuntimeError("drive inspection occurs before the M140 lock")

        constants: dict[str, object] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                try:
                    constants[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        if constants.get("EXPECTED_PAYLOAD_BYTES") != 2_035_472_384:
            raise RuntimeError("payload byte constant mismatch")
        if constants.get("EXPECTED_FREE_BYTES") != 2_102_581_248:
            raise RuntimeError("free-space constant mismatch")

        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("m150_stager_lock_test", STAGER)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load M150 stager for negative lock test")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        absent = ROOT / "tmp/m150_deliberately_absent_m140_result.json"
        if absent.exists():
            raise RuntimeError("negative-lock sentinel path unexpectedly exists")
        try:
            module.require_m140(absent)
        except RuntimeError as exc:
            if str(exc) != "M150_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS":
                raise RuntimeError(f"unexpected negative-lock error: {exc}") from exc
        else:
            raise RuntimeError("M150 negative lock unexpectedly accepted absent M140")

        result.update(
            {
                "status": "PASS",
                "stager": "scripts/m150_stage_m120_fulltext_usb.py",
                "stager_sha256": sha256(STAGER),
                "m140_pass_required_before_drive_inspection": True,
                "absent_m140_negative_lock_test": "PASS",
                "exact_wsl_distro_required": "Ubuntu-24.04",
                "destination_must_be_drive_root": True,
                "destination_must_be_removable": True,
                "workspace_drive_prohibited": True,
                "minimum_free_bytes": 2_102_581_248,
                "source_and_destination_rehash": True,
                "partial_then_atomic_promotion": True,
                "overwrite_refused": True,
                "destructive_cleanup_present": False,
                "usb_write_run": False,
                "board_state_changed": False,
                "next_gate": "Wait for real M140 PASS; then identify the exact removable-drive root and run M150 once.",
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair M150 offline controls; do not write a USB drive."
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M150_M120_USB_STAGER_READINESS_PASS" if result["status"] == "PASS" else "M150_M120_USB_STAGER_READINESS_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
