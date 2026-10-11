#!/usr/bin/env python3
"""Generate the fixed four-frame M90 fixture with the official Mage-VL processor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from transformers import AutoProcessor


PROMPT = "Describe the motion and color change in this short video in one sentence."


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def frames(frame_count: int = 4, size: int = 448) -> tuple[list[Image.Image], np.ndarray]:
    result: list[Image.Image] = []
    square = max(24, size // 5)
    for index in range(frame_count):
        ratio = index / max(1, frame_count - 1)
        background = (
            int(round(30 + 150 * ratio)),
            int(round(70 + 80 * (1.0 - ratio))),
            int(round(190 - 130 * ratio)),
        )
        image = Image.new("RGB", (size, size), background)
        draw = ImageDraw.Draw(image)
        x = int(round((size - square) * ratio))
        y = (size - square) // 2
        draw.rectangle((x, y, x + square, y + square), fill=(245, 225, 40))
        draw.text((12, 12), f"frame {index + 1}", fill=(255, 255, 255))
        result.append(image)
    return result, np.stack([np.asarray(image, dtype=np.uint8) for image in result])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    model = args.model.resolve()
    processor = AutoProcessor.from_pretrained(model, trust_remote_code=True, local_files_only=True)
    pil_frames, raw_frames = frames()
    messages = [{"role": "user", "content": [{"type": "video"}, {"type": "text", "text": PROMPT}]}]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded = processor(text=[rendered], videos=[pil_frames], return_tensors="pt", padding=True)
    tensors = {
        "frames_rgb_u8": raw_frames,
        "pixel_values": encoded["pixel_values"].detach().cpu().numpy(),
        "image_grid_thw": encoded["image_grid_thw"].detach().cpu().numpy(),
        "patch_positions": encoded["patch_positions"].detach().cpu().numpy(),
        "input_ids": encoded["input_ids"].detach().cpu().numpy(),
        "attention_mask": encoded["attention_mask"].detach().cpu().numpy(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp.npz")
    np.savez_compressed(temporary, **tensors)
    os.replace(temporary, args.output)
    payload = {
        "gate": "M90-official-four-frame-video-processor-fixture",
        "status": "PASS",
        "model": "microsoft/Mage-VL",
        "model_path": str(model),
        "prompt": PROMPT,
        "rendered_prompt": rendered,
        "shapes": {name: list(value.shape) for name, value in tensors.items()},
        "dtypes": {name: str(value.dtype) for name, value in tensors.items()},
        "fixture_sha256": sha256(args.output),
        "fixture_bytes": args.output.stat().st_size,
        "input_token_count": int(tensors["input_ids"].shape[1]),
        "visual_patch_count": int(tensors["pixel_values"].shape[0]),
        "merged_visual_token_count": int(tensors["pixel_values"].shape[0] // 4),
    }
    rendered_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary_result = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary_result.write_text(rendered_json, encoding="utf-8")
    os.replace(temporary_result, args.result)
    print("M90_OFFICIAL_VIDEO_PROCESSOR_FIXTURE_PASS")
    print(rendered_json, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
