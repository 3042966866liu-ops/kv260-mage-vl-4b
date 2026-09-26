#!/usr/bin/env python3
"""M276 exact five-batch prompt over the unchanged M273 views."""

from __future__ import annotations

from pathlib import Path

from m273_latest_multiscale_contract import (
    IMAGE_PAD,
    VISION_END,
    VISION_START,
    VISUAL_TOKENS_PER_VIEW,
    VIEW_COUNT,
    make_views,
    preprocess,
)


M276_KNIFE_PROMPT = (
    "[TELLME_KNIFE_BINARY_V3] Knife visible? "
    "Reply exactly 1 for yes or 0 for no:"
)


def render(_external_prompt: str, timestamp_seconds: float) -> str:
    frames = "".join(
        f"<{timestamp_seconds:.1f} seconds>{VISION_START}"
        f"{IMAGE_PAD * VISUAL_TOKENS_PER_VIEW}{VISION_END}"
        for _ in range(VIEW_COUNT)
    )
    return (
        "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{frames}{M276_KNIFE_PROMPT}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def tokenize(tokenizer_json: Path, external_prompt: str, timestamp_seconds: float) -> list[int]:
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    return [
        int(value)
        for value in tokenizer.encode(render(external_prompt, timestamp_seconds), add_special_tokens=False).ids
    ]


__all__ = ["M276_KNIFE_PROMPT", "make_views", "preprocess", "render", "tokenize"]
