#!/usr/bin/env python3
"""Freeze the 27-measurement BACT KV260 boundary schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.benchmark import BOUNDARY_TRIPLETS, calls, counterbalanced_schedule, summarize_latency


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    m283 = workspace / "deployment/mage_vl4b/M283R1_BACT_BOUNDARY_EVIDENCE_SPLIT_RESULT.json"
    m284 = workspace / "deployment/mage_vl4b/M284_BACT_OUTER_BOUNDARY_GEOMETRY_RESULT.json"
    schedule = counterbalanced_schedule()
    assert len(schedule) == 27
    for tokens in {value for triplet in BOUNDARY_TRIPLETS for value in triplet}:
        positions = sorted(
            record["position_within_triplet"] for record in schedule if record["prompt_tokens"] == tokens
        )
        assert positions == [0, 1, 2], (tokens, positions)
    # Prove the analyzer itself with deterministic timing that contains a known step.
    synthetic = [
        {
            **record,
            "observed_logical_fpga_calls": record["expected_logical_fpga_calls"],
            "finite": True,
            "prefill_ms": 1000.0 + 150.0 * record["t32_batches"] + 3.0 * record["position_within_triplet"],
        }
        for record in schedule
    ]
    synthetic_summary = summarize_latency(synthetic)
    if not all(value["cross_boundary_step_delta_ms"] > 0.0 for value in synthetic_summary["boundary_summary"].values()):
        raise RuntimeError("M293 synthetic latency analyzer did not recover positive steps")

    result = {
        "date": "2026-09-02",
        "gate": "M293-counterbalanced-BACT-boundary-board-plan",
        "status": "PASS_OFFLINE_SCHEDULE_ONLY",
        "classification": (
            "Frozen 27-measurement counterbalanced board schedule and tested analysis contract only. "
            "No new KV260 execution, TTFT distribution, semantic accuracy, power or real-time evidence."
        ),
        "predecessors": {
            "m283_split": {"path": str(m283.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(m283)},
            "m284_geometry": {"path": str(m284.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(m284)},
        },
        "triplets": [list(item) for item in BOUNDARY_TRIPLETS],
        "schedule": schedule,
        "measurement_count": len(schedule),
        "runtime_load_count_target": 1,
        "vision_execution_count_target": 1,
        "unmeasured_warmup_count": 1,
        "acceptance": {
            "build_id": "0x4D395832",
            "kernel": "mage_m120_m89x2_0",
            "all_outputs_finite": True,
            "every_call_delta_exact": True,
            "semantic_decision_invariance_required": False,
            "semantic_reason": "Artificial x suffixes isolate tokenizer/hardware geometry and are not natural prompts.",
            "stable_m254_restore_required": True,
        },
        "analysis": {
            "per_token": "median and median absolute deviation over three positions",
            "same_batch_control": "edge median minus low median",
            "boundary_step": "high median minus mean(low median, edge median)",
            "automatic_speed_claim": False,
        },
        "synthetic_analyzer_test": synthetic_summary,
        "source_sha256": sha256(Path(__file__).resolve()),
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Package one hash-locked COM3 runner that loads runtime/vision once, performs one unmeasured warmup, "
            "executes this exact schedule with partial-result checkpoints, and restores M254 on every exit path."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M293_COUNTERBALANCED_BOUNDARY_PLAN_PASS measurements=27")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
