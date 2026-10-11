#!/usr/bin/env python3
"""Offline geometry, finite-output and host timing gate for M262."""

from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import io
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [item for item in sys.path if Path(item or ".").resolve() != _SCRIPT_DIR]

from keyframe_reducer import select_alarm_keyframes
from m261_budgeted_w4_runtime import M261BudgetedVariableFramePSVisionRuntime
from m262_lowres_contract import IMAGE_PAD, preprocess, render, tokenize
from m262_lowres_runtime import M262LowResolutionPSVisionRuntime
from variable_video_contract import preprocess as preprocess_448


PROMPT = "判断最新画面中是否出现刀具，并简要说明人物动作。"


def digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def execute(runtime_class, candidate, tensors):
    started = time.perf_counter()
    runtime = runtime_class(
        candidate / "ps_vision_payload",
        candidate / "vision_layout",
        candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        heartbeat_seconds=3600.0,
    )
    init_ms = (time.perf_counter() - started) * 1000.0
    try:
        started = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            output = runtime(
                tensors["pixel_values"],
                tensors["image_grid_thw"],
                tensors["patch_positions"],
            )
        forward_ms = (time.perf_counter() - started) * 1000.0
        evidence = dict(runtime.decoder_evidence())
    finally:
        runtime.close()
    return output, init_ms, forward_ms, evidence


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
    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"

    full, full_init_ms, full_ms, full_decoder = execute(
        M261BudgetedVariableFramePSVisionRuntime, candidate, preprocess_448(selected)
    )
    gc.collect()
    low_tensors = preprocess(selected)
    low, low_init_ms, low_ms, low_decoder = execute(
        M262LowResolutionPSVisionRuntime, candidate, low_tensors
    )
    if full.shape != (392, 2560) or low.shape != (98, 2560):
        raise RuntimeError(f"M262 output geometry mismatch: {full.shape}/{low.shape}")
    if not np.isfinite(full).all() or not np.isfinite(low).all():
        raise RuntimeError("M262 finite-output gate failed")
    pooled = full.reshape(2, 14, 14, 2560).reshape(
        2, 7, 2, 7, 2, 2560
    ).mean(axis=(2, 4), dtype=np.float32).reshape(98, 2560)
    delta = low.astype(np.float64) - pooled.astype(np.float64)
    rmse = float(np.sqrt(np.mean(delta * delta)))
    cosine = float(
        np.dot(low.ravel().astype(np.float64), pooled.ravel().astype(np.float64))
        / (np.linalg.norm(low.ravel().astype(np.float64)) * np.linalg.norm(pooled.ravel().astype(np.float64)))
    )
    rendered = render(PROMPT, selection.timestamps_seconds)
    ids = tokenize(
        candidate / "text_auxiliary/tokenizer/tokenizer.json",
        PROMPT,
        selection.timestamps_seconds,
    )
    if rendered.count(IMAGE_PAD) != 98 or not 1 <= len(ids) < 442:
        raise RuntimeError("M262 prompt geometry reduction failed")
    t32_batches = math.ceil(len(ids) / 32)
    calls = t32_batches * 154 + 8
    if calls >= 2164:
        raise RuntimeError("M262 logical call count did not improve over M259")
    if not (
        low_decoder["cache_bytes"] == 66699264
        and low_decoder["cache_misses"] == 26
        and low_decoder["uncached_decode_calls"] == 72
        and low_decoder["cache_within_budget"] is True
    ):
        raise RuntimeError("M262 inherited M261 cache accounting mismatch")

    import m262_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M262LowResolutionPSVisionRuntime":
        raise RuntimeError("M262 composed vision runtime injection failed")
    if composed_server.M120VideoRuntime.__name__ != "M262LowResolutionKeyframeRuntime":
        raise RuntimeError("M262 composed video runtime injection failed")

    source_paths = (
        workspace / "deployment/mage_vl4b/m262_lowres_source/m262_lowres_contract.py",
        workspace / "deployment/mage_vl4b/m262_lowres_source/m262_lowres_runtime.py",
        workspace / "deployment/mage_vl4b/m262_lowres_source/m262_video_runtime.py",
        workspace / "deployment/mage_vl4b/m262_lowres_source/m262_m254_video_server.py",
        workspace / "deployment/mage_vl4b/m262_lowres_source/M262_BOUNDARY.md",
        Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M262-two-keyframe-224-low-resolution-offline",
        "status": "PASS_OFFLINE_GEOMETRY_FINITE_SEMANTIC_AND_BOARD_PENDING",
        "classification": (
            "Frozen two-frame low-resolution preprocessing, finite visual output, pooled-feature "
            "measurement, prompt/call geometry and composed import closure only; not semantic "
            "accuracy, ARM64 board speed, FPGA E2E, Web deployment, or promotion."
        ),
        "selected_frame_indices": list(selection.indices),
        "source_frame_size": 448,
        "candidate_frame_size": 224,
        "pixel_values_shape": list(low_tensors["pixel_values"].shape),
        "image_grid_thw": low_tensors["image_grid_thw"].tolist(),
        "full_visual_shape": list(full.shape),
        "low_visual_shape": list(low.shape),
        "low_visual_sha256_fp32": digest(low.astype(np.float32)),
        "low_visual_finite": True,
        "pooled_full_reference_shape": list(pooled.shape),
        "pooled_reference_cosine": cosine,
        "pooled_reference_rmse": rmse,
        "pooled_similarity_is_semantic_accuracy": False,
        "prompt_tokens": len(ids),
        "visual_prompt_tokens": rendered.count(IMAGE_PAD),
        "t32_batches": t32_batches,
        "logical_fpga_calls_one_generated_token": calls,
        "calls_vs_m259_reduction_percent": 100.0 * (2164 - calls) / 2164,
        "calls_vs_four_frame_reduction_percent": 100.0 * (4166 - calls) / 4166,
        "host_full_448_vision_ms": full_ms,
        "host_low_224_vision_ms": low_ms,
        "host_vision_speedup": full_ms / low_ms,
        "host_vision_reduction_percent": 100.0 * (full_ms - low_ms) / full_ms,
        "host_timing_is_board_evidence": False,
        "full_init_ms": full_init_ms,
        "low_init_ms": low_init_ms,
        "full_decoder_evidence": full_decoder,
        "low_decoder_evidence": low_decoder,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "semantic_accuracy_passed": False,
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Run labelled knife/non-knife and temporal-action semantic comparison against M259; "
            "reject low resolution if the fixed task labels regress before any board action."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        "M262_LOWRES_OFFLINE_PASS "
        f"visual_ms={low_ms:.3f} tokens={len(ids)} calls={calls} "
        f"cosine={cosine:.9f} rmse={rmse:.9f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
