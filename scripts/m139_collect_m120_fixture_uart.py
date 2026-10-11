#!/usr/bin/env python3
"""Collect one real M120 descriptor/chain UART gate without weakening equality."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_BUILD_ID = 0x4D395832
EXPECTED_MANIFEST = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "single-descriptor": {
        "milestone": "M139",
        "descriptor_count": 1,
        "identity": "fixture-ordinal0-layer0-family4-bits2-groups40-descriptors1",
        "input_bytes": 102416,
        "output_bytes": 4096,
        "output_sha256": "28bf653102885387d67be746eb1b417c999fe128d7c95af6bbc7635af0768350",
        "level": "L4.1 real single-descriptor numerical subgate",
        "next": "Run one real M120 single-chain gate only; Layer-0 remains locked.",
    },
    "single-chain": {
        "milestone": "M140",
        "descriptor_count": 2,
        "identity": "fixture-ordinal0-layer0-family4-bits2-groups40-descriptors2",
        "input_bytes": 102432,
        "output_bytes": 8192,
        "output_sha256": "c03f51cc7cd6d157e04bd0da674ee59652168b58473d6d3b2070f58fe30ec3a0",
        "level": "L4.2 real single-chain numerical subgate",
        "next": "Build and verify the exact M120 complete Layer-0 runtime package; do not enter fixed-text first.",
    },
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_objects(text: str) -> list[dict]:
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


def find_last(values: list[dict], gate: str) -> dict | None:
    matches = [value for value in values if value.get("gate") == gate]
    return matches[-1] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=tuple(CONTRACTS), required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    contract = CONTRACTS[args.level]
    milestone = str(contract["milestone"])
    normalized = args.level.upper().replace("-", "_")
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": f"{milestone}-M120-COM3-{args.level}",
        "status": "FAIL",
        "attempt": args.attempt,
        "candidate_build_id": f"0x{EXPECTED_BUILD_ID:08x}",
    }
    try:
        text = args.log.read_text(encoding="utf-8", errors="replace")
        values = json_objects(text)
        environment = find_last(values, "M136-M120-board-environment")
        measurement = find_last(values, f"M136-M120-{args.level}")
        if environment is None or measurement is None:
            raise RuntimeError("environment or numerical gate JSON absent from UART log")
        if environment.get("status") != "PASS":
            raise RuntimeError(f"environment preflight failed: {environment.get('error')}")
        if environment.get("package_manifest_sha256") != EXPECTED_MANIFEST:
            raise RuntimeError("environment package manifest mismatch")
        if int(environment.get("xcl_probe_count", -1)) != 1 or int(environment.get("pynq_device_count", -1)) != 1:
            raise RuntimeError("XRT/PYNQ single-device gate failed")
        if measurement.get("status") != "PASS":
            raise RuntimeError(f"numerical gate failed: {measurement.get('error')}")
        exact = {
            "identity": contract["identity"],
            "descriptor_count": contract["descriptor_count"],
            "input_bytes": contract["input_bytes"],
            "output_bytes": contract["output_bytes"],
            "output_sha256": contract["output_sha256"],
        }
        for key, expected in exact.items():
            if measurement.get(key) != expected:
                raise RuntimeError(f"{key} mismatch: observed={measurement.get(key)!r} expected={expected!r}")
        if str(measurement.get("build_id", "")).lower() != f"0x{EXPECTED_BUILD_ID:08x}".lower():
            raise RuntimeError("Build-ID mismatch")
        snapshot = measurement.get("snapshot")
        if not isinstance(snapshot, dict) or int(snapshot.get("ap_return", -1)) != EXPECTED_BUILD_ID:
            raise RuntimeError("valid AP return snapshot absent")
        if not bool(snapshot.get("mm2s_idle")) or not bool(snapshot.get("s2mm_idle")):
            raise RuntimeError("DMA not idle after gate")
        if bool(snapshot.get("mm2s_error")) or bool(snapshot.get("s2mm_error")):
            raise RuntimeError("DMA error asserted")
        if f"M136_M120_{normalized}_GATE_PASS" not in text:
            raise RuntimeError("numerical PASS marker absent")
        if f"M136_M120_{normalized}_RUNNER_PASS" not in text:
            raise RuntimeError("runner PASS marker absent")
        result.update(
            {
                "status": "PASS",
                "classification": "Real M120 packed-weight KV260 exact full-output gate; not a complete layer or model gate.",
                "evidence_level": contract["level"],
                "package_manifest_sha256": EXPECTED_MANIFEST,
                "environment": environment,
                "measurement": measurement,
                "fpga_transaction_executed": True,
                "overlay_loaded": True,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": contract["next"],
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["fpga_transaction_executed"] = None
        result["next_gate"] = f"Remain at {args.level}; do not advance to a broader gate."
    try:
        result["uart_log"] = args.log.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        result["uart_log"] = str(args.log.resolve())
    result["uart_log_sha256"] = file_sha256(args.log)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"{milestone}_M120_{normalized}_BOARD_" + ("PASS" if result["status"] == "PASS" else "FAIL"))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
