#!/usr/bin/env python3
"""Two-window exactness and accounting gate for the deployable M261 runtime."""

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
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [
    item for item in sys.path if Path(item or ".").resolve() != _SCRIPT_DIR
]

from keyframe_reducer import select_alarm_keyframes
from m261_budgeted_w4_runtime import (
    EXPECTED_CACHE_BYTES,
    EXPECTED_CACHE_ENTRIES,
    M261BudgetedVariableFramePSVisionRuntime,
)
from variable_video_contract import preprocess


def digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


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
    selected, selection = select_alarm_keyframes(
        frames, keep=2, timestamps_seconds=(0.0, 1.0, 2.0, 3.0)
    )
    tensors = preprocess(selected)
    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    runtime = M261BudgetedVariableFramePSVisionRuntime(
        candidate / "ps_vision_payload",
        candidate / "vision_layout",
        candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        heartbeat_seconds=3600.0,
    )
    outputs = []
    timings = []
    evidence = []
    try:
        for _ in range(2):
            started = time.perf_counter()
            with contextlib.redirect_stdout(io.StringIO()):
                output = runtime(
                    tensors["pixel_values"],
                    tensors["image_grid_thw"],
                    tensors["patch_positions"],
                )
            timings.append((time.perf_counter() - started) * 1000.0)
            outputs.append(output)
            evidence.append(dict(runtime.decoder_evidence()))
    finally:
        runtime.close()
    if (
        outputs[0].shape != (392, 2560)
        or not np.isfinite(outputs[0]).all()
        or not np.array_equal(outputs[0], outputs[1])
    ):
        raise RuntimeError("M261 output exactness/finite gate failed")
    cold, warm = evidence
    if not (
        cold["cache_misses"] == EXPECTED_CACHE_ENTRIES
        and cold["cache_hits"] == 0
        and cold["uncached_decode_calls"] == 72
        and cold["cache_bytes"] == EXPECTED_CACHE_BYTES
        and warm["cache_misses"] == EXPECTED_CACHE_ENTRIES
        and warm["cache_hits"] == EXPECTED_CACHE_ENTRIES
        and warm["uncached_decode_calls"] == 144
        and warm["cache_bytes"] == EXPECTED_CACHE_BYTES
        and warm["cache_within_budget"] is True
    ):
        raise RuntimeError(f"M261 cache accounting mismatch: {cold}/{warm}")

    import m261_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M261BudgetedVariableFramePSVisionRuntime":
        raise RuntimeError("M261 composed vision runtime injection failed")
    if composed_server.M120VideoRuntime.__name__ != "M261PreVisionKeyframeRuntime":
        raise RuntimeError("M261 composed video runtime injection failed")

    source_paths = (
        workspace / "deployment/mage_vl4b/m261_bounded_cache_source/m261_budgeted_w4_runtime.py",
        workspace / "deployment/mage_vl4b/m261_bounded_cache_source/m261_video_runtime.py",
        workspace / "deployment/mage_vl4b/m261_bounded_cache_source/m261_m254_video_server.py",
        workspace / "deployment/mage_vl4b/m261_bounded_cache_source/M261_CACHE_POLICY.json",
        workspace / "deployment/mage_vl4b/m261_bounded_cache_source/M261_BOUNDARY.md",
        Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M261-deployable-bounded-exact-cache-offline",
        "status": "PASS_OFFLINE_EXACT_BOARD_MEMORY_AND_SPEED_PENDING",
        "classification": (
            "Deployable bounded-cache source, exact outputs and composed import closure only; "
            "not ARM64 board memory/speed, semantic accuracy, FPGA E2E, Web deployment, or promotion."
        ),
        "selected_frame_indices": list(selection.indices),
        "output_shape": list(outputs[0].shape),
        "output_sha256_fp32": digest(outputs[0].astype(np.float32)),
        "warm_output_bit_exact_to_cold": True,
        "cold_window_ms": timings[0],
        "warm_window_ms": timings[1],
        "host_warm_speedup": timings[0] / timings[1],
        "host_warm_reduction_percent": 100.0 * (timings[0] - timings[1]) / timings[0],
        "host_timing_is_board_evidence": False,
        "cold_evidence": cold,
        "warm_evidence": warm,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "COM3 read-only memory-headroom gate, then isolated two-window ARM64 timing/identity gate."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        "M261_BOUNDED_RUNTIME_OFFLINE_PASS "
        f"cold_ms={timings[0]:.3f} warm_ms={timings[1]:.3f} "
        f"cache_mib={EXPECTED_CACHE_BYTES / (1 << 20):.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
