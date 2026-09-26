#!/usr/bin/env python3
"""Exact fixed-four-frame Mage-VL prompt expansion without Transformers."""

from __future__ import annotations

from pathlib import Path


IMAGE_PAD = "<|image_pad|>"
VISION_START = "<|vision_start|>"
VISION_END = "<|vision_end|>"
VISUAL_TOKENS_PER_FRAME = 196


def render(prompt: str) -> str:
    question = prompt.strip()
    if not question or len(question) > 3000:
        raise ValueError("prompt must contain 1..3000 characters")
    frames = "".join(
        f"<{index:.1f} seconds>{VISION_START}{IMAGE_PAD * VISUAL_TOKENS_PER_FRAME}{VISION_END}"
        for index in range(4)
    )
    return (
        "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{frames}{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def tokenize(tokenizer_json: Path, prompt: str) -> list[int]:
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise RuntimeError("the board image needs the aarch64 tokenizers wheel") from exc
    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    return [int(value) for value in tokenizer.encode(render(prompt), add_special_tokens=False).ids]
