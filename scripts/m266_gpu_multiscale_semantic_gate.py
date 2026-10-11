#!/usr/bin/env python3
"""M266 global-plus-detail multiscale semantic gate for Mage-VL."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from m264_gpu_resolution_semantic_suite import (
    FirstTokenTimer,
    build_samples,
    parse_flags,
    sha256,
)


PROMPT = (
    "每个时刻依次给出全景和中心放大图。请仅依据可见内容判断安全状态。"
    "只回答：刀具=有或无；人物=有或无；动作=一个简短动作。"
)
DETAIL_CROP_SIZE = 320
OUTPUT_SIZE = 224
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def area_resize(frame: np.ndarray, size: int) -> np.ndarray:
    return cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA).astype(np.uint8, copy=False)


def multiscale_views(frames_448: np.ndarray) -> np.ndarray:
    offset = (448 - DETAIL_CROP_SIZE) // 2
    end = offset + DETAIL_CROP_SIZE
    views = []
    for frame in frames_448:
        views.append(area_resize(frame, OUTPUT_SIZE))
        views.append(area_resize(frame[offset:end, offset:end], OUTPUT_SIZE))
    return np.stack(views)


def prepare(processor, frames: np.ndarray):
    images = [Image.fromarray(frame, mode="RGB") for frame in frames]
    messages = [{
        "role": "user",
        "content": [{"type": "video"}, {"type": "text", "text": PROMPT}],
    }]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def run_one(model, processor, frames: np.ndarray, label: str, expected) -> dict:
    import torch

    preprocess_started = time.perf_counter()
    inputs = prepare(processor, frames)
    preprocess_ms = (time.perf_counter() - preprocess_started) * 1000.0
    shapes = {key: list(value.shape) for key, value in inputs.items() if hasattr(value, "shape")}
    moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
    timer = FirstTokenTimer()
    generation_started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **moved,
            do_sample=False,
            use_cache=True,
            max_new_tokens=40,
            streamer=timer,
        )
    generation_finished = time.perf_counter()
    if timer.first_token_time is None:
        raise RuntimeError(f"M266 {label} generated no observable first token")
    prompt_tokens = int(moved["input_ids"].shape[1])
    token_ids = [int(value) for value in output[0, prompt_tokens:].tolist()]
    answer = processor.tokenizer.decode(
        token_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
    ).strip()
    return {
        "label": label,
        "prompt_tokens": prompt_tokens,
        "tensor_shapes": shapes,
        "generated_token_ids": token_ids,
        "answer": answer,
        "semantic": parse_flags(answer, expected),
        "preprocess_ms": preprocess_ms,
        "ttft_ms": (timer.first_token_time - generation_started) * 1000.0,
        "generation_ms": (generation_finished - generation_started) * 1000.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m264", type=Path, required=True)
    parser.add_argument("--m265", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()
    m264_path = args.m264.resolve()
    m265_path = args.m265.resolve()
    m264 = json.loads(m264_path.read_text(encoding="utf-8"))
    m265 = json.loads(m265_path.read_text(encoding="utf-8"))
    if m264.get("supported_sample_count", 0) < 1:
        raise RuntimeError("M266 requires at least one supported M264 448 baseline")
    m264_support = {
        record["name"]: bool(record["full_supported"])
        for record in m264.get("records", [])
    }
    if not m264_support.get("businesswoman_knife_positive", False):
        raise RuntimeError("M266 requires the M264 448 knife-positive baseline to be supported")
    if m265.get("status") != "FAIL_NO_TESTED_RESOLUTION_PASSES_SMALL_LABELLED_SUITE":
        raise RuntimeError("M266 requires the frozen uniform-resolution sweep failure")

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M266 requires the existing WSL CUDA environment")
    samples = build_samples(workspace, examples)
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

    records = []
    for sample in samples:
        result = run_one(
            model,
            processor,
            multiscale_views(sample.frames_448),
            sample.name,
            sample.expected,
        )
        records.append({
            "name": sample.name,
            "expected": {
                "knife": sample.expected.knife,
                "person": sample.expected.person,
                "action_any": list(sample.expected.action_any),
            },
            "candidate": result,
            "full_448_supported": m264_support.get(sample.name, False),
            "pass": bool(result["semantic"]["matches_expected"]),
            "candidate_regression": bool(
                m264_support.get(sample.name, False)
                and not result["semantic"]["matches_expected"]
            ),
        })

    supported_records = [record for record in records if record["full_448_supported"]]
    regressions = [record["name"] for record in records if record["candidate_regression"]]
    suite_pass = (
        len(records) == 4
        and len(supported_records) == m264["supported_sample_count"]
        and not regressions
        and all(record["pass"] for record in supported_records)
    )
    prompt_token_counts = sorted({record["candidate"]["prompt_tokens"] for record in records})
    visual_tokens = 4 * (OUTPUT_SIZE // 32) ** 2
    projected = None
    if len(prompt_token_counts) == 1:
        prompt_tokens = prompt_token_counts[0]
        batches = math.ceil(prompt_tokens / 32)
        calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
        projected = {
            "official_processor_prompt_tokens": prompt_tokens,
            "t32_batches_from_official_prompt": batches,
            "logical_calls_from_official_prompt": calls,
            "call_reduction_vs_M264_official_448_prompt_percent": 100.0 * (1.0 - calls / 2318.0),
            "not_board_measurement": True,
        }
    status = (
        "PASS_SMALL_LABELLED_MULTISCALE_SUITE_BOARD_PENDING"
        if suite_pass
        else "FAIL_SMALL_LABELLED_MULTISCALE_SUITE"
    )
    result = {
        "date": "2026-09-02",
        "gate": "M266-official-gpu-global-detail-multiscale-semantic",
        "status": status,
        "classification": (
            "Small labelled official Mage-VL NF4/BF16 GPU multiscale regression screen; not "
            "target-camera accuracy, KV260 quantized semantics, FPGA speed, or board promotion."
        ),
        "predecessors": {
            "m264": str(m264_path),
            "m264_sha256": sha256(m264_path),
            "m265": str(m265_path),
            "m265_sha256": sha256(m265_path),
        },
        "strategy": {
            "selected_keyframes": 2,
            "views_per_keyframe": ["224x224 global", "224x224 centered 320-of-448 crop"],
            "input_frames_to_processor": 4,
            "visual_tokens": visual_tokens,
            "visual_token_reduction_vs_M259_392_percent": 100.0 * (1.0 - visual_tokens / 392.0),
            "detail_source_is_label_independent": True,
            "future_board_roi_source": (
                "Use the already bounded fast-path person/object region to choose the detail crop; "
                "the current center crop is a deterministic feasibility screen, not final ROI logic."
            ),
        },
        "prompt": PROMPT,
        "records": records,
        "full_448_supported_sample_count": len(supported_records),
        "candidate_regressions_on_supported_samples": regressions,
        "suite_pass": suite_pass,
        "projected_schedule": projected,
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
            "Four examples prove only a regression screen; a labelled held-out target-camera set "
            "and calibrated M252 metrics remain required."
        ),
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "If PASS, replace the center-crop feasibility rule with hash-locked fast-path ROI "
            "selection, rerun this suite, package cleanly, and wait for COM3 for KV260 TTFT."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        f"M266_GPU_MULTISCALE_SEMANTIC_{'PASS' if suite_pass else 'FAIL'} "
        f"supported_passed={sum(record['pass'] for record in supported_records)}/"
        f"{len(supported_records)} regressions={regressions}"
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
