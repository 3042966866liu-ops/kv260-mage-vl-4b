#!/usr/bin/env python3
"""Emit the exact TeLLMe Qwen chat-template input IDs and a stable digest."""

from __future__ import annotations

import argparse
import hashlib
import json

from tokenizers import Tokenizer


DEFAULT_PROMPT = "请用一句完整的话介绍现场可编程门阵列的用途。"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()
    rendered = (
        "<|im_start|>system\n"
        "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
        "<|im_end|>\n<|im_start|>user\n"
        + args.prompt
        + "<|im_end|>\n<|im_start|>assistant\n"
    )
    token_ids = Tokenizer.from_file(args.tokenizer).encode(
        rendered, add_special_tokens=False
    ).ids
    canonical = json.dumps(token_ids, separators=(",", ":"))
    result = {
        "gate": "qwen25-3b-chat-input-identity",
        "status": "PASS" if len(token_ids) == 44 else "FAIL",
        "prompt": args.prompt,
        "rendered": rendered,
        "token_ids": token_ids,
        "token_count": len(token_ids),
        "token_ids_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
