#!/usr/bin/env python3
"""Bind the implemented T32 resource report to the board-executed BACT build."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re


EXPECTED_HASHES = {
    "implementation": "76451300b7f3a7005528ec6a8166ab3d38dfa83dc9f81257c4f5fb4bbfb673e7",
    "board": "1a8138f92fc9340b1e5c660f886729cd725280d29877863af54cdd12aef895d1",
    "cost_model": "74b2205f532ab63caf623c1da5af2dbf0cb7e24214bdc9650a487f794debfbb2",
    "utilization_report": "5d0c816168b141495afe18e04a5266260adb8693b14388fb2de67ab3eb3a16cb",
    "timing_report": "5503908e200beee1830fc82f75e5e5391e0e2846b5be73882e4869dfe291859f",
}

RESOURCE_NAMES = {
    "CLB LUTs": "clb_luts",
    "CLB Registers": "clb_registers",
    "Block RAM Tile": "block_ram_tiles",
    "URAM": "uram",
    "DSPs": "dsps",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_hash(name: str, path: Path) -> None:
    observed = digest(path)
    expected = EXPECTED_HASHES[name]
    if observed != expected:
        raise RuntimeError(f"M300_HASH_FAIL name={name} expected={expected} observed={observed}")


def parse_utilization(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="strict")
    resources = {}
    for display_name, key in RESOURCE_NAMES.items():
        pattern = re.compile(
            rf"^\|\s*{re.escape(display_name)}\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|$",
            re.MULTILINE,
        )
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"M300_RESOURCE_PARSE_FAIL resource={display_name}")
        used = int(match.group(1))
        available = int(match.group(2))
        reported_percent = float(match.group(3))
        computed_percent = used / available * 100.0
        if not math.isclose(computed_percent, reported_percent, rel_tol=0.0, abs_tol=0.01):
            raise RuntimeError(f"M300_RESOURCE_PERCENT_FAIL resource={display_name}")
        resources[key] = {
            "used": used,
            "available": available,
            "headroom": available - used,
            "reported_utilization_percent": reported_percent,
            "computed_utilization_percent": computed_percent,
        }
    return resources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    paths = {
        "implementation": root / "deployment/mage_vl4b/M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json",
        "board": root / "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
        "cost_model": root / "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
        "utilization_report": root / "deployment/mage_vl4b/m120_m89x2_board_candidate/full_shell_reports/impl_utilization.rpt",
        "timing_report": root / "deployment/mage_vl4b/m120_m89x2_board_candidate/full_shell_reports/impl_timing_summary.rpt",
    }
    for name, path in paths.items():
        verify_hash(name, path)

    implementation = json.loads(paths["implementation"].read_text(encoding="utf-8"))
    board = json.loads(paths["board"].read_text(encoding="utf-8"))
    cost = json.loads(paths["cost_model"].read_text(encoding="utf-8"))
    if implementation["status"] != "PASS":
        raise RuntimeError("M300_IMPLEMENTATION_GATE_FAIL")
    if board["status"] != "PASS_COUNTERBALANCED_PILOT":
        raise RuntimeError("M300_BOARD_GATE_FAIL")
    if cost["status"] != "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL":
        raise RuntimeError("M300_COST_MODEL_GATE_FAIL")
    build_ids = {
        implementation["build_id"].lower(),
        board["build_id"].lower(),
        cost["board_identity"]["build_id"].lower(),
    }
    if len(build_ids) != 1:
        raise RuntimeError("M300_BUILD_ID_BINDING_FAIL")

    resources = parse_utilization(paths["utilization_report"])
    for key, observed in implementation["resources"].items():
        if resources[key]["used"] != observed:
            raise RuntimeError(f"M300_IMPLEMENTATION_RESOURCE_BINDING_FAIL resource={key}")
    timing = implementation["timing"]
    if timing["wns_ns"] <= 0 or timing["whs_ns"] < 0 or implementation["routing"]["routing_error_nets"] != 0:
        raise RuntimeError("M300_TIMING_OR_ROUTING_FAIL")
    if implementation["serious_drc_count"] != 0:
        raise RuntimeError("M300_DRC_FAIL")

    result = {
        "date": "2026-09-03",
        "gate": "M300-BACT-build-resource-and-board-identity-binding",
        "status": "PASS_IMPLEMENTED_RESOURCES_BOUND_TO_BOARD_EXECUTED_BUILD",
        "classification": (
            "The routed T32 full-shell utilization/timing reports and the 27-point KV260 execution share exact "
            "Build ID 0x4D395832. This proves implementation resources and execution identity, not dynamic power, "
            "semantic accuracy, BACT causal speed, Web promotion or real-time performance."
        ),
        "build_id": board["build_id"],
        "kernel": board["kernel"],
        "implementation": {
            "wns_ns": timing["wns_ns"],
            "whs_ns": timing["whs_ns"],
            "tns_ns": timing["tns_ns"],
            "ths_ns": timing["ths_ns"],
            "fully_routed_nets": implementation["routing"]["fully_routed_nets"],
            "routing_error_nets": implementation["routing"]["routing_error_nets"],
            "serious_drc_count": implementation["serious_drc_count"],
            "resources": resources,
        },
        "board_execution_binding": {
            "runtime_load_count": board["runtime_load_count"],
            "vision_execution_count": board["vision_execution_count"],
            "completed_measurements": board["completed_measurements"],
            "expected_measurements": board["expected_measurements"],
            "expected_logical_fpga_calls_including_warmup": board["expected_total_logical_fpga_calls_including_warmup"],
            "observed_logical_fpga_calls_including_warmup": board["observed_total_logical_fpga_calls_including_warmup"],
            "all_outputs_finite": all(row["finite"] for row in board["records"]),
        },
        "bact_incremental_pl_resources": {
            "clb_luts": 0,
            "clb_registers": 0,
            "block_ram_tiles": 0,
            "uram": 0,
            "dsps": 0,
            "proof_scope": (
                "Current BACT candidate selection/token budgeting executes on PS and uses the unchanged Build "
                "0x4D395832 T32 bitstream; no new PL image was implemented or loaded for M288--M300."
            ),
        },
        "resource_risk": {
            "highest_utilization_resource": "dsps",
            "dsp_utilization_percent": resources["dsps"]["reported_utilization_percent"],
            "dsp_headroom": resources["dsps"]["headroom"],
            "interpretation": (
                "The current design is routed with positive timing slack, but DSP utilization is the tightest "
                "resource. Future T64/T128 work must time-fold rather than replicate MAC arrays."
            ),
        },
        "sources": {
            name: {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": digest(path)}
            for name, path in paths.items()
        },
        "claims": {
            "implemented_resource_claim_allowed": True,
            "board_execution_identity_claim_allowed": True,
            "bact_zero_incremental_pl_resource_claim_allowed_for_current_ps_selector": True,
            "dynamic_power_claim_allowed": False,
            "semantic_accuracy_claim_allowed": False,
            "causal_speed_claim_allowed": False,
            "real_time_claim_allowed": False,
        },
        "board_execution_run": False,
        "active_m254_m256_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Complete M296 human review and four-baseline held-out accuracy. Any future hardware candidate must "
            "retain the fixed CSim/header/CoSim/implementation/COM3 gate order."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(
        "M300_BACT_RESOURCE_BINDING_PASS "
        f"build={board['build_id']} dsp={resources['dsps']['reported_utilization_percent']:.2f}% "
        f"wns_ns={timing['wns_ns']:.3f} board_points={board['completed_measurements']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
