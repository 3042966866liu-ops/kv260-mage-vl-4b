#!/usr/bin/env python3
"""Profile exact M260 cache entries and scan bounded-memory policies."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import resource
import sys
import time
import types
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [
    item for item in sys.path if Path(item or ".").resolve() != _SCRIPT_DIR
]

import m222_vectorized_w4_runtime as _m222v
from keyframe_reducer import select_alarm_keyframes
from m260_cached_w4_runtime import (
    M260CachedCodeFourPortW4Store,
    M260CachedVariableFramePSVisionRuntime,
)
from variable_video_contract import preprocess


MIB = 1 << 20
BUDGETS_MIB = (64, 96, 128, 192, 256)


def digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def run_window(runtime, tensors):
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        output = runtime(
            tensors["pixel_values"],
            tensors["image_grid_thw"],
            tensors["patch_positions"],
        )
    return output, (time.perf_counter() - started) * 1000.0


def component_bytes(components) -> int:
    return int(sum(array.nbytes for array in components))


def select_entries(profile: dict, budget_bytes: int) -> tuple[list[str], int]:
    ranked = sorted(
        profile,
        key=lambda name: (
            -profile[name]["benefit_per_mib"],
            -profile[name]["saved_ms"],
            name,
        ),
    )
    selected = []
    used = 0
    for name in ranked:
        size = int(profile[name]["cache_bytes"])
        if used + size <= budget_bytes:
            selected.append(name)
            used += size
    return selected, used


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    fixture_root = workspace / "deployment/mage_vl4b/m249_ssdlite_board_candidate/fixtures"
    frames = np.stack([
        np.load(fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy", allow_pickle=False)
        for index, number in enumerate((68, 102, 137, 171))
    ])
    selected_frames, selection = select_alarm_keyframes(
        frames, keep=2, timestamps_seconds=(0.0, 1.0, 2.0, 3.0)
    )
    tensors = preprocess(selected_frames)
    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    runtime = M260CachedVariableFramePSVisionRuntime(
        candidate / "ps_vision_payload",
        candidate / "vision_layout",
        candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        heartbeat_seconds=3600.0,
    )
    store = runtime.store
    cold_by_name: dict[str, float] = {}
    warm_by_name: dict[str, float] = {}
    phase = "cold"
    original_decode = store.decode

    def measured_decode(name: str):
        started = time.perf_counter()
        value = original_decode(name)
        elapsed = (time.perf_counter() - started) * 1000.0
        target = cold_by_name if phase == "cold" else warm_by_name
        target[name] = target.get(name, 0.0) + elapsed
        return value

    store.decode = measured_decode
    try:
        cold_output, cold_window_ms = run_window(runtime, tensors)
        phase = "warm"
        full_output, full_window_ms = run_window(runtime, tensors)
        if not np.array_equal(cold_output, full_output):
            raise RuntimeError("M261 full-cache output is not bit-exact")
        if set(cold_by_name) != set(warm_by_name) or len(cold_by_name) != 98:
            raise RuntimeError("M261 decode profile closure mismatch")

        full_components = dict(store._components)
        if len(full_components) != 98:
            raise RuntimeError("M261 expected exactly 98 cached visual Linear entries")
        profile = {}
        for name, components in full_components.items():
            size = component_bytes(components)
            saved = max(0.0, cold_by_name[name] - warm_by_name[name])
            profile[name] = {
                "cache_bytes": size,
                "cold_decode_ms": cold_by_name[name],
                "warm_reconstruct_ms": warm_by_name[name],
                "saved_ms": saved,
                "benefit_per_mib": saved / (size / MIB),
            }

        policies = []
        for budget_mib in BUDGETS_MIB:
            names, used = select_entries(profile, budget_mib * MIB)
            allowed = frozenset(names)
            store._components = {name: full_components[name] for name in allowed}
            store.cache_bytes = used
            counters = {"hits": 0, "uncached": 0}

            def bounded_decode(self, name: str):
                if name in allowed:
                    counters["hits"] += 1
                    return M260CachedCodeFourPortW4Store.decode(self, name)
                counters["uncached"] += 1
                return _m222v.M222VectorizedFourPortW4Store.decode(self, name)

            store.decode = types.MethodType(bounded_decode, store)
            output, window_ms = run_window(runtime, tensors)
            exact = np.array_equal(cold_output, output)
            finite = bool(np.isfinite(output).all())
            if not exact or not finite or counters["hits"] != len(allowed):
                raise RuntimeError(f"M261 budget {budget_mib} MiB exactness/accounting failed")
            policies.append({
                "budget_mib": budget_mib,
                "used_bytes": used,
                "used_mib": used / MIB,
                "cached_entries": len(allowed),
                "uncached_entries": counters["uncached"],
                "window_ms": window_ms,
                "host_speedup_vs_cold": cold_window_ms / window_ms,
                "host_reduction_vs_cold_percent": 100.0 * (cold_window_ms - window_ms) / cold_window_ms,
                "output_bit_exact": exact,
                "finite": finite,
                "selected_names": sorted(allowed),
            })

        full_improvement = max(0.0, cold_window_ms - full_window_ms)
        for policy in policies:
            improvement = max(0.0, cold_window_ms - policy["window_ms"])
            policy["retained_full_cache_improvement_fraction"] = (
                improvement / full_improvement if full_improvement else 0.0
            )
        eligible = [
            policy for policy in policies
            if policy["retained_full_cache_improvement_fraction"] >= 0.80
        ]
        recommended = min(eligible, key=lambda item: item["used_bytes"]) if eligible else min(
            policies, key=lambda item: item["window_ms"]
        )
    finally:
        runtime.close()

    result = {
        "date": "2026-09-02",
        "gate": "M261-bounded-exact-w4-cache-budget-scan-offline",
        "status": "PASS_OFFLINE_EXACT_BOARD_MEMORY_AND_SPEED_PENDING",
        "classification": (
            "Same-host bounded-cache scan with exact visual outputs only; not ARM64 memory/speed, "
            "semantic accuracy, FPGA E2E, Web deployment, or promotion."
        ),
        "selected_frame_indices": list(selection.indices),
        "output_shape": list(cold_output.shape),
        "output_sha256_fp32": digest(cold_output.astype(np.float32)),
        "cold_window_ms": cold_window_ms,
        "full_cache_window_ms": full_window_ms,
        "full_cache_bytes": sum(component_bytes(value) for value in full_components.values()),
        "full_cache_entries": len(full_components),
        "policies": policies,
        "selection_rule": "smallest measured budget retaining at least 80% of full-cache host improvement",
        "recommended_budget_mib": recommended["budget_mib"],
        "recommended_used_mib": recommended["used_mib"],
        "recommended_cached_entries": recommended["cached_entries"],
        "recommended_selected_names": recommended["selected_names"],
        "host_timing_is_board_evidence": False,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "next_gate": (
            "Use COM3 to measure active-service MemAvailable, then accept only a policy whose cache "
            "plus explicit safety reserve fits before isolated two-window board timing."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        "M261_CACHE_BUDGET_SCAN_PASS "
        f"cold_ms={cold_window_ms:.3f} full_ms={full_window_ms:.3f} "
        f"recommended_mib={recommended['budget_mib']} "
        f"recommended_actual_mib={recommended['used_mib']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
