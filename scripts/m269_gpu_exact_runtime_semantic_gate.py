#!/usr/bin/env python3
"""M269 exact runtime-view GPU semantic gate before packaging."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from m264_gpu_resolution_semantic_suite import build_samples, sha256
from m267_gpu_multiscale_binary_knife_gate import prepare


LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m268", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()
    m268_path = args.m268.resolve()
    m268 = json.loads(m268_path.read_text(encoding="utf-8"))
    if m268.get("status") != "PASS_HASH_LOCKED_FAST_ROI_BINARY_SUITE_BOARD_PENDING":
        raise RuntimeError("M269 requires the frozen M268 fast-ROI PASS")

    source = workspace / "deployment/mage_vl4b/m269_multiscale_binary_source"
    m246_root = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path[:0] = [str(source), str(m246_root)]
    from m246_knife_binary import (  # pylint: disable=import-error,import-outside-toplevel
        KNIFE_NO_TOKEN_ID,
        KNIFE_PROMPT,
        KNIFE_YES_TOKEN_ID,
    )
    from m269_multiscale_contract import make_views  # pylint: disable=import-error,import-outside-toplevel

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M269 requires the existing WSL CUDA environment")
    samples = build_samples(workspace, examples)
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    if list(processor.tokenizer.encode("0", add_special_tokens=False)) != [KNIFE_NO_TOKEN_ID]:
        raise RuntimeError("M269 tokenizer 0 contract mismatch")
    if list(processor.tokenizer.encode("1", add_special_tokens=False)) != [KNIFE_YES_TOKEN_ID]:
        raise RuntimeError("M269 tokenizer 1 contract mismatch")
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
        expected = 1 if sample.expected.knife == "有" else 0
        exact_views = make_views(sample.frames_448)
        inputs = prepare(processor, exact_views, KNIFE_PROMPT)
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
        records.append({
            "name": sample.name,
            "expected": expected,
            "decision": decision,
            "pass": decision == expected,
            "no_logit": no_logit,
            "yes_logit": yes_logit,
            "margin_yes_minus_no": yes_logit - no_logit,
            "score_calibrated": False,
            "prompt_tokens": int(moved["input_ids"].shape[1]),
            "tensor_shapes": shapes,
            "view_shape": list(exact_views.shape),
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
        "PASS_EXACT_RUNTIME_VIEW_SMALL_BINARY_SUITE_BOARD_PENDING"
        if suite_pass
        else "FAIL_EXACT_RUNTIME_VIEW_SMALL_BINARY_SUITE"
    )
    source_files = sorted(path for path in source.iterdir() if path.is_file())
    result = {
        "date": "2026-09-02",
        "gate": "M269-exact-runtime-view-official-gpu-binary-semantic",
        "status": status,
        "classification": (
            "Exact NumPy-only M269 view-construction small official GPU regression screen; not "
            "calibrated accuracy, KV260 semantics, FPGA speed or board promotion."
        ),
        "predecessor": str(m268_path),
        "predecessor_sha256": sha256(m268_path),
        "view_contract": {
            "source_keyframes": 2,
            "per_keyframe": ["448-to-224 exact 2x2 area average", "exact centered 224 crop"],
            "processor_views": 4,
            "visual_tokens": 196,
            "new_board_runtime_dependencies": ["numpy"],
            "cv2_required_on_board": False,
        },
        "source_files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in source_files
        ],
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
        "semantic_accuracy_reason": "Four examples are a regression screen; M252 held-out metrics remain required.",
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "Run offline geometry/import/package closure, create a clean delta, then wait for COM3 "
            "for isolated KV260 memory, exact identity, binary semantics and complete TTFT."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        f"M269_GPU_EXACT_RUNTIME_SEMANTIC_{'PASS' if suite_pass else 'FAIL'} "
        f"passed={sum(record['pass'] for record in records)}/{len(records)}"
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
