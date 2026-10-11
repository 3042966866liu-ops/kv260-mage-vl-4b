#!/usr/bin/env python3
"""Offline fail-closed M257 alarm-keyframe and prompt-cost gate."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m257_alarm_keyframe_source"
sys.path.insert(0, str(SOURCE))

from keyframe_reducer import select_alarm_keyframes, select_merged_visual_tokens  # noqa: E402
from variable_video_contract import preprocess, tokenize  # noqa: E402


PROMPT = "Describe the motion and color change in this short video in one sentence."
IMAGE_PAD_ID = 151655
LANGUAGE_FAMILIES_PER_BATCH = 154
LM_HEAD_CALLS = 8


def sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def main() -> int:
    fixture_root = ROOT / "deployment/mage_vl4b/m249_ssdlite_board_candidate/fixtures"
    frames = np.stack(
        [np.load(fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy")
         for index, number in enumerate((68, 102, 137, 171))]
    )
    tokenizer = (
        ROOT
        / "deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
    )
    official = np.load(
        ROOT
        / "deployment/mage_vl4b/m181_m120_video_board_candidate/fixtures/official_four_frame_processor.npz",
        allow_pickle=False,
    )
    baseline_ids = np.asarray(official["input_ids"][0], dtype=np.int64)
    with np.load(
        ROOT
        / "deployment/mage_vl4b/m181_m120_video_board_candidate/fixtures/m56_w4_vision_merged_bf16.npz",
        allow_pickle=False,
    ) as vision_fixture:
        merged_visual_bits = np.asarray(vision_fixture["merged_vision_w4_bf16_bits"], dtype=np.uint16)

    records = []
    frozen_preprocess_path = (
        ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate/board_preprocess.py"
    )
    spec = importlib.util.spec_from_file_location("m181_frozen_board_preprocess", frozen_preprocess_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen M181 board_preprocess")
    frozen_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen_module)
    frozen_preprocess = frozen_module.preprocess(frames)
    baseline_preprocess = preprocess(frames)
    checks = {
        "real_fixture_shape": list(frames.shape) == [4, 448, 448, 3],
        "baseline_prompt_tokens_849": int(baseline_ids.size) == 849,
        "baseline_image_pads_784": int(np.count_nonzero(baseline_ids == IMAGE_PAD_ID)) == 784,
        "k4_pixel_values_exact_frozen_m181": bool(
            np.array_equal(baseline_preprocess["pixel_values"], frozen_preprocess["pixel_values"])
        ),
        "k4_grid_exact_frozen_m181": bool(
            np.array_equal(baseline_preprocess["image_grid_thw"], frozen_preprocess["image_grid_thw"])
        ),
        "k4_positions_exact_frozen_m181": bool(
            np.array_equal(baseline_preprocess["patch_positions"], frozen_preprocess["patch_positions"])
        ),
    }
    for keep in (4, 3, 2):
        selected, selection = select_alarm_keyframes(
            frames,
            keep=keep,
            timestamps_seconds=(0.0, 1.0, 2.0, 3.0),
        )
        prepared = preprocess(selected)
        ids = np.asarray(tokenize(tokenizer, PROMPT, selection.timestamps_seconds), dtype=np.int64)
        selected_visual_bits = select_merged_visual_tokens(merged_visual_bits, selection.indices)
        expected_visual = keep * 196
        batches = math.ceil(int(ids.size) / 32)
        calls = batches * LANGUAGE_FAMILIES_PER_BATCH + LM_HEAD_CALLS
        selected_pixel_blocks = np.concatenate(
            [
                frozen_preprocess["pixel_values"][index * 784 : (index + 1) * 784]
                for index in selection.indices
            ],
            axis=0,
        )
        checks[f"k{keep}_latest_alarm_frame_retained"] = selection.latest_index in selection.indices
        checks[f"k{keep}_chronological"] = tuple(sorted(selection.indices)) == selection.indices
        checks[f"k{keep}_pixel_values_exact_subset"] = bool(
            np.array_equal(prepared["pixel_values"], selected_pixel_blocks)
        )
        checks[f"k{keep}_visual_token_count"] = int(prepared["merged_visual_tokens"]) == expected_visual
        checks[f"k{keep}_image_pad_count"] = int(np.count_nonzero(ids == IMAGE_PAD_ID)) == expected_visual
        checks[f"k{keep}_postvision_shape"] = list(selected_visual_bits.shape) == [expected_visual, 2560]
        expected_visual_bits = np.concatenate(
            [merged_visual_bits[index * 196 : (index + 1) * 196] for index in selection.indices],
            axis=0,
        )
        checks[f"k{keep}_postvision_exact_blocks"] = bool(
            np.array_equal(selected_visual_bits, expected_visual_bits)
        )
        if keep == 4:
            checks["k4_token_ids_exact_original"] = bool(np.array_equal(ids, baseline_ids))
        records.append(
            {
                "frames_kept": keep,
                "selected_indices": list(selection.indices),
                "selected_frame_sha256": [sha256(frames[index]) for index in selection.indices],
                "context_scores_vs_latest": list(selection.context_scores),
                "prompt_tokens": int(ids.size),
                "visual_tokens": expected_visual,
                "selected_visual_bits_sha256": sha256(selected_visual_bits),
                "t32_batches": batches,
                "logical_fpga_calls": calls,
                "call_reduction_vs_4166": 1.0 - calls / 4166.0,
                "call_scaled_language_projection_ms_not_measured": 704177.3267810058 * calls / 4166.0,
                "postvision_ttft_projection_ms_not_measured": (
                    307308.0 + 704177.3267810058 * calls / 4166.0
                ),
            }
        )

    passed = all(checks.values())
    result = {
        "date": "2026-09-02",
        "gate": "M257-alarm-keyframe-reduction-offline-contract",
        "status": "PASS" if passed else "FAIL",
        "classification": (
            "Real user-video keyframe selection, exact selected-frame preprocessing and prompt/call-count "
            "contract only; not semantic accuracy, board execution, measured speedup, FPGA or Web promotion."
        ),
        "policy": "always retain newest alarm frame; retain highest-luma-change context frames; chronological output",
        "checks": checks,
        "candidates": records,
        "stable_board_changed": False,
        "next_gate": (
            "Integrate post-vision whole-frame token selection into an isolated M243 runtime, then run "
            "the two- and three-frame candidates against frozen 4B semantic conclusions; reject any "
            "candidate that changes required knife/action conclusions before board timing."
        ),
    }
    output = ROOT / "deployment/mage_vl4b/M257_ALARM_KEYFRAME_OFFLINE_RESULT.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M257_ALARM_KEYFRAME_OFFLINE_PASS" if passed else "M257_ALARM_KEYFRAME_OFFLINE_FAIL")
    print(json.dumps(records, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
