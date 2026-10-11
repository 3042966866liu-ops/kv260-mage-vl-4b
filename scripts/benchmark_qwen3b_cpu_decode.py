#!/usr/bin/env python3
"""Measure Qwen2.5-3B CPU Prefill and token-by-token Decode separately."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time

import psutil
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path", default="/home/lyy/models/Qwen2.5-3B-Instruct"
    )
    parser.add_argument(
        "--prompt", default="请用一句完整的话介绍现场可编程门阵列的用途。"
    )
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--threads", type=int, default=20)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="float32")
    return parser.parse_args()


@torch.inference_mode()
def generate_profile(model, tokenizer, prompt: str, max_new_tokens: int) -> dict:
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    encoded = tokenizer(text, return_tensors="pt")
    input_ids = encoded["input_ids"]
    attention_mask = encoded["attention_mask"]

    started = time.perf_counter()
    output = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=True)
    next_token = torch.argmax(output.logits[:, -1, :], dim=-1, keepdim=True)
    first_token_ready = time.perf_counter()
    generated = [int(next_token.item())]
    past = output.past_key_values

    for _ in range(1, max_new_tokens):
        attention_mask = torch.cat(
            (attention_mask, torch.ones((1, 1), dtype=attention_mask.dtype)), dim=1
        )
        output = model(
            input_ids=next_token,
            attention_mask=attention_mask,
            past_key_values=past,
            use_cache=True,
        )
        past = output.past_key_values
        next_token = torch.argmax(output.logits[:, -1, :], dim=-1, keepdim=True)
        generated.append(int(next_token.item()))

    finished = time.perf_counter()
    ttft_ms = (first_token_ready - started) * 1000.0
    decode_ms = (finished - first_token_ready) * 1000.0
    return {
        "prompt_tokens": int(input_ids.shape[1]),
        "generated_tokens": len(generated),
        "token_ids": generated,
        "answer": tokenizer.decode(generated, skip_special_tokens=True),
        "ttft_ms": ttft_ms,
        "decode_after_first_ms": decode_ms,
        "request_wall_ms": (finished - started) * 1000.0,
        "later_token_ms": decode_ms / max(1, len(generated) - 1),
        "decode_tokens_per_second": max(1, len(generated) - 1) / max(
            finished - first_token_ready, 1e-12
        ),
    }


def mean(rows: list[dict], key: str) -> float:
    return statistics.fmean(float(row[key]) for row in rows)


def main() -> int:
    args = parse_args()
    if args.max_new_tokens < 2 or args.runs < 1 or args.threads < 1:
        raise ValueError("max-new-tokens >= 2, runs >= 1 and threads >= 1 are required")

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    load_started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=dtype,
        device_map="cpu",
        trust_remote_code=True,
    )
    model.eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0

    warmup = generate_profile(model, tokenizer, args.prompt, 2)
    rows = [
        generate_profile(model, tokenizer, args.prompt, args.max_new_tokens)
        for _ in range(args.runs)
    ]
    result = {
        "gate": "qwen25-3b-cpu-decode-baseline",
        "status": "PASS",
        "model_path": args.model_path,
        "model_type": str(model.config.model_type),
        "torch_version": torch.__version__,
        "transformers_version": __import__("transformers").__version__,
        "device": "cpu",
        "cpu": os.popen("lscpu | sed -n 's/^Model name:[[:space:]]*//p'").read().strip(),
        "threads": args.threads,
        "interop_threads": torch.get_num_interop_threads(),
        "dtype": args.dtype,
        "load_ms": load_ms,
        "process_rss_gib": psutil.Process().memory_info().rss / 1024**3,
        "prompt": args.prompt,
        "max_new_tokens": args.max_new_tokens,
        "warmup": warmup,
        "runs": rows,
        "average": {
            "ttft_ms": mean(rows, "ttft_ms"),
            "decode_after_first_ms": mean(rows, "decode_after_first_ms"),
            "request_wall_ms": mean(rows, "request_wall_ms"),
            "later_token_ms": mean(rows, "later_token_ms"),
            "decode_tokens_per_second": mean(rows, "decode_tokens_per_second"),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
