#!/usr/bin/env python3
"""Consolidate the reproducible M258 sweep without promoting it to board PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m258_vision_state_sweep_source"
OUTPUT = ROOT / "deployment/mage_vl4b/M258_VISION_STATE_POLICY_OFFLINE_RESULT.json"
M244 = ROOT / "deployment/mage_vl4b/M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    sweep = []
    for prefix in range(7):
        path = SOURCE / f"M258_PREFIX_{prefix}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        observed = value["policy"]["bf16_prefix_layers"]
        if observed != list(range(prefix)):
            raise RuntimeError(f"M258 prefix identity mismatch: {prefix}/{observed}")
        sweep.append({
            "bf16_prefix": prefix,
            "status": value["status"],
            "cosine": value["metrics_vs_M56_W4_BF16_golden"]["cosine_similarity"],
            "rmse": value["metrics_vs_M56_W4_BF16_golden"]["rmse"],
            "host_vision_forward_ms": value["vision_forward_ms"],
            "result_sha256": sha256(path),
        })
    if sweep[0]["status"] != "FAIL" or any(
        item["status"] != "PASS" for item in sweep[1:]
    ):
        raise RuntimeError("M258 sweep status contract mismatch")

    selected = sweep[2]
    m244 = json.loads(M244.read_text(encoding="utf-8"))
    layers = {
        int(item["payload"]["index"]): float(item["payload"]["layer_ms"])
        for item in m244["events"] if item["event"] == "vision_layer_pass"
    }
    if sorted(layers) != list(range(24)):
        raise RuntimeError("M258 M244 layer evidence is incomplete")
    bf16_mean = sum(layers[index] for index in range(6)) / 6.0
    fp32_mean = sum(layers[index] for index in range(6, 24)) / 18.0
    layer_sum_ms = sum(layers.values())
    final_layer_event = next(
        item for item in m244["events"]
        if item["event"] == "vision_layer_pass"
        and int(item["payload"]["index"]) == 23
    )
    baseline_ms = float(final_layer_event["payload"]["elapsed_s"]) * 1000.0
    changed = 4
    projected_ms = baseline_ms - changed * (bf16_mean - fp32_mean)

    sources = (
        SOURCE / "m258_vectorized_w4_runtime.py",
        SOURCE / "m258_m254_video_server.py",
        SOURCE / "M258_BOUNDARY.md",
        ROOT / "scripts/m258_gate_vision_state_policy.py",
        Path(__file__),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M258-visual-state-boundary-offline-sweep",
        "status": "PASS_OFFLINE_NUMERICAL_BOARD_TIMING_PENDING",
        "classification": (
            "Frozen four-frame numerical sweep and isolated Web-entry integration source; "
            "not ARM64 board timing, FPGA E2E, semantic accuracy, Web deployment, or promotion."
        ),
        "selected_policy": {
            "bf16_prefix": 2,
            "bf16_layers": [0, 1],
            "fp32_layers": list(range(2, 24)),
            "selection_reason": (
                "Prefix 1 passes too close to the cosine threshold; prefix 2 retains "
                "a larger numerical guard band while converting four expensive BF16 blocks."
            ),
            "cosine": selected["cosine"],
            "rmse": selected["rmse"],
        },
        "sweep": sweep,
        "frozen_thresholds": {"cosine_minimum": 0.999, "rmse_maximum": 0.05},
        "unchanged": [
            "M222 packed W4/FP16-scale decoder",
            "FP32 W4 Linear GEMM",
            "four-frame preprocessing and token count",
            "M238/M241 T32 language path",
            "M254 fast alarm path",
            "overlay/boot/DTB/CMA/partitions/stable rollback",
        ],
        "board_projection_not_measurement": {
            "source_result": str(M244.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": sha256(M244),
            "m244_visual_total_ms": baseline_ms,
            "m244_visual_layer_sum_ms": layer_sum_ms,
            "m244_pre_layer_and_boundary_ms": baseline_ms - layer_sum_ms,
            "m244_bf16_layer_mean_ms": bf16_mean,
            "m244_fp32_layer_mean_ms": fp32_mean,
            "changed_layers": [2, 3, 4, 5],
            "projected_visual_ms": projected_ms,
            "projected_reduction_ms": baseline_ms - projected_ms,
            "projected_reduction_percent": 100.0 * (baseline_ms - projected_ms) / baseline_ms,
            "measured_board_speedup": False,
        },
        "source_hashes": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in sources
        },
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Package from a clean whitelist, verify recursive dependency/hash closure, then run "
            "an isolated COM3 board fixed-four-frame numerical/timing gate before any Web promotion."
        ),
    }
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, OUTPUT)
    print(
        "M258_OFFLINE_FINALIZE_PASS "
        f"selected_prefix=2 cosine={selected['cosine']:.12f} "
        f"projected_board_visual_ms={projected_ms:.3f} measured=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
