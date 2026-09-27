#!/usr/bin/env python3
"""Score exact browser RGB448 capture with unchanged M249 SSDLite weights.

Offline diagnostic only. It does not change thresholds or assert board parity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torchvision.models.detection import ssdlite320_mobilenet_v3_large


CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
FRAME_BYTES = 448 * 448 * 3


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--positive", required=True, type=Path)
    parser.add_argument("--negative", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if sha(args.checkpoint) != CHECKPOINT_SHA:
        raise RuntimeError("M249 checkpoint SHA-256 mismatch")
    torch.set_num_threads(4)
    model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    results = []
    with torch.inference_mode():
        for label, path in (("positive", args.positive), ("negative", args.negative)):
            raw = path.read_bytes()
            if len(raw) != FRAME_BYTES:
                raise RuntimeError(f"not RGB448: {path}")
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(448, 448, 3)
            tensor = torch.from_numpy(frame.copy()).permute(2, 0, 1).contiguous().float().div_(255.0).to(device)
            prediction = model([tensor])[0]
            labels = prediction["labels"].cpu().numpy()
            scores = prediction["scores"].cpu().numpy()
            boxes = prediction["boxes"].cpu().numpy()
            matches = []
            for target, name in ((1, "person"), (49, "knife")):
                for index in np.flatnonzero(labels == target):
                    matches.append({"class": name, "score": float(scores[index]),
                                    "box_xyxy": [float(v) for v in boxes[index]]})
            matches.sort(key=lambda row: row["score"], reverse=True)
            knife_scores = [item["score"] for item in matches if item["class"] == "knife"]
            results.append({
                "label": label, "path": str(path), "sha256": sha(path),
                "raw_knife_max": max(knife_scores, default=None),
                "runtime_knife_max_after_0_05_filter": max((v for v in knife_scores if v >= 0.05), default=0),
                "detections_person_knife_top": matches[:10],
            })
    result = {
        "gate": "M336-exact-browser-RGB448-M249-detector-short-diagnostic",
        "status": "MEASURED_OFFLINE_ONLY", "checkpoint_sha256": CHECKPOINT_SHA,
        "device": device, "torch_version": torch.__version__,
        "unchanged_min_detection_score": 0.05,
        "unchanged_safe_threshold": 0.20,
        "unchanged_alarm_threshold": 0.80,
        "rows": results,
        "boundary": "Two AI-generated calibration still frames; not board parity, real-camera accuracy, or automatic alarm validation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
