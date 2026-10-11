#!/usr/bin/env python3
"""Scan old owner-provided clips for a genuine, unchanged M254 knife alarm.

This is functional fixture selection only, never an accuracy evaluation.
Browser canvas and OpenCV use slightly different resampling, so a host hit
still requires confirmation using the actual Web RGB448 input on KV260.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision.models.detection import ssdlite320_mobilenet_v3_large

CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
ALARM_THRESHOLD = 0.80


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--videos", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if digest(args.checkpoint) != CHECKPOINT_SHA:
        raise RuntimeError("detector checkpoint identity mismatch")
    torch.set_num_threads(4)
    model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval().cuda()
    rows = []
    with torch.inference_mode():
        for video in args.videos:
            capture = cv2.VideoCapture(str(video))
            if not capture.isOpened():
                raise RuntimeError(f"cannot open {video}")
            count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            indices = np.linspace(0, count - 1, min(args.samples, count), dtype=np.int64)
            samples = []
            for index in indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
                ok, bgr = capture.read()
                if not ok:
                    raise RuntimeError(f"cannot decode {video} frame {index}")
                height, width = bgr.shape[:2]
                side = min(height, width)
                x, y = (width - side) // 2, (height - side) // 2
                cropped = bgr[y:y + side, x:x + side]
                rgb = cv2.cvtColor(cv2.resize(cropped, (448, 448)), cv2.COLOR_BGR2RGB)
                tensor = torch.from_numpy(rgb).permute(2, 0, 1).contiguous().float().div_(255).cuda()
                prediction = model([tensor])[0]
                labels = prediction["labels"].cpu().numpy()
                scores = prediction["scores"].cpu().numpy()
                knives = scores[labels == 49]
                samples.append({"frame_index": int(index),
                                "knife_top_score": float(knives.max()) if knives.size else None})
            capture.release()
            maximum = max((s["knife_top_score"] for s in samples if s["knife_top_score"] is not None),
                          default=None)
            rows.append({"video": video.name, "sha256": digest(video), "frames": count,
                         "max_knife_score": maximum,
                         "sampled_alarm_count": sum(s["knife_top_score"] is not None and
                                                    s["knife_top_score"] >= ALARM_THRESHOLD for s in samples),
                         "samples": samples})
    result = {"gate": "M333-historical-real-detector-trigger-search", "status": "MEASURED",
              "classification": "Host fixture search with approximate browser crop; no board alarm or quality claim",
              "checkpoint_sha256": CHECKPOINT_SHA, "unchanged_alarm_threshold": ALARM_THRESHOLD,
              "videos": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "MEASURED", "clips": [
        {k: row[k] for k in ("video", "max_knife_score", "sampled_alarm_count")} for row in rows]}))


if __name__ == "__main__":
    main()
