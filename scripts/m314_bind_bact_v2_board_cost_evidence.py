#!/usr/bin/env python3
"""Bind M313 geometry to existing KV260 T32 evidence without rerunning the board."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    paths = {
        "selector": workspace / "deployment/mage_vl4b/M313_BACT_V2_SELECTOR_RESULT.json",
        "geometry": workspace / "deployment/mage_vl4b/M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json",
        "board": workspace / "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
        "cost_model": workspace / "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
        "protocol": workspace / "bact/bact_v2_protocol.json",
    }
    documents = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    selector = documents["selector"]
    geometry = documents["geometry"]
    board = documents["board"]
    cost_model = documents["cost_model"]
    protocol = documents["protocol"]

    expected_build = "0x4d395832"
    expected_kernel = "mage_m120_m89x2_0"
    identities = {
        str(selector["hardware_identity"]["build_id"]).lower(),
        str(board["build_id"]).lower(),
        str(cost_model["board_identity"]["build_id"]).lower(),
        str(protocol["hardwareContract"]["buildId"]).lower(),
    }
    kernels = {
        selector["hardware_identity"]["kernel"],
        board["kernel"],
        board["loaded_kernel_ip"],
        cost_model["board_identity"]["kernel"],
        protocol["hardwareContract"]["kernel"],
    }
    assert identities == {expected_build}
    assert kernels == {expected_kernel}
    assert selector["hardware_identity"]["bitstream_changed"] is False
    assert board["completed_measurements"] == board["expected_measurements"] == 27
    assert board["runtime_load_count"] == 1 and board["vision_execution_count"] == 1
    assert board["host_collection"]["active_service_restoration_proved"] is True
    assert board["stable_rollback_preserved"] is True
    assert board["boot_dtb_cma_partitions_changed"] is False
    assert cost_model["source_sha256"] == sha256(paths["board"])

    records_checked = 0
    token_points: dict[int, list[dict]] = {}
    for record in board["records"]:
        tokens = int(record["prompt_tokens"])
        batches = math.ceil(tokens / 32)
        calls = 154 * batches + 8
        assert record["pass"] is True and record["finite"] is True
        assert record["t32_batches"] == batches
        assert record["expected_logical_fpga_calls"] == calls
        assert record["observed_logical_fpga_calls"] == calls
        token_points.setdefault(tokens, []).append(record)
        records_checked += 1
    assert records_checked == 27
    assert set(token_points) == {127, 128, 129, 159, 160, 161, 191, 192, 193}
    assert all(len(records) == 3 for records in token_points.values())

    baseline_map = {
        "count-144": geometry["candidates"]["token_count_aware"],
        "bact-159": geometry["candidates"]["bact"],
        "ratio-164": geometry["candidates"]["fixed_ratio_visual_pruning"],
    }
    expected_tokens = {"count-144": 144, "bact-159": 159, "ratio-164": 164}
    baseline_costs = {}
    for candidate_id, entry in baseline_map.items():
        tokens = int(entry["targetPromptTokensPerProbe"])
        assert entry["candidateId"] == candidate_id
        assert tokens == expected_tokens[candidate_id]
        batches = math.ceil(tokens / 32)
        calls = 154 * batches + 8
        assert entry["t32BatchesPerProbe"] == batches
        assert entry["logicalFpgaCallsPerProbe"] == calls
        baseline_costs[candidate_id] = {
            "total_tokens": tokens,
            "t32_batches": batches,
            "logical_calls": calls,
            "view_count": entry["viewCount"],
            "visual_tokens": entry["visualTokens"],
            "direct_point_in_27_record_board_sweep": tokens in token_points,
        }

    assert baseline_costs["count-144"]["t32_batches"] == baseline_costs["bact-159"]["t32_batches"] == 5
    assert baseline_costs["count-144"]["logical_calls"] == baseline_costs["bact-159"]["logical_calls"] == 778
    assert baseline_costs["bact-159"]["total_tokens"] - baseline_costs["count-144"]["total_tokens"] == 15
    assert baseline_costs["ratio-164"]["t32_batches"] - baseline_costs["bact-159"]["t32_batches"] == 1
    assert baseline_costs["ratio-164"]["logical_calls"] - baseline_costs["bact-159"]["logical_calls"] == 154
    assert selector["selected"]["candidate"]["candidate_id"] == "bact-159"

    result = {
        "date": "2026-09-03",
        "gate": "M314-BACT-V2-unchanged-geometry-KV260-cost-evidence-binding",
        "status": "PASS_EXISTING_BOARD_EVIDENCE_BOUND_NO_RERUN_REQUIRED",
        "classification": (
            "Hash-bound reuse of an existing real-KV260 27-point T32 boundary study. It proves the exact "
            "logical-call staircase for unchanged Build/Kernel geometry and supports descriptive pilot timing "
            "only; it is not a new board run or a quality, power, real-time or causal speed result."
        ),
        "identity": {
            "board": "AMD Kria KV260",
            "build_id": "0x4D395832",
            "kernel": expected_kernel,
            "formula": "Calls(N)=154*ceil(N/32)+8",
            "geometry_or_runtime_changed_since_source": False,
        },
        "existing_board_evidence": {
            "path": "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
            "sha256": sha256(paths["board"]),
            "measurements_verified": records_checked,
            "unique_token_points": sorted(token_points),
            "repeats_per_point": 3,
            "all_observed_calls_equal_formula": True,
            "runtime_load_count": board["runtime_load_count"],
            "vision_execution_count": board["vision_execution_count"],
        },
        "baseline_cost_identities": baseline_costs,
        "contrasts": {
            "same_cost_more_information": {
                "comparison": ["bact-159", "count-144"],
                "retained_token_delta": 15,
                "batch_delta": 0,
                "logical_call_delta": 0,
                "quality_advantage_claim_allowed": False,
            },
            "cross_boundary": {
                "comparison": ["ratio-164", "bact-159"],
                "removed_tokens": 5,
                "removed_batches": 1,
                "removed_logical_calls": 154,
                "causal_latency_claim_allowed": False,
            },
        },
        "rerun_decision": {
            "new_board_run_required": False,
            "reason": "Selector preserves the exact Build, Kernel, T32 granularity and language-chain formula already covered by 27 real-KV260 records.",
            "existing_27_point_sweep_repeated": False,
        },
        "inputs": {
            name: {"path": str(path.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(path)}
            for name, path in paths.items()
        },
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "M315 current-stage evidence and claim pack.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_bytes(canonical_bytes(result))
    os.replace(partial, args.result)
    print(
        "M314_BACT_V2_BOARD_EVIDENCE_BIND_PASS "
        "build=0x4D395832 records=27 count144=5/778 bact159=5/778 ratio164=6/932 rerun=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
