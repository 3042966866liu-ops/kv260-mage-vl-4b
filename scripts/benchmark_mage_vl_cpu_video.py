#!/usr/bin/env python3
"""Matched-method CPU benchmark for Microsoft's Mage-VL video model."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import threading
import time
from pathlib import Path

import psutil
import torch
from transformers import AutoModelForCausalLM, AutoProcessor


OFFICIAL_REVISION = "d88b153285f1633a61b2f693c59c8576693af185"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, default=Path("/home/lyy/models/Mage-VL"))
    parser.add_argument(
        "--video",
        type=Path,
        default=Path("/home/lyy/models/Mage-VL/examples/soccer-broadcast.mp4"),
    )
    parser.add_argument("--question", default="Describe this video.")
    parser.add_argument("--num-frames", type=int, default=32)
    parser.add_argument("--warmup-tokens", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def sample_video(video: Path, num_frames: int):
    import cv2
    import numpy as np
    from PIL import Image

    capture = cv2.VideoCapture(str(video))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if frame_count <= 0:
        capture.release()
        raise ValueError(f"could not read video: {video}")
    indices = np.linspace(0, frame_count - 1, min(num_frames, frame_count), dtype=int)
    frames = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise ValueError(f"could not decode frame {index} from {video}")
        frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    capture.release()
    return frames, frame_count, fps


def checkpoint_weight_bytes(model_path: Path) -> int:
    index = json.loads((model_path / "model.safetensors.index.json").read_text())
    metadata = index.get("metadata", {})
    if "total_size" in metadata:
        return int(metadata["total_size"])
    files = {str(name) for name in index["weight_map"].values()}
    return sum((model_path / name).stat().st_size for name in files)


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


class PeakRssMonitor:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.wait(0.02):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.stop_event.set()
        self.thread.join()
        self.peak = max(self.peak, self.process.memory_info().rss)


class FirstTokenTimer:
    """Minimal Transformers streamer that timestamps the first generated token."""

    def __init__(self) -> None:
        self.prompt_seen = False
        self.first_token_time: float | None = None

    def put(self, value) -> None:
        if not self.prompt_seen:
            self.prompt_seen = True
            return
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()

    def end(self) -> None:
        return None


def rss_gib() -> float:
    return psutil.Process().memory_info().rss / 2**30


def prepare_inputs(processor, video: Path, question: str, num_frames: int):
    frames, frame_count, fps = sample_video(video, num_frames)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video"},
                {"type": "text", "text": question},
            ],
        }
    ]
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    started = time.perf_counter()
    inputs = processor(
        text=[text], videos=[frames], return_tensors="pt", padding=True
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    tensor_shapes = {
        key: list(value.shape)
        for key, value in inputs.items()
        if hasattr(value, "shape")
    }
    return inputs, {
        "video_file": str(video),
        "video_bytes": video.stat().st_size,
        "source_frames": frame_count,
        "source_fps": fps,
        "sampled_frames": len(frames),
        "processing_ms": elapsed_ms,
        "input_ids": int(inputs["input_ids"].shape[1]),
        "processor_tensor_shapes": tensor_shapes,
        "video_grid_thw": (
            inputs["video_grid_thw"].tolist()
            if "video_grid_thw" in inputs
            else None
        ),
    }


@torch.inference_mode()
def generate_profile(model, tokenizer, inputs: dict, max_new_tokens: int) -> dict:
    timer = FirstTokenTimer()
    started = time.perf_counter()
    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        streamer=timer,
    )
    finished = time.perf_counter()
    if timer.first_token_time is None:
        raise RuntimeError("streamer did not observe a generated token")
    prompt_tokens = int(inputs["input_ids"].shape[1])
    generated = [int(value) for value in output[0, prompt_tokens:].tolist()]
    decode_ms = (finished - timer.first_token_time) * 1000.0
    return {
        "generated_tokens": len(generated),
        "token_ids": generated,
        "answer": tokenizer.decode(generated, skip_special_tokens=True).strip(),
        "ttft_ms": (timer.first_token_time - started) * 1000.0,
        "decode_after_first_ms": decode_ms,
        "request_wall_ms": (finished - started) * 1000.0,
        "later_token_ms": decode_ms / max(1, len(generated) - 1),
        "decode_tokens_per_second": max(1, len(generated) - 1)
        / max(finished - timer.first_token_time, 1e-12),
        "rss_gib": rss_gib(),
    }


def average(rows: list[dict], key: str) -> float:
    return statistics.fmean(float(row[key]) for row in rows)


def write_result(result: dict, output: Path | None) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
    print(rendered, end="")


def main() -> int:
    args = parse_args()
    if min(args.num_frames, args.warmup_tokens, args.max_new_tokens, args.runs, args.threads) < 1:
        raise ValueError("frame/token/run/thread counts must be positive")
    if not args.model_path.is_dir() or not args.video.is_file():
        raise FileNotFoundError("model snapshot or official sample video is incomplete")

    source_weight_bytes = checkpoint_weight_bytes(args.model_path)
    dtype_bytes = 4 if args.dtype == "float32" else 2
    expanded_weight_bytes = source_weight_bytes * dtype_bytes // 2
    memory = psutil.virtual_memory()
    preflight = {
        "wsl_total_gib": memory.total / 2**30,
        "wsl_available_gib": memory.available / 2**30,
        "source_checkpoint_weight_gib": source_weight_bytes / 2**30,
        "expanded_weight_gib": expanded_weight_bytes / 2**30,
        "required_weight_plus_2gib_reserve_gib": (expanded_weight_bytes + 2**31) / 2**30,
        "pass": memory.total >= expanded_weight_bytes + 2**31,
    }
    base = {
        "date": time.strftime("%Y-%m-%d"),
        "gate": "microsoft-mage-vl-cpu-video-baseline",
        "model": "microsoft/Mage-VL",
        "official_revision": OFFICIAL_REVISION,
        "model_path": str(args.model_path),
        "device": "cpu under WSL2",
        "cpu": cpu_name(),
        "threads": args.threads,
        "interop_threads": 1,
        "dtype": args.dtype,
        "torch_version": torch.__version__,
        "transformers_version": __import__("transformers").__version__,
        "method": "one excluded 2-token warm-up followed by four measured 8-token runs",
        "memory_preflight": preflight,
    }
    if args.preflight_only or not preflight["pass"]:
        base.update(
            {
                "status": "PASS" if preflight["pass"] else "BLOCKED_INSUFFICIENT_WSL_MEMORY",
                "model_loaded": False,
                "reason": None
                if preflight["pass"]
                else "checkpoint weights plus a 2 GiB runtime reserve exceed the WSL memory limit",
            }
        )
        write_result(base, args.output)
        return 0 if preflight["pass"] else 2

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
    with PeakRssMonitor() as peak:
        processor = AutoProcessor.from_pretrained(
            args.model_path, trust_remote_code=True, local_files_only=True
        )
        load_started = time.perf_counter()
        model = AutoModelForCausalLM.from_pretrained(
            args.model_path,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=dtype,
            device_map="cpu",
            low_cpu_mem_usage=True,
        ).eval()
        load_ms = (time.perf_counter() - load_started) * 1000.0
        after_load_rss = rss_gib()
        inputs, media = prepare_inputs(
            processor, args.video, args.question, args.num_frames
        )
        inputs = {
            key: (
                value.to(dtype=dtype)
                if key in ("pixel_values", "pixel_values_videos")
                else value
            )
            for key, value in inputs.items()
        }
        after_preprocess_rss = rss_gib()
        warmup = generate_profile(
            model, processor.tokenizer, inputs, args.warmup_tokens
        )
        rows = [
            generate_profile(model, processor.tokenizer, inputs, args.max_new_tokens)
            for _ in range(args.runs)
        ]

    token_ids_match = all(row["token_ids"] == rows[0]["token_ids"] for row in rows)
    answers_match = all(row["answer"] == rows[0]["answer"] for row in rows)
    base.update(
        {
            "status": "PASS" if token_ids_match and answers_match else "FAIL_NONDETERMINISTIC",
            "model_loaded": True,
            "load_ms": load_ms,
            "rss_after_load_gib": after_load_rss,
            "rss_after_preprocess_gib": after_preprocess_rss,
            "peak_rss_gib": peak.peak / 2**30,
            "question": args.question,
            "media": media,
            "warmup": warmup,
            "runs": rows,
            "determinism": {
                "token_ids_match": token_ids_match,
                "answers_match": answers_match,
            },
            "average": {
                "ttft_ms": average(rows, "ttft_ms"),
                "decode_after_first_ms": average(rows, "decode_after_first_ms"),
                "request_wall_ms": average(rows, "request_wall_ms"),
                "later_token_ms": average(rows, "later_token_ms"),
                "decode_tokens_per_second": average(rows, "decode_tokens_per_second"),
            },
            "median": {
                "ttft_ms": statistics.median(float(row["ttft_ms"]) for row in rows),
                "later_token_ms": statistics.median(
                    float(row["later_token_ms"]) for row in rows
                ),
            },
        }
    )
    write_result(base, args.output)
    return 0 if base["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
