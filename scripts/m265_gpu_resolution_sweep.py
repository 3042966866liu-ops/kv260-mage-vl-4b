#!/usr/bin/env python3
"""M265 find the smallest labelled-suite-safe Mage-VL visual resolution."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np

from m264_gpu_resolution_semantic_suite import build_samples, run_one, sha256


CANDIDATE_SIZES = (256, 320, 384)
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8
BOARD_TEXT_TOKENS = 50


def resize_frames(frames: np.ndarray, size: int) -> np.ndarray:
    return np.stack([
        cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)
        for frame in frames
    ]).astype(np.uint8, copy=False)


def board_geometry(size: int) -> dict:
    if size % 32:
        raise ValueError(f"size must be divisible by 32: {size}")
    merged_axis = size // 32
    visual_tokens = 2 * merged_axis * merged_axis
    prompt_tokens = visual_tokens + BOARD_TEXT_TOKENS
    batches = math.ceil(prompt_tokens / 32)
    calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
    return {
        "frame_size": [size, size],
        "frames": 2,
        "merged_visual_axis_per_frame": merged_axis,
        "visual_tokens": visual_tokens,
        "board_contract_prompt_tokens": prompt_tokens,
        "t32_batches": batches,
        "logical_fpga_calls": calls,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m264", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()
    m264_path = args.m264.resolve()
    m264 = json.loads(m264_path.read_text(encoding="utf-8"))
    if m264.get("gate") != "M264-official-gpu-labelled-resolution-semantic-suite":
        raise RuntimeError("M265 predecessor is not the exact M264 semantic suite")
    if m264.get("candidate_regressions") != ["businesswoman_knife_positive"]:
        raise RuntimeError("M265 predecessor no longer has the frozen knife-positive 224 regression")

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M265 requires the existing WSL CUDA environment")
    samples = build_samples(workspace, examples)
    sample_by_name = {sample.name: sample for sample in samples}
    knife_sample = sample_by_name["businesswoman_knife_positive"]
    other_samples = [sample for sample in samples if sample.name != knife_sample.name]
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        quantization_config=quant,
        device_map="auto",
        low_cpu_mem_usage=True,
    ).eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0
    torch.cuda.reset_peak_memory_stats()

    sweeps = []
    selected = None
    for size in CANDIDATE_SIZES:
        geometry = board_geometry(size)
        knife_result = run_one(
            model,
            processor,
            resize_frames(knife_sample.frames_448, size),
            f"{knife_sample.name}:{size}",
            knife_sample.expected,
        )
        records = [{
            "name": knife_sample.name,
            "result": knife_result,
            "pass": bool(knife_result["semantic"]["matches_expected"]),
        }]
        # Knife-positive recall is a hard requirement. Do not spend more GPU work on
        # a resolution that already fails it.
        if records[0]["pass"]:
            for sample in other_samples:
                candidate = run_one(
                    model,
                    processor,
                    resize_frames(sample.frames_448, size),
                    f"{sample.name}:{size}",
                    sample.expected,
                )
                records.append({
                    "name": sample.name,
                    "result": candidate,
                    "pass": bool(candidate["semantic"]["matches_expected"]),
                })
        passed = len(records) == len(samples) and all(record["pass"] for record in records)
        sweeps.append({
            "size": size,
            "geometry": geometry,
            "records": records,
            "knife_positive_pass": records[0]["pass"],
            "all_four_samples_executed": len(records) == len(samples),
            "suite_pass": passed,
        })
        if passed:
            selected = sweeps[-1]
            break

    status = (
        "PASS_SMALLEST_TESTED_LABELLED_SUITE_SAFE_RESOLUTION_BOARD_PENDING"
        if selected is not None
        else "FAIL_NO_TESTED_RESOLUTION_PASSES_SMALL_LABELLED_SUITE"
    )
    baseline_calls = 2164
    selected_summary = None
    if selected is not None:
        geometry = selected["geometry"]
        selected_summary = {
            **geometry,
            "logical_call_reduction_vs_M259_448_fraction": (
                1.0 - geometry["logical_fpga_calls"] / baseline_calls
            ),
            "logical_call_reduction_vs_M259_448_percent": (
                100.0 * (1.0 - geometry["logical_fpga_calls"] / baseline_calls)
            ),
            "selection_rule": (
                "Smallest ascending candidate whose knife-positive sample and all three "
                "additional labelled samples match their frozen expected labels."
            ),
        }
    result = {
        "date": "2026-09-02",
        "gate": "M265-official-gpu-labelled-resolution-sweep",
        "status": status,
        "classification": (
            "Small labelled official Mage-VL NF4/BF16 GPU resolution screen; not target-camera "
            "accuracy, KV260 quantized semantics, FPGA speed, or board promotion."
        ),
        "predecessor": str(m264_path),
        "predecessor_sha256": sha256(m264_path),
        "frozen_predecessor_regression": m264["candidate_regressions"],
        "tested_sizes_ascending": list(CANDIDATE_SIZES),
        "sweeps": sweeps,
        "selected": selected_summary,
        "model": "microsoft/Mage-VL",
        "checkpoint": str(model_path),
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "semantic_accuracy_passed": False,
        "semantic_accuracy_reason": (
            "The selection suite has four labelled examples and is only a resolution-regression "
            "screen, not held-out target-camera accuracy."
        ),
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "Generate a clean candidate at the selected resolution, then wait for COM3 and run "
            "isolated KV260 memory, exact identity, semantic and complete TTFT gates."
            if selected is not None
            else "Retain M259 448 and add labelled data before considering any other visual reduction."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    chosen = selected_summary["frame_size"][0] if selected_summary else None
    print(f"M265_GPU_RESOLUTION_SWEEP_{'PASS' if selected else 'FAIL'} selected={chosen}")
    return 0 if selected is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
