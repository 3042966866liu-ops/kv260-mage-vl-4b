#!/usr/bin/env python3
"""Measure an official SSDLite person/knife baseline on a local video.

This is a host-only model-selection probe.  It deliberately reports MEASURED,
never PASS, because one unlabelled demonstration video cannot establish
accuracy or KV260 real-time performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision.models.detection import (
    SSDLite320_MobileNet_V3_Large_Weights,
    ssdlite320_mobilenet_v3_large,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=8)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if args.sample_count < 1:
        raise ValueError("sample-count must be positive")
    if not args.video.is_file():
        raise FileNotFoundError(args.video)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
    categories = list(weights.meta["categories"])
    person_label = categories.index("person")
    knife_label = categories.index("knife")
    model_load_started = time.perf_counter()
    model = ssdlite320_mobilenet_v3_large(weights=weights).eval().to(args.device)
    model_load_ms = (time.perf_counter() - model_load_started) * 1000.0

    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {args.video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if frame_count < 1:
        raise RuntimeError("video reports no frames")
    indices = np.linspace(0, frame_count - 1, num=min(args.sample_count, frame_count), dtype=np.int64)
    frames = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        ok, bgr = capture.read()
        if not ok:
            raise RuntimeError(f"failed reading frame {index}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).contiguous().float().div_(255.0)
        frames.append(tensor)
    capture.release()

    timings = []
    records = []
    with torch.inference_mode():
        for sample_index, (frame_index, frame) in enumerate(zip(indices.tolist(), frames)):
            if args.device == "cuda":
                torch.cuda.synchronize()
            started = time.perf_counter()
            prediction = model([frame.to(args.device)])[0]
            if args.device == "cuda":
                torch.cuda.synchronize()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            timings.append(elapsed_ms)
            labels = prediction["labels"].detach().cpu().numpy()
            scores = prediction["scores"].detach().cpu().numpy()
            person_scores = scores[labels == person_label]
            knife_scores = scores[labels == knife_label]
            records.append({
                "sample_index": sample_index,
                "frame_index": frame_index,
                "timestamp_s": frame_index / fps if fps > 0 else None,
                "inference_ms": elapsed_ms,
                "person_top_score": float(person_scores.max()) if person_scores.size else None,
                "person_count_score_ge_0_50": int(np.count_nonzero(person_scores >= 0.50)),
                "knife_top_score": float(knife_scores.max()) if knife_scores.size else None,
                "knife_count_score_ge_0_20": int(np.count_nonzero(knife_scores >= 0.20)),
            })

    checkpoint_name = Path(weights.url).name
    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / checkpoint_name
    result = {
        "date": "2026-09-02",
        "gate": "M249-official-SSDLite320-person-knife-host-probe",
        "status": "MEASURED",
        "classification": "Unlabelled WSL host model-selection measurement only; not accuracy, action recognition, target-scene, board, FPGA, Web or real-time evidence.",
        "model": "torchvision/ssdlite320_mobilenet_v3_large/COCO_V1",
        "torch": torch.__version__,
        "torchvision": __import__("torchvision").__version__,
        "device": args.device,
        "model_load_ms": model_load_ms,
        "model_metadata": {
            "num_params": weights.meta["num_params"],
            "ops_g": weights.meta["_ops"],
            "file_size_mib": weights.meta["_file_size"],
            "coco_box_map": weights.meta["_metrics"]["COCO-val2017"]["box_map"],
            "person_label": person_label,
            "knife_label": knife_label,
        },
        "checkpoint": {
            "path": str(checkpoint),
            "exists": checkpoint.is_file(),
            "bytes": checkpoint.stat().st_size if checkpoint.is_file() else None,
            "sha256": sha256(checkpoint) if checkpoint.is_file() else None,
        },
        "video": {
            "path": str(args.video),
            "sha256": sha256(args.video),
            "frame_count": frame_count,
            "fps": fps,
            "sample_count": len(records),
        },
        "timing": {
            "first_sample_ms": timings[0],
            "median_all_ms": float(np.median(timings)),
            "median_after_first_ms": float(np.median(timings[1:])) if len(timings) > 1 else timings[0],
            "minimum_ms": min(timings),
            "maximum_ms": max(timings),
        },
        "records": records,
        "thresholds_calibrated": False,
        "next_gate": "Inspect detections against labelled target-scene frames; export/quantize only if person and knife recall justify this candidate."
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    print("M249_SSDLITE_PERSON_KNIFE_HOST_PROBE_MEASURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
