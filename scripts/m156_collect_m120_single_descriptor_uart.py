#!/usr/bin/env python3
"""Collect the bounded M156 descriptor diagnostic from its UART log."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = {
        "date": "2026-09-01",
        "gate": "M156-M120-COM3-single-descriptor-diagnostic",
        "status": "FAIL",
        "attempt": args.attempt,
        "classification": "Real-board same-descriptor numerical measurement only; no acceptance threshold and no broader gate.",
    }
    try:
        begin = text.rindex("__M156_RESULT_BEGIN__") + len("__M156_RESULT_BEGIN__")
        end = text.index("__M156_RESULT_END__", begin)
        measurement = json.loads(text[begin:end].strip())
        if measurement.get("gate") != "M156-M120-single-descriptor-difference-diagnostic":
            raise RuntimeError("M156 measurement gate mismatch")
        if measurement.get("status") != "MEASURED" or measurement.get("fpga_transaction_executed") is not True:
            raise RuntimeError(f"M156 measurement failed: {measurement.get('error')}")
        if str(measurement.get("build_id", "")).lower() != "0x4d395832":
            raise RuntimeError("M156 Build ID mismatch")
        if measurement.get("identity") != "fixture-ordinal0-layer0-family4-bits2-groups40-descriptors1":
            raise RuntimeError("M156 descriptor identity mismatch")
        if int(measurement.get("input_bytes", -1)) != 102416 or int(measurement.get("output_bytes", -1)) != 4096:
            raise RuntimeError("M156 transfer size mismatch")
        snapshot = measurement.get("snapshot", {})
        if int(snapshot.get("ap_return", -1)) != 0x4D395832:
            raise RuntimeError("M156 AP return mismatch")
        if not snapshot.get("mm2s_idle") or not snapshot.get("s2mm_idle") or snapshot.get("mm2s_error") or snapshot.get("s2mm_error"):
            raise RuntimeError("M156 DMA completion evidence invalid")
        if "M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_MEASURED" not in text or "M156_M120_SINGLE_DESCRIPTOR_RUNNER_PASS" not in text:
            raise RuntimeError("M156 completion marker missing")
        result.update(
            {
                "status": "MEASURED",
                "candidate_build_id": "0x4d395832",
                "measurement": measurement,
                "fpga_transaction_executed": True,
                "overlay_loaded": True,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Classify the exact numerical pattern and predeclare the same-descriptor repair/acceptance gate; do not run single-chain.",
            }
        )
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M156 only."
    result["uart_log"] = args.log.resolve().relative_to(ROOT).as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_COLLECT_PASS" if result["status"] == "MEASURED" else "M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_COLLECT_FAIL")
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
