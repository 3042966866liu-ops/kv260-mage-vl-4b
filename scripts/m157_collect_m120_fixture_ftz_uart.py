#!/usr/bin/env python3
"""Collect corrected M139/M140 board evidence under the frozen FTZ contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "single-descriptor": {"gate": "M139-M120-COM3-single-descriptor", "descriptors": 1, "canonical": "a8b15e89c3a7edc97368a481206ed1f2ac604ce959863a6cf5d99401db959a38"},
    "single-chain": {"gate": "M140-M120-COM3-single-chain", "descriptors": 2, "canonical": "7167dff9da96757a768b44254403d1a439615fffbca3139ee5bfd261fa3c7a2d"},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=tuple(CONTRACTS), required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    expected = CONTRACTS[args.level]
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = {"date": "2026-09-01", "gate": expected["gate"], "status": "FAIL", "attempt": args.attempt}
    try:
        begin = text.rindex("__M157_RESULT_BEGIN__") + len("__M157_RESULT_BEGIN__")
        end = text.index("__M157_RESULT_END__", begin)
        measurement = json.loads(text[begin:end].strip())
        if measurement.get("status") != "PASS" or measurement.get("gate") != f"M157-M120-{args.level}-FP16-FTZ":
            raise RuntimeError(f"corrected numerical gate failed: {measurement.get('error')}")
        exact = {
            "build_id": "0x4d395832",
            "descriptor_count": expected["descriptors"],
            "canonical_output_sha256": expected["canonical"],
            "observed_output_sha256": expected["canonical"],
            "full_canonical_output_bit_exact": True,
            "tolerance_used": False,
            "fpga_transaction_executed": True,
        }
        for key, value in exact.items():
            observed = measurement.get(key)
            if key == "build_id":
                observed = str(observed).lower()
            if observed != value:
                raise RuntimeError(f"M157 {key} mismatch: {observed!r} != {value!r}")
        snapshot = measurement.get("snapshot", {})
        if int(snapshot.get("ap_return", -1)) != 0x4D395832 or not snapshot.get("mm2s_idle") or not snapshot.get("s2mm_idle") or snapshot.get("mm2s_error") or snapshot.get("s2mm_error"):
            raise RuntimeError("M157 DMA/AP completion evidence invalid")
        if "M157_M120_FIXTURE_FTZ_RUNNER_PASS" not in text:
            raise RuntimeError("M157 runner marker missing")
        result.update(
            {
                "status": "PASS",
                "candidate_build_id": "0x4d395832",
                "classification": "Real M120 packed-weight KV260 full-output gate under the predeclared deterministic FP16 FTZ contract; not a layer or full model gate.",
                "reference_contract": "FP16 subnormal-to-signed-zero; all remaining bits and padding exact; no tolerance",
                "package_manifest_sha256": "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e",
                "measurement": measurement,
                "fpga_transaction_executed": True,
                "overlay_loaded": True,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run corrected single-chain only." if args.level == "single-descriptor" else "M140 PASS unlocks M150/M154 preparation; Layer-0 still must run next.",
            }
        )
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = f"Remain at {args.level}; do not advance."
    result["uart_log"] = args.log.resolve().relative_to(ROOT).as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M157_M120_FIXTURE_FTZ_COLLECT_PASS" if result["status"] == "PASS" else "M157_M120_FIXTURE_FTZ_COLLECT_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
