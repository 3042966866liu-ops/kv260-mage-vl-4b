#!/usr/bin/env python3
"""Screen fewer multiscale views and a shorter binary prompt on the frozen suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from m264_gpu_resolution_semantic_suite import build_samples
from m266_gpu_multiscale_semantic_gate import multiscale_views


LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8
EXPECTED_M267_SHA256 = "4e4da9ab407cffb4ef3e544bfac159bff93f17422fda318c95ef205252339f47"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    parser.add_argument("--m267", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    m267_path = args.m267.resolve()
    if sha256(m267_path) != EXPECTED_M267_SHA256:
        raise RuntimeError("M272 frozen M267 hash mismatch")
    m267 = json.loads(m267_path.read_text(encoding="utf-8"))
    if not m267.get("suite_pass"):
        raise RuntimeError("M272 requires M267 binary baseline PASS")

    m246_root = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path.insert(0, str(m246_root))
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_PROMPT, KNIFE_YES_TOKEN_ID

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M272 requires the existing WSL CUDA environment")
    samples = build_samples(workspace, args.examples.resolve())
    expected = {
        sample.name: (1 if sample.expected.knife == "有" else 0)
        for sample in samples
    }
    prompt_v2 = (
        "[TELLME_KNIFE_BINARY_V2] Inspect these video views. "
        "Answer exactly 1 if a knife is visible, otherwise 0:"
    )
    # M266 view order is context-global, context-detail, latest-global, latest-detail.
    candidates = (
        {"name": "four_views_v1_baseline", "indices": [0, 1, 2, 3], "prompt": KNIFE_PROMPT},
        {"name": "four_views_short_prompt", "indices": [0, 1, 2, 3], "prompt": prompt_v2},
        {"name": "three_global_context_latest_pair", "indices": [0, 2, 3], "prompt": prompt_v2},
        {"name": "three_detail_context_latest_pair", "indices": [1, 2, 3], "prompt": prompt_v2},
        {"name": "two_latest_global_detail", "indices": [2, 3], "prompt": prompt_v2},
    )

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
    if list(processor.tokenizer.encode("0", add_special_tokens=False)) != [KNIFE_NO_TOKEN_ID]:
        raise RuntimeError("M272 tokenizer 0 contract mismatch")
    if list(processor.tokenizer.encode("1", add_special_tokens=False)) != [KNIFE_YES_TOKEN_ID]:
        raise RuntimeError("M272 tokenizer 1 contract mismatch")
    torch.cuda.reset_peak_memory_stats()

    outputs = []
    for candidate in candidates:
        records = []
        for sample in samples:
            all_views = multiscale_views(sample.frames_448)
            views = np.ascontiguousarray(all_views[candidate["indices"]])
            inputs = prepare(processor, views, candidate["prompt"])
            moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
            started = time.perf_counter()
            with torch.inference_mode():
                output = model(**moved, use_cache=False)
            forward_ms = (time.perf_counter() - started) * 1000.0
            logits = output.logits[0, -1].float()
            no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
            yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
            decision = 1 if yes_logit >= no_logit else 0
            records.append({
                "name": sample.name,
                "expected": expected[sample.name],
                "decision": decision,
                "pass": decision == expected[sample.name],
                "no_logit": no_logit,
                "yes_logit": yes_logit,
                "margin_yes_minus_no": yes_logit - no_logit,
                "absolute_decision_margin": abs(yes_logit - no_logit),
                "prompt_tokens": int(moved["input_ids"].shape[1]),
                "visual_tokens": len(candidate["indices"]) * 49,
                "forward_ms": forward_ms,
            })
        prompt_counts = {record["prompt_tokens"] for record in records}
        if len(prompt_counts) != 1:
            raise RuntimeError(f"M272 inconsistent prompt geometry {candidate['name']}")
        prompt_tokens = prompt_counts.pop()
        batches = math.ceil(prompt_tokens / 32)
        calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
        passed = len(records) == 4 and all(record["pass"] for record in records)
        outputs.append({
            "name": candidate["name"],
            "view_indices": candidate["indices"],
            "view_count": len(candidate["indices"]),
            "prompt": candidate["prompt"],
            "records": records,
            "suite_pass": passed,
            "minimum_absolute_margin": min(record["absolute_decision_margin"] for record in records),
            "prompt_tokens": prompt_tokens,
            "visual_tokens": len(candidate["indices"]) * 49,
            "t32_batches": batches,
            "logical_calls": calls,
            "call_reduction_vs_m269_percent": 100.0 * (1.0 - calls / 1394.0),
        })

    passing = [item for item in outputs if item["suite_pass"]]
    selected = None
    if passing:
        selected = sorted(
            passing,
            key=lambda item: (item["logical_calls"], -item["minimum_absolute_margin"], item["name"]),
        )[0]["name"]
    result = {
        "date": "2026-09-02",
        "gate": "M272-official-GPU-view-count-and-prompt-screen",
        "status": "PASS_SCREEN_HAS_CANDIDATE" if selected else "FAIL_NO_CANDIDATE",
        "classification": (
            "Small official Mage-VL NF4/BF16 binary regression screen and exact schedule geometry only; "
            "not calibrated accuracy, KV260 semantics, board TTFT or promotion."
        ),
        "predecessor_m267": str(m267_path),
        "predecessor_m267_sha256": sha256(m267_path),
        "candidates": outputs,
        "selected_for_further_validation": selected,
        "selection_rule": "Fewest logical calls among 4/4 passes, then largest minimum absolute two-token margin.",
        "model": "microsoft/Mage-VL",
        "checkpoint": str(model_path),
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "semantic_accuracy_passed": False,
        "threshold_calibrated": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "Do not replace M269 from this small screen alone. If a lower-call candidate passes, freeze its "
            "exact NumPy runtime and run the existing regression/closure chain before any later board gate."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(
        f"M272_GPU_VIEW_SWEEP_{'PASS' if selected else 'FAIL'} selected={selected} "
        + " ".join(f"{item['name']}:{item['suite_pass']}/{item['logical_calls']}" for item in outputs)
    )
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
