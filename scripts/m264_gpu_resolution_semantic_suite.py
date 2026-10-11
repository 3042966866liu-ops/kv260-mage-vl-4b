#!/usr/bin/env python3
"""M264 labelled semantic suite for Mage-VL 448 versus low-resolution input."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


PROMPT = (
    "请仅依据这两帧可见内容判断安全状态。"
    "只按以下格式回答，不要解释：刀具=有或无；人物=有或无；动作=一个简短动作。"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def square_rgb(image: Image.Image, size: int = 448) -> np.ndarray:
    fitted = ImageOps.fit(image.convert("RGB"), (size, size), method=Image.Resampling.LANCZOS)
    return np.asarray(fitted, dtype=np.uint8)


def downsample_2x(frames: np.ndarray) -> np.ndarray:
    count = int(frames.shape[0])
    values = frames.astype(np.float32).reshape(count, 224, 2, 224, 2, 3)
    return np.rint(values.mean(axis=(2, 4), dtype=np.float32)).clip(0, 255).astype(np.uint8)


def load_two_video_frames(path: Path) -> np.ndarray:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if count < 2:
        raise RuntimeError(f"video has fewer than two frames: {path}")
    selected = []
    for index in (max(0, count // 3), max(1, (2 * count) // 3)):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = capture.read()
        if not ok:
            raise RuntimeError(f"cannot decode frame {index}: {path}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        selected.append(square_rgb(Image.fromarray(rgb, mode="RGB")))
    capture.release()
    return np.stack(selected)


@dataclass(frozen=True)
class Expected:
    knife: str
    person: str
    action_any: tuple[str, ...]


@dataclass(frozen=True)
class Sample:
    name: str
    frames_448: np.ndarray
    expected: Expected
    provenance: str


class FirstTokenTimer:
    def __init__(self):
        self.prompt_seen = False
        self.first_token_time = None

    def put(self, _value):
        if not self.prompt_seen:
            self.prompt_seen = True
        elif self.first_token_time is None:
            self.first_token_time = time.perf_counter()

    def end(self):
        return None


def normalized(answer: str) -> str:
    return answer.lower().replace(" ", "").replace("：", "=")


def parse_flags(answer: str, expected: Expected) -> dict:
    compact = normalized(answer)
    knife = None
    person = None
    for value in ("有", "无"):
        if f"刀具={value}" in compact:
            knife = value
        if f"人物={value}" in compact:
            person = value
    action_match = True if not expected.action_any else any(
        marker.lower().replace(" ", "") in compact for marker in expected.action_any
    )
    return {
        "knife": knife,
        "person": person,
        "action_expected_any": list(expected.action_any),
        "action_match": action_match,
        "matches_expected": (
            knife == expected.knife and person == expected.person and action_match
        ),
    }


def prepare(processor, frames: np.ndarray):
    images = [Image.fromarray(frame, mode="RGB") for frame in frames]
    messages = [{
        "role": "user",
        "content": [{"type": "video"}, {"type": "text", "text": PROMPT}],
    }]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def run_one(model, processor, frames: np.ndarray, label: str, expected: Expected) -> dict:
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
        raise RuntimeError(f"M264 {label} generated no observable first token")
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


def build_samples(workspace: Path, examples: Path) -> list[Sample]:
    fixture_root = workspace / "deployment/mage_vl4b/m249_ssdlite_board_candidate/fixtures"
    motorcycle = np.stack([
        np.load(fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy", allow_pickle=False)
        for index, number in enumerate((68, 102, 137, 171))
    ])[[0, 3]]
    dog = square_rgb(Image.open(examples / "dog.jpg"))
    knife_path = (
        workspace / "deployment/mage_vl4b/m264_semantic_fixtures/"
        "knife_positive_businesswoman_960.jpg"
    )
    knife = square_rgb(Image.open(knife_path))
    soccer = load_two_video_frames(examples / "soccer-broadcast.mp4")
    return [
        Sample(
            "motorcycle_person_no_knife",
            motorcycle,
            Expected("无", "有", ("摩托", "骑", "驾驶", "挥手", "招手")),
            "Frozen user motorcycle frames 0 and 3 from M249 fixtures.",
        ),
        Sample(
            "soccer_people_no_knife",
            soccer,
            Expected("无", "有", ("足球", "踢球", "运动", "跑", "比赛")),
            str(examples / "soccer-broadcast.mp4"),
        ),
        Sample(
            "dog_no_person_no_knife",
            np.stack([dog, dog]),
            Expected("无", "无", ()),
            str(examples / "dog.jpg"),
        ),
        Sample(
            "businesswoman_knife_positive",
            np.stack([knife, knife]),
            Expected("有", "有", ("切", "准备", "拿刀", "持刀", "处理", "做饭", "烹饪")),
            "Wikimedia Commons CC BY 2.0 fixture documented in m264_semantic_fixtures/README.md.",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M264 requires the existing WSL CUDA environment")
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
    for sample_index, sample in enumerate(samples):
        # Alternate order to avoid always assigning the warmer second run to 224.
        variants = [
            ("M259-448", sample.frames_448),
            ("M262-224", downsample_2x(sample.frames_448)),
        ]
        if sample_index % 2:
            variants.reverse()
        measured = {
            label: run_one(model, processor, frames, f"{sample.name}:{label}", sample.expected)
            for label, frames in variants
        }
        full = measured["M259-448"]
        low = measured["M262-224"]
        records.append({
            "name": sample.name,
            "provenance": sample.provenance,
            "expected": {
                "knife": sample.expected.knife,
                "person": sample.expected.person,
                "action_any": list(sample.expected.action_any),
            },
            "full_448": full,
            "candidate_224": low,
            "full_supported": bool(full["semantic"]["matches_expected"]),
            "candidate_pass": bool(low["semantic"]["matches_expected"]),
            "candidate_regression": bool(
                full["semantic"]["matches_expected"] and not low["semantic"]["matches_expected"]
            ),
            "semantic_flags_match": (
                full["semantic"]["knife"] == low["semantic"]["knife"]
                and full["semantic"]["person"] == low["semantic"]["person"]
                and full["semantic"]["action_match"] == low["semantic"]["action_match"]
            ),
        })

    supported = [record for record in records if record["full_supported"]]
    regressions = [record["name"] for record in records if record["candidate_regression"]]
    positive_supported = any(
        record["expected"]["knife"] == "有" and record["full_supported"] for record in records
    )
    positive_candidate_pass = any(
        record["expected"]["knife"] == "有" and record["candidate_pass"] for record in records
    )
    suite_pass = (
        len(supported) == len(records)
        and not regressions
        and positive_supported
        and positive_candidate_pass
        and all(record["candidate_pass"] for record in records)
    )
    status = (
        "PASS_SMALL_LABELLED_SUITE_RESOLUTION_CANDIDATE_BOARD_STILL_PENDING"
        if suite_pass
        else "FAIL_OR_BASELINE_UNSUPPORTED_REQUIRES_RESOLUTION_SWEEP"
    )
    knife_fixture = (
        workspace / "deployment/mage_vl4b/m264_semantic_fixtures/"
        "knife_positive_businesswoman_960.jpg"
    )
    result = {
        "date": "2026-09-02",
        "gate": "M264-official-gpu-labelled-resolution-semantic-suite",
        "status": status,
        "classification": (
            "Small labelled official Mage-VL NF4/BF16 GPU resolution-regression suite; "
            "not KV260 quantized semantics, production accuracy, FPGA speed, or board promotion."
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
        "records": records,
        "supported_sample_count": len(supported),
        "sample_count": len(records),
        "candidate_regressions": regressions,
        "knife_positive_supported_by_full": positive_supported,
        "knife_positive_passed_by_candidate": positive_candidate_pass,
        "suite_pass": suite_pass,
        "semantic_accuracy_passed": False,
        "semantic_accuracy_reason": (
            "Four labelled examples are a regression screen, not a held-out target-camera dataset "
            "or calibrated accuracy measurement."
        ),
        "knife_fixture": {
            "path": str(knife_fixture),
            "sha256": sha256(knife_fixture),
            "bytes": knife_fixture.stat().st_size,
            "source_page": (
                "https://commons.wikimedia.org/wiki/"
                "File:Businesswoman_prepares_fruits_and_vegetables_in_kitchen.jpg"
            ),
            "license": "CC BY 2.0 (per source page)",
        },
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "If PASS, package the 224 candidate and wait for COM3 before a same-level isolated "
            "KV260 memory/TTFT gate. If FAIL, sweep 256/320/384 and select the smallest resolution "
            "with no supported-sample regression."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        f"M264_GPU_SEMANTIC_SUITE_{'PASS' if suite_pass else 'FAIL'} "
        f"supported={len(supported)}/{len(records)} regressions={regressions}"
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
