#!/usr/bin/env python3
"""Convert one M120 Build-ID UART log into fail-closed local board evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_BUILD_ID = 0x4D395832
EXPECTED_MANIFEST = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def objects_in(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    values: list[dict] = []
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def last_gate(values: list[dict], gate: str) -> dict | None:
    matches = [value for value in values if value.get("gate") == gate]
    return matches[-1] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M138-M120-COM3-build-id",
        "status": "FAIL",
        "attempt": args.attempt,
        "candidate_build_id": f"0x{EXPECTED_BUILD_ID:08x}",
    }
    try:
        text = args.log.read_text(encoding="utf-8", errors="replace")
        values = objects_in(text)
        environment = last_gate(values, "M136-M120-board-environment")
        measurement = last_gate(values, "M136-M120-build-id-minimal")
        if environment is None or measurement is None:
            raise RuntimeError("environment or Build-ID JSON absent from UART log")
        if environment.get("status") != "PASS":
            raise RuntimeError(f"environment preflight failed: {environment.get('error')}")
        if environment.get("package_manifest_sha256") != EXPECTED_MANIFEST:
            raise RuntimeError("environment package manifest mismatch")
        if int(environment.get("xcl_probe_count", -1)) != 1:
            raise RuntimeError("XRT probe count is not one")
        if int(environment.get("pynq_device_count", -1)) != 1:
            raise RuntimeError("PYNQ device count is not one")
        if measurement.get("status") != "PASS":
            raise RuntimeError(f"Build-ID gate failed: {measurement.get('error')}")
        if str(measurement.get("build_id", "")).lower() != f"0x{EXPECTED_BUILD_ID:08x}".lower():
            raise RuntimeError("Build-ID mismatch")
        if int(measurement.get("input_bytes", -1)) != 2576:
            raise RuntimeError("unexpected smallest-transaction input byte count")
        if int(measurement.get("output_bytes", -1)) != 4096:
            raise RuntimeError("unexpected smallest-transaction output byte count")
        snapshot = measurement.get("snapshot")
        if not isinstance(snapshot, dict):
            raise RuntimeError("transaction snapshot absent")
        if int(snapshot.get("ap_return", -1)) != EXPECTED_BUILD_ID:
            raise RuntimeError("AP return Build-ID mismatch")
        if not bool(snapshot.get("mm2s_idle")) or not bool(snapshot.get("s2mm_idle")):
            raise RuntimeError("DMA not idle after transaction")
        if bool(snapshot.get("mm2s_error")) or bool(snapshot.get("s2mm_error")):
            raise RuntimeError("DMA error asserted")
        if "M136_M120_BUILD_ID_GATE_PASS" not in text or "M136_M120_BUILD_ID_RUNNER_PASS" not in text:
            raise RuntimeError("required gate/runner PASS marker absent")
        result.update(
            {
                "status": "PASS",
                "classification": "Real KV260 smallest legal zero-data FPGA transaction; proves M120/M89X2 Build ID, DMA forward progress and zero-output contract only.",
                "evidence_level": "L4 Build-ID subgate",
                "package_manifest_sha256": EXPECTED_MANIFEST,
                "environment": environment,
                "measurement": measurement,
                "fpga_transaction_executed": True,
                "overlay_loaded": True,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run one real M120 single-descriptor gate only; single-chain remains locked until that PASS.",
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["fpga_transaction_executed"] = None
        result["next_gate"] = "Remain at Build-ID level; inspect the retained UART log and do not run descriptor/chain."
    try:
        result["uart_log"] = args.log.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        result["uart_log"] = str(args.log.resolve())
    result["uart_log_sha256"] = sha256(args.log)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M138_M120_BUILD_ID_BOARD_PASS" if result["status"] == "PASS" else "M138_M120_BUILD_ID_BOARD_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
