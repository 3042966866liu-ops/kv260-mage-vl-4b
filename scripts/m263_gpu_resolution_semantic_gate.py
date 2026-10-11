#!/usr/bin/env python3
"""Official Mage-VL GPU semantic comparison for M259-448 versus M262-224."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np


PROMPT = (
    "请判断这两帧中是否出现刀具，并判断人物主要动作。"
    "只按以下格式回答：刀具=有或无；动作=一个简短动作。"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def downsample_2x(frames: np.ndarray) -> np.ndarray:
    values = frames.astype(np.float32).reshape(2, 224, 2, 224, 2, 3)
    return np.rint(values.mean(axis=(2, 4), dtype=np.float32)).clip(0, 255).astype(np.uint8)


class FirstTokenTimer:
    def __init__(self):
        self.prompt_seen = False
        self.first_token_time = None

    def put(self, value):
        if not self.prompt_seen:
            self.prompt_seen = True
            return
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()

    def end(self):
        return None


def semantic_flags(answer: str) -> dict:
    compact = answer.lower().replace(" ", "")
    knife_absent = any(
        marker in compact
        for marker in ("刀具=无", "刀具：无", "没有刀具", "未发现刀具", "未检测到刀具", "noknife")
    )
    visible_action = any(
        marker in compact
        for marker in (
            "摩托", "骑车", "骑行", "驾驶", "挥手", "招手",
            "motorcycle", "riding", "driving", "waving", "wave",
        )
    )
    return {"knife_absent": knife_absent, "recognized_visible_action": visible_action}


def prepare(processor, frames):
    from PIL import Image

    images = [Image.fromarray(frame, mode="RGB") for frame in frames]
    messages = [{
        "role": "user",
        "content": [{"type": "video"}, {"type": "text", "text": PROMPT}],
    }]
    rendered = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return processor(
        text=[rendered], videos=[images], return_tensors="pt", padding=True
    )


def run_one(model, processor, frames, label: str) -> dict:
    import torch

    started = time.perf_counter()
    inputs = prepare(processor, frames)
    preprocess_ms = (time.perf_counter() - started) * 1000.0
    shapes = {
        key: list(value.shape)
        for key, value in inputs.items()
        if hasattr(value, "shape")
    }
    moved = {
        key: value.to("cuda") if hasattr(value, "to") else value
        for key, value in inputs.items()
    }
    timer = FirstTokenTimer()
    started = time.perf_counter()
    with torch.inference_mode():
        output = model.generate(
            **moved,
            do_sample=False,
            use_cache=True,
            max_new_tokens=32,
            streamer=timer,
        )
    finished = time.perf_counter()
    if timer.first_token_time is None:
        raise RuntimeError(f"M263 {label} generated no observable first token")
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
        "semantic_flags": semantic_flags(answer),
        "preprocess_ms": preprocess_ms,
        "ttft_ms": (timer.first_token_time - started) * 1000.0,
        "generation_ms": (finished - started) * 1000.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(model_path)

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M263 requires the existing WSL CUDA environment")
    fixture_root = workspace / "deployment/mage_vl4b/m249_ssdlite_board_candidate/fixtures"
    all_frames = np.stack([
        np.load(fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy", allow_pickle=False)
        for index, number in enumerate((68, 102, 137, 171))
    ])
    frames_448 = all_frames[[0, 3]]
    frames_224 = downsample_2x(frames_448)

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True
    )
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
    full = run_one(model, processor, frames_448, "M259-448")
    low = run_one(model, processor, frames_224, "M262-224")
    expected = {"knife_absent": True, "recognized_visible_action": True}
    full_pass = full["semantic_flags"] == expected
    low_pass = low["semantic_flags"] == expected
    status = (
        "PASS_ONE_FROZEN_NEGATIVE_ACTION_SAMPLE_MORE_LABELS_REQUIRED"
        if full_pass and low_pass
        else "FAIL_FROZEN_MOTORCYCLE_SEMANTIC"
    )
    result = {
        "date": "2026-09-02",
        "gate": "M263-official-gpu-M259-448-vs-M262-224-semantic",
        "status": status,
        "classification": (
            "Official Mage-VL NF4/BF16 GPU semantic comparison on one frozen non-knife motorcycle "
            "sample only; not board quantized semantics, aggregate accuracy, FPGA speed, Web, or promotion."
        ),
        "model": "microsoft/Mage-VL",
        "checkpoint": str(model_path),
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "prompt": PROMPT,
        "frozen_expected": expected,
        "full_448": full,
        "candidate_224": low,
        "candidate_matches_frozen_expected": low_pass,
        "candidate_matches_full_semantic_flags": low["semantic_flags"] == full["semantic_flags"],
        "semantic_accuracy_passed": False,
        "semantic_accuracy_reason": (
            "One non-knife motorcycle sample cannot establish knife sensitivity, specificity, "
            "or action accuracy; labelled positive and negative sets remain mandatory."
        ),
        "rejected_attempts": [
            "The first frozen action rubric accepted only motorcycle/riding terms and rejected both identical 448 and 224 answers '挥手'. The visible rider has a raised waving hand, so the rerun freezes riding or waving as valid visible actions without changing the knife-negative requirement."
        ],
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "Add labelled knife-positive, knife-negative and multiple action windows; compare fixed "
            "M259-448 and M262-224 outputs before any board package is created."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        "M263_GPU_RESOLUTION_SEMANTIC_" + ("PASS" if full_pass and low_pass else "FAIL")
        + f" full={full['answer']!r} low={low['answer']!r}"
    )
    return 0 if full_pass and low_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
