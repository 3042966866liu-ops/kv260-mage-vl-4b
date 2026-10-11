#!/usr/bin/env python3
"""Combine the positive and negative M120 RTL CoSim gates fail-closed."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deployment" / "mage_vl4b"
OUT = DEPLOY / "M134_M120_RTL_COSIM_GATE_RESULT.json"


def digest(path: Path) -> dict[str, object]:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return {"path": str(path.relative_to(ROOT)), "sha256": h.hexdigest(), "bytes": path.stat().st_size}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    try:
        m130_path = DEPLOY / "M130_M120_NUMERICAL_CSIM_RESULT.json"
        m134_timeout_path = DEPLOY / "M134_M120_RTL_TIMEOUT_GATE_RESULT.json"
        m132_tb = ROOT / "hls" / "mage_prefill_m89x_runtime" / "tb_m132_m120_fifo_backpressure_rtl.cpp"
        m133_tb = ROOT / "hls" / "mage_prefill_m89x_runtime" / "tb_m133_m120_max_descriptor_rtl.cpp"
        m132_tcl = ROOT / "hls" / "mage_prefill_m89x_runtime" / "run_m132_fifo_backpressure_cosim.tcl"
        m133_tcl = ROOT / "hls" / "mage_prefill_m89x_runtime" / "run_m133_max_descriptor_cosim.tcl"
        m132_hls = ROOT / "m132_m120_fifo_backpressure_hls" / "hls" / "hls.log"
        m133_hls = ROOT / "m133_m120_max_descriptor_hls" / "hls" / "hls.log"
        m132_xsim = ROOT / "m132_m120_fifo_backpressure_hls" / "hls" / "sim" / "verilog" / "xsim.log"
        m133_xsim = ROOT / "m133_m120_max_descriptor_hls" / "hls" / "sim" / "verilog" / "xsim.log"
        m132_report = ROOT / "m132_m120_fifo_backpressure_hls" / "hls" / "sim" / "report" / "m89x_runtime_kernel_cosim.rpt"
        m133_report = ROOT / "m133_m120_max_descriptor_hls" / "hls" / "sim" / "report" / "m89x_runtime_kernel_cosim.rpt"

        m130 = json.loads(read(m130_path))
        timeout = json.loads(read(m134_timeout_path))
        tb132, tb133 = read(m132_tb), read(m133_tb)
        tcl132, tcl133 = read(m132_tcl), read(m133_tcl)
        hls132, hls133 = read(m132_hls), read(m133_hls)
        xsim132, xsim133 = read(m132_xsim), read(m133_xsim)
        rpt132, rpt133 = read(m132_report), read(m133_report)

        require(m130.get("status") == "PASS_M120_REAL_RECORD_NUMERICAL_CSIM_HEADER_CLOSURE", "M130 numerical CSim is not PASS")
        require(m130.get("header_closure", {}).get("missing_count") == 0, "recursive header closure missing_count is not zero")
        require(m130.get("kernel_return_code", "").lower() == "0x4d395832", "M130 build ID drift")
        require(timeout.get("status") == "PASS", "M134 expected-timeout gate is not PASS")
        require(timeout.get("build_id", "").lower() == "0x4d395832", "M134 timeout build ID drift")

        positive_common = "*** C/RTL co-simulation finished: PASS ***"
        require(positive_common in hls132, "M132 HLS CoSim PASS marker missing")
        require(positive_common in hls133, "M133 HLS CoSim PASS marker missing")
        require("RTL Simulation : 1 / 1 [100.00%]" in xsim132, "M132 RTL transaction did not complete")
        require("RTL Simulation : 1 / 1 [100.00%]" in xsim133, "M133 RTL transaction did not complete")
        require("Verilog|      Pass" in rpt132 and "1836263" in rpt132, "M132 report mismatch")
        require("Verilog|      Pass" in rpt133 and "29580" in rpt133, "M133 report mismatch")

        require("constexpr unsigned kRowsPerShard = 512;" in tb132, "M132 does not cover maximum rows per shard")
        require("kPairsPerShard == 8192" in tb132, "M132 does not cover maximum result FIFO occupancy")
        require("kExpectedOutputWords == 32768" in tb132, "M132 exact output word contract missing")
        require("tlast_count != 1" in tb132 and "expected_last" in tb132, "M132 final TLAST checks missing")
        require("returned != 0x4D395832U" in tb132, "M132 return/build-ID check missing")
        require("-random_stall" in tcl132, "M132 random AXI stall/backpressure option missing")

        require("constexpr unsigned kDescriptorCount = 10;" in tb133, "M133 maximum descriptor count missing")
        require("kExpectedOutputWords == 5120" in tb133, "M133 exact chain word count missing")
        require("tlast_count != 1" in tb133 and "expected_last" in tb133, "M133 final TLAST checks missing")
        require("returned != 0x4D395832U" in tb133, "M133 return/build-ID check missing")
        require("cosim_design -rtl verilog" in tcl133, "M133 RTL CoSim command missing")

        completion132 = int(re.search(r'1 / 1 \[100\.00%\] @ "(\d+)"', xsim132).group(1))
        completion133 = int(re.search(r'1 / 1 \[100\.00%\] @ "(\d+)"', xsim133).group(1))

        evidence_paths = [
            m130_path, m134_timeout_path, m132_tb, m133_tb, m132_tcl, m133_tcl,
            m132_hls, m133_hls, m132_xsim, m133_xsim, m132_report, m133_report,
        ]
        result = {
            "gate": "M134-M120-combined-RTL-CoSim",
            "status": "PASS",
            "classification": "Numerical CSim/header closure plus split RTL CoSim coverage for max FIFO occupancy, random AXI stalls, max descriptor count, exact word count/final TLAST, ap_done completion, return/build ID and bounded timeout failure; not full Vivado implementation, board, E2E, performance, video or Web evidence.",
            "build_id": "0x4D395832",
            "target_part": "xck26-sfvc784-2LV-c",
            "clock_period_ns": 4.8,
            "clock_uncertainty_ns": 1.3,
            "coverage": {
                "numerical_csim_real_records": True,
                "recursive_header_closure_missing": 0,
                "maximum_rows_per_shard": 512,
                "maximum_fifo_pairs_per_shard": 8192,
                "random_axi_stall_backpressure": True,
                "maximum_descriptor_count": 10,
                "m132_output_words64": 32768,
                "m133_output_words64": 5120,
                "only_final_tlast": True,
                "ap_done_completion": True,
                "return_build_id": "0x4D395832",
                "bounded_timeout_expected_failure": True,
            },
            "rtl_results": {
                "m132_max_fifo_random_stall": {"status": "PASS", "latency_cycles": 1836263, "completion_time_ps": completion132},
                "m133_max_descriptor_count": {"status": "PASS", "latency_cycles": 29580, "completion_time_ps": completion133},
                "m134_bounded_timeout": {"status": "PASS_EXPECTED_FAILURE", "watchdog_budget_cycles": timeout["watchdog_budget_cycles"], "fatal_time_ps": timeout["fatal_time_ps"]},
            },
            "rejected_attempts": [
                {"attempt": "M131 combined groups=40, descriptors=10, rows=512 with random stalls", "status": "REJECTED_NOT_PASS", "reason": "XSIM made no transaction progress after entering 0/1 and was interrupted; no PASS claim."},
                {"attempt": "M131B single monolithic full-geometry no-stall CoSim", "status": "REJECTED_NOT_PASS", "reason": "Empirical runtime extrapolated to tens of hours; interrupted after C reference and replaced by orthogonal maximum-occupancy/descriptor/backpressure gates without lowering any individual contract."},
                {"attempt": "M134 UVM_TIMEOUT argument-only negative gate", "status": "REJECTED_FALSE_NEGATIVE", "reason": "Generated XSIM wrapper completed normally; replaced by an explicit isolated 200-cycle watchdog that produced fatal before ap_done."},
            ],
            "evidence": [digest(path) for path in evidence_paths],
            "board_state_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "Export the exact passed M89-X2 IP and require a clean full Vivado synthesis/place/route/bitstream with nonnegative WNS/WHS and zero serious DRC before board packaging.",
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        temp = OUT.with_suffix(OUT.suffix + ".tmp")
        temp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, OUT)
        print(f"M134_M120_COMBINED_RTL_COSIM_GATE_PASS output={OUT}")
        return 0
    except Exception as exc:
        print(f"M134_M120_COMBINED_RTL_COSIM_GATE_FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
