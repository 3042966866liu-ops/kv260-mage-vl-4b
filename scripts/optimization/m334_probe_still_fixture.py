#!/usr/bin/env python3
"""Find an unchanged M249 detector alarm in clearly identified stock stills.

Fixture selection only. A still-image hit does not validate video accuracy or
the KV260 Web route; the exact bytes must be checked again on the board.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torchvision.models.detection import ssdlite320_mobilenet_v3_large


CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--images", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if digest(args.checkpoint) != CHECKPOINT_SHA:
        raise RuntimeError("detector checkpoint SHA mismatch")
    torch.set_num_threads(4)
    model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval().cuda()
    rows = []
    with torch.inference_mode():
        for source in args.images:
            image = Image.open(source).convert("RGB")
            width, height = image.size
            side = min(width, height)
            left, top = (width - side) // 2, (height - side) // 2
            image = image.crop((left, top, left + side, top + side))
            image = image.resize((448, 448), Image.Resampling.BILINEAR)
            frame = np.asarray(image, dtype=np.uint8)
            tensor = torch.from_numpy(frame.copy()).permute(2, 0, 1).float().div_(255).cuda()
            prediction = model([tensor])[0]
            scores = prediction["scores"].cpu().numpy()
            labels = prediction["labels"].cpu().numpy()
            knives = scores[labels == 49]
            rows.append({"source": str(source), "source_sha256": digest(source),
                         "frame_rgb448_sha256": hashlib.sha256(frame.tobytes()).hexdigest(),
                         "knife_top_score": float(knives.max()) if knives.size else None,
                         "would_alarm_at_0_80": bool(knives.size and knives.max() >= 0.80)})
    result = {"gate": "M334-stock-still-unchanged-detector-fixture-search",
              "status": "MEASURED", "checkpoint_sha256": CHECKPOINT_SHA,
              "classification": "host functional-fixture search; not video or KV260 result",
              "images": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
