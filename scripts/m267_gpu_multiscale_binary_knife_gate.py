#!/usr/bin/env python3
"""M267 constrained 0/1 knife review for the M266 multiscale visual input."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from m264_gpu_resolution_semantic_suite import build_samples, sha256
from m266_gpu_multiscale_semantic_gate import multiscale_views


LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def prepare(processor, frames: np.ndarray, prompt: str):
    images = [Image.fromarray(frame, mode="RGB") for frame in frames]
    messages = [{
        "role": "user",
        "content": [{"type": "video"}, {"type": "text", "text": prompt}],
    }]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m264", type=Path, required=True)
    parser.add_argument("--m266", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()
    m264_path = args.m264.resolve()
    m266_path = args.m266.resolve()
    m264 = json.loads(m264_path.read_text(encoding="utf-8"))
    m266 = json.loads(m266_path.read_text(encoding="utf-8"))
    if m266.get("status") != "FAIL_SMALL_LABELLED_MULTISCALE_SUITE":
        raise RuntimeError("M267 requires the frozen M266 general-semantic failure")

    m246_root = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path.insert(0, str(m246_root))
    from m246_knife_binary import (  # pylint: disable=import-error,import-outside-toplevel
        KNIFE_NO_TOKEN_ID,
        KNIFE_PROMPT,
        KNIFE_YES_TOKEN_ID,
    )

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M267 requires the existing WSL CUDA environment")
    samples = build_samples(workspace, examples)
    m264_knife = {
        record["name"]: record["full_448"]["semantic"]["knife"]
        for record in m264["records"]
    }
    expected = {
        sample.name: (1 if sample.expected.knife == "有" else 0)
        for sample in samples
    }
    if any(m264_knife.get(name) != ("有" if value else "无") for name, value in expected.items()):
        raise RuntimeError("M267 requires all four M264 448 knife labels to match the frozen labels")

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    tokenizer = processor.tokenizer
    no_ids = list(tokenizer.encode("0", add_special_tokens=False))
    yes_ids = list(tokenizer.encode("1", add_special_tokens=False))
    if no_ids != [KNIFE_NO_TOKEN_ID] or yes_ids != [KNIFE_YES_TOKEN_ID]:
        raise RuntimeError(f"M267 tokenizer contract mismatch 0={no_ids} 1={yes_ids}")
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
        preprocess_started = time.perf_counter()
        inputs = prepare(processor, multiscale_views(sample.frames_448), KNIFE_PROMPT)
        preprocess_ms = (time.perf_counter() - preprocess_started) * 1000.0
        shapes = {key: list(value.shape) for key, value in inputs.items() if hasattr(value, "shape")}
        moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
        started = time.perf_counter()
        with torch.inference_mode():
            output = model(**moved, use_cache=False)
        forward_ms = (time.perf_counter() - started) * 1000.0
        logits = output.logits[0, -1].float()
        no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
        yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
        decision = 1 if yes_logit >= no_logit else 0
        margin = yes_logit - no_logit
        records.append({
            "name": sample.name,
            "expected": expected[sample.name],
            "decision": decision,
            "pass": decision == expected[sample.name],
            "no_logit": no_logit,
            "yes_logit": yes_logit,
            "margin_yes_minus_no": margin,
            "score_calibrated": False,
            "prompt_tokens": int(moved["input_ids"].shape[1]),
            "tensor_shapes": shapes,
            "preprocess_ms": preprocess_ms,
            "forward_ms": forward_ms,
        })

    suite_pass = len(records) == 4 and all(record["pass"] for record in records)
    prompt_counts = sorted({record["prompt_tokens"] for record in records})
    projected = None
    if len(prompt_counts) == 1:
        prompt_tokens = prompt_counts[0]
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
        "PASS_SMALL_LABELLED_BINARY_MULTISCALE_SUITE_BOARD_PENDING"
        if suite_pass
        else "FAIL_SMALL_LABELLED_BINARY_MULTISCALE_SUITE"
    )
    result = {
        "date": "2026-09-02",
        "gate": "M267-official-gpu-constrained-binary-multiscale-knife",
        "status": status,
        "classification": (
            "Small labelled official Mage-VL NF4/BF16 constrained-logit knife regression screen; "
            "not calibrated knife accuracy, target-camera evidence, KV260 semantics, or FPGA speed."
        ),
        "predecessors": {
            "m264": str(m264_path),
            "m264_sha256": sha256(m264_path),
            "m266": str(m266_path),
            "m266_sha256": sha256(m266_path),
            "m246_source_sha256": sha256(m246_root / "m246_knife_binary.py"),
        },
        "architecture_decision": (
            "The bounded fast path remains responsible for person/action updates and immediate "
            "alarm. The 4B path is alarm-only semantic knife review and must not block or revoke it."
        ),
        "prompt": KNIFE_PROMPT,
        "knife_no_token_id": KNIFE_NO_TOKEN_ID,
        "knife_yes_token_id": KNIFE_YES_TOKEN_ID,
        "visual_strategy": m266["strategy"],
        "records": records,
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
        "threshold_calibrated": False,
        "semantic_accuracy_passed": False,
        "semantic_accuracy_reason": (
            "Four examples are only a regression screen. M252 held-out target-camera calibration "
            "is still required before reporting precision, recall or false-alarm rate."
        ),
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "If PASS, replace center crop with hash-locked fast-path ROI selection, rerun the same "
            "binary suite, package cleanly, and wait for COM3 for isolated KV260 TTFT."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        f"M267_GPU_BINARY_MULTISCALE_{'PASS' if suite_pass else 'FAIL'} "
        f"passed={sum(record['pass'] for record in records)}/{len(records)}"
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
