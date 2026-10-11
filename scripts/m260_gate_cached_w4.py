#!/usr/bin/env python3
"""Two-window exactness/performance gate for M260's persistent code cache."""

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
from m260_cached_w4_runtime import M260CachedVariableFramePSVisionRuntime
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
        np.load(fixture_root / f"frame_{i:02d}_{n:04d}_rgb448.npy", allow_pickle=False)
        for i, n in enumerate((68, 102, 137, 171))
    ])
    selected, selection = select_alarm_keyframes(
        frames, keep=2, timestamps_seconds=(0.0, 1.0, 2.0, 3.0)
    )
    tensors = preprocess(selected)
    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    runtime = M260CachedVariableFramePSVisionRuntime(
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
            started = time.monotonic()
            with contextlib.redirect_stdout(io.StringIO()):
                output = runtime(
                    tensors["pixel_values"],
                    tensors["image_grid_thw"],
                    tensors["patch_positions"],
                )
            timings.append((time.monotonic() - started) * 1000.0)
            outputs.append(output)
            evidence.append(dict(runtime.decoder_evidence()))
    finally:
        runtime.close()
    exact = np.array_equal(outputs[0], outputs[1])
    if not exact or outputs[0].shape != (392, 2560) or not np.isfinite(outputs[1]).all():
        raise RuntimeError("M260 repeated-window output exactness/finite gate failed")
    if evidence[0]["cache_misses"] != 98 or evidence[0]["cache_hits"] != 0:
        raise RuntimeError("M260 cold cache accounting mismatch")
    if evidence[1]["cache_misses"] != 98 or evidence[1]["cache_hits"] != 98:
        raise RuntimeError("M260 warm cache accounting mismatch")
    import m260_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M260CachedVariableFramePSVisionRuntime":
        raise RuntimeError("M260 composed vision runtime injection failed")
    if composed_server.M120VideoRuntime.__name__ != "M260PreVisionKeyframeRuntime":
        raise RuntimeError("M260 composed video runtime injection failed")
    result = {
        "date": "2026-09-02",
        "gate": "M260-two-window-exact-packed-code-cache-offline",
        "status": "PASS_OFFLINE_EXACT_BOARD_MEMORY_AND_SPEED_PENDING",
        "classification": (
            "Two repeated host windows, exact output and cache accounting only; not ARM64 board "
            "memory/speed, semantic accuracy, FPGA E2E, Web deployment, or promotion."
        ),
        "selected_frame_indices": list(selection.indices),
        "output_shape": list(outputs[0].shape),
        "output_sha256_fp32": digest(outputs[0].astype(np.float32)),
        "warm_output_bit_exact_to_cold": exact,
        "cold_window_ms": timings[0],
        "warm_window_ms": timings[1],
        "host_warm_speedup": timings[0] / timings[1],
        "host_warm_reduction_percent": 100.0 * (timings[0] - timings[1]) / timings[0],
        "host_timing_is_board_evidence": False,
        "cold_evidence": evidence[0],
        "warm_evidence": evidence[1],
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                workspace / "deployment/mage_vl4b/m260_cached_w4_source/m260_cached_w4_runtime.py",
                workspace / "deployment/mage_vl4b/m260_cached_w4_source/m260_video_runtime.py",
                workspace / "deployment/mage_vl4b/m260_cached_w4_source/m260_m254_video_server.py",
                workspace / "deployment/mage_vl4b/m260_cached_w4_source/M260_BOUNDARY.md",
                Path(__file__).resolve(),
            )
        },
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Reject if ARM64 free-memory headroom cannot cover cache plus fast detector and language "
            "runtime; otherwise run isolated COM3 two-window timing/identity gate."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        "M260_CACHED_W4_OFFLINE_PASS "
        f"cold_ms={timings[0]:.3f} warm_ms={timings[1]:.3f} "
        f"cache_mib={evidence[1]['cache_bytes'] / (1 << 20):.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
