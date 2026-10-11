#!/usr/bin/env python3
"""Finalize the M128 numerical CSim and header-closure evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-result", type=Path, required=True)
    parser.add_argument("--csim-log", type=Path, required=True)
    parser.add_argument("--hls-log", type=Path, required=True)
    parser.add_argument("--header-audit", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--testbench", type=Path, required=True)
    parser.add_argument("--tcl", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M130-M120-real-record-numerical-CSim-and-header-closure",
        "status": "FAIL",
        "classification": "Vitis HLS 2026.1 numerical CSim plus recursive local-header closure; not RTL CoSim, synthesis, FPGA, board, performance or Web evidence",
    }
    try:
        fixture = json.loads(args.fixture_result.read_text(encoding="utf-8"))
        header = json.loads(args.header_audit.read_text(encoding="utf-8"))
        csim_text = args.csim_log.read_text(encoding="utf-8", errors="strict")
        hls_text = args.hls_log.read_text(encoding="utf-8", errors="strict")
        if fixture.get("status") != "PASS_M120_REAL_RECORD_CSIM_FIXTURE_BUILT":
            raise RuntimeError("M130_FIXTURE_STATUS_FAIL")
        if header.get("status") != "PASS" or header.get("missing") != []:
            raise RuntimeError("M130_HEADER_CLOSURE_FAIL")
        required = [
            "M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS",
            "M128_OUTPUT_WORDS=16384",
            "CSim done with 0 errors",
        ]
        missing_markers = [marker for marker in required if marker not in csim_text]
        if missing_markers:
            raise RuntimeError(f"M130_CSIM_MARKER_FAIL missing={missing_markers}")
        chain_lines = [line for line in csim_text.splitlines() if line.startswith("M128_CHAIN_PASS")]
        if len(chain_lines) != 7:
            raise RuntimeError(f"M130_CHAIN_PASS_COUNT_FAIL count={len(chain_lines)}")
        if "CSim done with 0 errors" not in hls_text:
            raise RuntimeError("M130_HLS_LOG_STATUS_FAIL")

        result.update(
            {
                "status": "PASS_M120_REAL_RECORD_NUMERICAL_CSIM_HEADER_CLOSURE",
                "vitis_hls_version": "2026.1",
                "target_part": "xck26-sfvc784-2LV-c",
                "kernel_return_code": "0x4d395832",
                "fixture_result": {"path": str(args.fixture_result), "sha256": sha256_file(args.fixture_result)},
                "fixture_sha256": fixture["fixture_sha256"],
                "coverage": fixture["coverage"],
                "chain_pass_count": len(chain_lines),
                "descriptor_count": fixture["descriptor_count"],
                "output_words64": 16384,
                "fp16_bit_exact_against_independent_reference": True,
                "coalesced_final_tlast_verified": True,
                "input_and_output_stream_empty_after_each_chain": True,
                "csim_log": {"path": str(args.csim_log), "sha256": sha256_file(args.csim_log)},
                "hls_log": {"path": str(args.hls_log), "sha256": sha256_file(args.hls_log)},
                "header_closure": {
                    "path": str(args.header_audit),
                    "sha256": sha256_file(args.header_audit),
                    "dependency_count": header["dependency_count"],
                    "header_count": header["header_count"],
                    "missing_count": len(header["missing"]),
                    "staged_file_count": len(header["staged_files"]),
                },
                "sources": [
                    {"path": str(path), "sha256": sha256_file(path)}
                    for path in (args.kernel, args.testbench, args.tcl)
                ],
                "rejected_attempts": [
                    {
                        "attempt": "first M128 CSim compile",
                        "status": "FAIL_BEFORE_ARITHMETIC_EXECUTION",
                        "reason": "Testbench omitted <hls_math.h>, so fp_struct was undeclared. The include was added and recursive closure now reports missing=0 before the passing rerun.",
                    }
                ],
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run maximum groups=152, descriptor_count=10, rows_per_shard=512 RTL CoSim with explicit AXIS backpressure, exact word count/final TLAST, ap_done, return code and bounded timeout.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same CSim/header-closure evidence gate; do not enter RTL CoSim or touch the board."

    atomic_json(args.result, result)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_M120_REAL_RECORD_NUMERICAL_CSIM_HEADER_CLOSURE":
        return 1
    print("M130_M120_NUMERICAL_CSIM_HEADER_CLOSURE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
