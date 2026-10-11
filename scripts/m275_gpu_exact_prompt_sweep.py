#!/usr/bin/env python3
"""Screen shorter prompts on the exact M273 two-view inputs."""

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


EXPECTED_M273_SHA256 = "23e53a0e020c169e5dcaf4a191835bc0f37dba7e58026495b5c37cb23eea36c7"
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(processor, views, prompt):
    images = [Image.fromarray(frame, mode="RGB") for frame in views]
    messages = [{"role": "user", "content": [{"type": "video"}, {"type": "text", "text": prompt}]}]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m273", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    m273_path = args.m273.resolve()
    if sha256(m273_path) != EXPECTED_M273_SHA256:
        raise RuntimeError("M275 M273 predecessor hash mismatch")
    predecessor = json.loads(m273_path.read_text(encoding="utf-8"))
    if not predecessor.get("suite_pass"):
        raise RuntimeError("M275 requires M273 exact-view PASS")
    source = workspace / "deployment/mage_vl4b/m273_latest_binary_source"
    sys.path.insert(0, str(source))
    from m273_latest_multiscale_contract import M273_KNIFE_PROMPT, make_views
    m246 = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path.insert(0, str(m246))
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_YES_TOKEN_ID

    prompts = (
        ("m273_v2_baseline", M273_KNIFE_PROMPT),
        ("tagged_short", "[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:"),
        ("plain_exact", "Is a knife visible? Reply with exactly 1 for yes or 0 for no:"),
        ("plain_minimal", "Knife visible? Answer only 1 or 0:"),
    )
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig
    if not torch.cuda.is_available():
        raise RuntimeError("M275 requires existing WSL CUDA")
    model_path = args.model.resolve()
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True, quantization_config=quant,
        device_map="auto", low_cpu_mem_usage=True,
    ).eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0
    samples = build_samples(workspace, args.examples.resolve())
    candidates = []
    for name, prompt in prompts:
        records = []
        for sample in samples:
            views = make_views(sample.frames_448[-1:])
            inputs = prepare(processor, views, prompt)
            moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
            started = time.perf_counter()
            with torch.inference_mode():
                output = model(**moved, use_cache=False)
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
                "absolute_decision_margin": abs(yes_logit - no_logit),
                "prompt_tokens": int(moved["input_ids"].shape[1]),
                "forward_ms": (time.perf_counter() - started) * 1000.0,
            })
        counts = {record["prompt_tokens"] for record in records}
        if len(counts) != 1:
            raise RuntimeError(f"M275 prompt geometry mismatch {name}")
        tokens = counts.pop()
        batches = math.ceil(tokens / 32)
        calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
        candidates.append({
            "name": name,
            "prompt": prompt,
            "records": records,
            "suite_pass": len(records) == 4 and all(record["pass"] for record in records),
            "minimum_absolute_margin": min(record["absolute_decision_margin"] for record in records),
            "prompt_tokens": tokens,
            "visual_tokens": 98,
            "t32_batches": batches,
            "logical_calls": calls,
            "call_reduction_vs_m273_percent": 100.0 * (1.0 - calls / 932.0),
        })
    passing = [item for item in candidates if item["suite_pass"]]
    selected = None if not passing else sorted(
        passing, key=lambda item: (item["logical_calls"], -item["minimum_absolute_margin"], item["name"])
    )[0]["name"]
    result = {
        "date": "2026-09-02",
        "gate": "M275-official-GPU-exact-two-view-prompt-sweep",
        "status": "PASS_SCREEN_HAS_SHORT_PROMPT" if selected else "FAIL_NO_SHORT_PROMPT",
        "classification": "Exact M273 views with small official-GPU prompt regression only; not calibrated accuracy, KV260 TTFT or promotion.",
        "predecessor_m273_sha256": sha256(m273_path),
        "candidates": candidates,
        "selected_for_further_validation": selected,
        "selection_rule": "Fewest calls among 4/4 passes, then largest minimum absolute two-token margin.",
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
        "next_gate": "Only a 4/4 candidate may be frozen into an exact tokenizer/runtime and rerun through full closure before board use.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M275_PROMPT_SWEEP_" + ("PASS" if selected else "FAIL") + f" selected={selected} " + " ".join(f"{item['name']}:{item['suite_pass']}/{item['prompt_tokens']}/{item['logical_calls']}" for item in candidates))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
