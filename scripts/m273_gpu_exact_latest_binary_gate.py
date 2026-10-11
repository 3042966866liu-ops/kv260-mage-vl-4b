#!/usr/bin/env python3
"""Official GPU screen for the exact boardable M273 NumPy views and prompt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

from PIL import Image

from m264_gpu_resolution_semantic_suite import build_samples


EXPECTED_M272_SHA256 = "46aa16a636c5008ad65e51caad73da4d55f0da15cf4cc266ed53f59d8183d4f9"
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(processor, views, prompt):
    images = [Image.fromarray(frame, mode="RGB") for frame in views]
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
    parser.add_argument("--m272", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    m272_path = args.m272.resolve()
    if sha256(m272_path) != EXPECTED_M272_SHA256:
        raise RuntimeError("M273 M272 predecessor hash mismatch")
    m272 = json.loads(m272_path.read_text(encoding="utf-8"))
    if m272.get("selected_for_further_validation") != "two_latest_global_detail":
        raise RuntimeError("M273 requires frozen M272 selected candidate")
    source = workspace / "deployment/mage_vl4b/m273_latest_binary_source"
    sys.path.insert(0, str(source))
    from m273_latest_multiscale_contract import M273_KNIFE_PROMPT, make_views
    m246 = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path.insert(0, str(m246))
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_YES_TOKEN_ID

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M273 requires existing WSL CUDA")
    model_path = args.model.resolve()
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True,
        quantization_config=quant, device_map="auto", low_cpu_mem_usage=True,
    ).eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0
    samples = build_samples(workspace, args.examples.resolve())
    records = []
    for sample in samples:
        views = make_views(sample.frames_448[-1:])
        inputs = prepare(processor, views, M273_KNIFE_PROMPT)
        moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
        started = time.perf_counter()
        with torch.inference_mode():
            output = model(**moved, use_cache=False)
        forward_ms = (time.perf_counter() - started) * 1000.0
        logits = output.logits[0, -1].float()
        no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
        yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
        expected = 1 if sample.expected.knife == "有" else 0
        decision = 1 if yes_logit >= no_logit else 0
        records.append({
            "name": sample.name,
            "expected": expected,
            "decision": decision,
            "pass": decision == expected,
            "no_logit": no_logit,
            "yes_logit": yes_logit,
            "margin_yes_minus_no": yes_logit - no_logit,
            "prompt_tokens": int(moved["input_ids"].shape[1]),
            "visual_tokens": 98,
            "forward_ms": forward_ms,
        })
    counts = {record["prompt_tokens"] for record in records}
    if len(counts) != 1:
        raise RuntimeError("M273 prompt geometry differs across samples")
    prompt_tokens = counts.pop()
    batches = math.ceil(prompt_tokens / 32)
    calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
    suite_pass = len(records) == 4 and all(record["pass"] for record in records)
    result = {
        "date": "2026-09-02",
        "gate": "M273-official-GPU-exact-latest-global-detail-binary",
        "status": "PASS_EXACT_LATEST_VIEW_SMALL_SUITE" if suite_pass else "FAIL_EXACT_LATEST_VIEW_SMALL_SUITE",
        "classification": (
            "Exact boardable NumPy view and official Mage-VL NF4/BF16 four-example regression only; "
            "not calibrated accuracy, board semantics, TTFT or promotion."
        ),
        "predecessor_m272_sha256": sha256(m272_path),
        "source_frame_policy": "latest alarm frame only",
        "views": ["exact 2x2 area-average global 224", "exact centered native 224 detail"],
        "prompt": M273_KNIFE_PROMPT,
        "records": records,
        "suite_pass": suite_pass,
        "visual_tokens": 98,
        "official_prompt_tokens": prompt_tokens,
        "t32_batches": batches,
        "logical_calls": calls,
        "call_reduction_vs_m269_percent": 100.0 * (1.0 - calls / 1394.0),
        "model": "microsoft/Mage-VL",
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "semantic_accuracy_passed": False,
        "threshold_calibrated": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": "Only if PASS, add exact PS runtime/cache and composed import closure before any board package.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(f"M273_GPU_EXACT_{'PASS' if suite_pass else 'FAIL'} prompt={prompt_tokens} calls={calls}")
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
