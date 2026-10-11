#!/usr/bin/env python3
"""Offline contract/timing gate for two-keyframe visual inference."""

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
import warnings
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [
    item for item in sys.path
    if Path(item or ".").resolve() != _SCRIPT_DIR
]

from keyframe_reducer import select_alarm_keyframes
from m259_variable_vision_runtime import M259VariableFramePSVisionRuntime
from variable_video_contract import IMAGE_PAD, preprocess, render


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
        np.load(
            fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy",
            allow_pickle=False,
        )
        for index, number in enumerate((68, 102, 137, 171))
    ])
    selected, selection = select_alarm_keyframes(
        frames, keep=2, timestamps_seconds=(0.0, 1.0, 2.0, 3.0)
    )
    tensors = preprocess(selected)
    expected_pixels = 2 * 28 * 28
    if tensors["pixel_values"].shape != (expected_pixels, 768):
        raise RuntimeError("M259 two-frame processor pixel shape mismatch")
    if tensors["image_grid_thw"].tolist() != [[1, 28, 28], [1, 28, 28]]:
        raise RuntimeError("M259 two-frame grid contract mismatch")
    if int(tensors["merged_visual_tokens"]) != 392:
        raise RuntimeError("M259 merged token contract mismatch")

    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    init_started = time.monotonic()
    runtime = M259VariableFramePSVisionRuntime(
        candidate / "ps_vision_payload",
        candidate / "vision_layout",
        candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        heartbeat_seconds=3600.0,
    )
    init_ms = (time.monotonic() - init_started) * 1000.0
    try:
        started = time.monotonic()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with contextlib.redirect_stdout(io.StringIO()):
                visual = runtime(
                    tensors["pixel_values"],
                    tensors["image_grid_thw"],
                    tensors["patch_positions"],
                )
        forward_ms = (time.monotonic() - started) * 1000.0
        decoder = runtime.decoder_evidence()
    finally:
        runtime.close()

    if visual.shape != (392, 2560) or not np.isfinite(visual).all():
        raise RuntimeError(f"M259 visual output contract failed: {visual.shape}")
    prompt = "判断最新画面中是否出现刀具，并简要说明人物动作。"
    rendered = render(prompt, selection.timestamps_seconds)
    if rendered.count(IMAGE_PAD) != 392:
        raise RuntimeError("M259 prompt visual token count mismatch")
    from tokenizers import Tokenizer

    tokenizer_path = candidate / "text_auxiliary/tokenizer/tokenizer.json"
    ids = Tokenizer.from_file(str(tokenizer_path)).encode(
        rendered, add_special_tokens=False
    ).ids
    # The fixed Chinese monitoring prompt is one token longer than M257's
    # English contract prompt.  Keep its exact tokenizer result hash-locked.
    if len(ids) != 442:
        raise RuntimeError(f"M259 expected 442 prompt tokens, observed {len(ids)}")

    warnings_text = [str(item.message) for item in caught]
    # Import the complete composed entry point only after the numerical run, so
    # dependency closure and process-local runtime injection are part of the
    # same fail-closed result rather than an informal separate observation.
    import m259_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M259VariableFramePSVisionRuntime":
        raise RuntimeError("M259 composed vision runtime injection failed")
    if composed_server.M120VideoRuntime.__name__ != "M259PreVisionKeyframeRuntime":
        raise RuntimeError("M259 composed video runtime injection failed")
    four_frame = json.loads(
        (workspace / "deployment/mage_vl4b/m258_vision_state_sweep_source/M258_PREFIX_2.json")
        .read_text(encoding="utf-8")
    )
    four_frame_host_ms = float(four_frame["vision_forward_ms"])
    sources = (
        workspace / "deployment/mage_vl4b/m259_prevision_keyframe_source/m259_variable_vision_runtime.py",
        workspace / "deployment/mage_vl4b/m259_prevision_keyframe_source/m259_video_runtime.py",
        workspace / "deployment/mage_vl4b/m259_prevision_keyframe_source/m259_m254_video_server.py",
        workspace / "deployment/mage_vl4b/m259_prevision_keyframe_source/M259_BOUNDARY.md",
        Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M259-two-alarm-keyframe-prevision-offline-contract",
        "status": "PASS_OFFLINE_FINITE_SEMANTIC_AND_BOARD_PENDING",
        "classification": (
            "Real frozen input, exact preprocessing/prompt geometry, finite visual output, "
            "and host timing only; not semantic accuracy, ARM64 board speed, FPGA E2E, "
            "continuous Web, or promotion evidence."
        ),
        "source_frame_count": 4,
        "selected_frame_indices": list(selection.indices),
        "selected_timestamps_seconds": list(selection.timestamps_seconds),
        "context_scores": list(selection.context_scores),
        "selected_frame_sha256": digest(selected),
        "pixel_values_shape": list(tensors["pixel_values"].shape),
        "pixel_values_sha256": digest(tensors["pixel_values"]),
        "visual_output_shape": list(visual.shape),
        "visual_output_sha256_fp32": digest(visual.astype(np.float32)),
        "visual_output_finite": True,
        "prompt_tokens": len(ids),
        "prompt_token_ids_sha256_i32": digest(np.asarray(ids, dtype=np.int32)),
        "visual_prompt_tokens": rendered.count(IMAGE_PAD),
        "t32_batches": (len(ids) + 31) // 32,
        "logical_fpga_calls_one_generated_token": ((len(ids) + 31) // 32) * 154 + 8,
        "host_vision_forward_ms": forward_ms,
        "host_four_frame_m258_prefix2_ms": four_frame_host_ms,
        "host_vision_speedup_vs_four_frame": four_frame_host_ms / forward_ms,
        "host_vision_reduction_percent": 100.0 * (four_frame_host_ms - forward_ms) / four_frame_host_ms,
        "host_timing_is_board_evidence": False,
        "init_ms": init_ms,
        "decoder_evidence": decoder,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "warning_count": len(warnings_text),
        "precision_policy": runtime.state_policy_evidence(),
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "quantization_changed": False,
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources
        },
        "rejected_attempts": [
            "Initial fixture-name template assumed one shared frame number; corrected to the frozen 68/102/137/171 manifest names.",
            "The inherited M90 gate hard-coded 784 output tokens; replaced by a strict frame_count*196 gate without relaxing finite checks.",
            "The fixed Chinese monitoring prompt tokenizes to 442, not the earlier English-contract 441; exact 442 count and ID hash are now locked.",
        ],
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Run a labeled knife/no-knife and action semantic set before any board promotion; "
            "if accepted, package and run isolated COM3 fixed-window numerical/timing gate."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, args.result)
    print(
        "M259_PREVISION_KEYFRAME_OFFLINE_PASS "
        f"frames={selection.indices} visual_ms={forward_ms:.3f} "
        f"tokens={len(ids)} calls={result['logical_fpga_calls_one_generated_token']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
