#!/usr/bin/env python3
"""Read-only M337 center-zoom input ablation on exact M335 RGB448 captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision.models.detection import ssdlite320_mobilenet_v3_large


CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
APP_SHA = "3aa35208a7739cb9068796735aec78410f39f94d48041f0b41bf3cf397dfd95e"
FRAME_BYTES = 448 * 448 * 3
ZOOM_SIDE = 336  # Center 75%; no scene-specific or label-selected region.


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite: {args.output}")
    if sha(args.checkpoint) != CHECKPOINT_SHA:
        raise RuntimeError("checkpoint hash mismatch")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    if baseline["status"] != "MEASURED_OFFLINE_ONLY" or baseline["appJsSha256"] != APP_SHA:
        raise RuntimeError("baseline identity mismatch")
    baseline_by_name = {video["video"]: video for video in baseline["videos"]}
    if len(baseline_by_name) != 6 or baseline["samplePlan"] != "all2fps":
        raise RuntimeError("expected six full 2-FPS baseline clips")

    torch.set_num_threads(4)
    model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    start = (448 - ZOOM_SIDE) // 2
    videos = []
    with torch.inference_mode():
        for name, base in sorted(baseline_by_name.items()):
            directory = args.capture_root / Path(name).stem
            capture = json.loads((directory / "RESULT.json").read_text(encoding="utf-8"))
            if sha(directory / "RESULT.json") != base["captureResultSha256"]:
                raise RuntimeError(f"capture result hash mismatch: {name}")
            if capture["sourceVideoSha256"] != base["sourceVideoSha256"] or len(capture["rows"]) != len(base["rows"]):
                raise RuntimeError(f"source identity or frame count mismatch: {name}")
            rows = []
            for frame_meta, base_row in zip(capture["rows"], base["rows"]):
                path = directory / frame_meta["rgbFile"]
                raw = path.read_bytes()
                if len(raw) != FRAME_BYTES or sha(path) != frame_meta["rgbSha256"] or frame_meta["rgbSha256"] != base_row["rgbSha256"]:
                    raise RuntimeError(f"RGB identity mismatch: {path}")
                image = np.frombuffer(raw, dtype=np.uint8).reshape(448, 448, 3)
                crop = image[start:start + ZOOM_SIDE, start:start + ZOOM_SIDE]
                zoom = cv2.resize(crop, (448, 448), interpolation=cv2.INTER_LINEAR)
                tensor = torch.from_numpy(zoom).permute(2, 0, 1).contiguous().float().div_(255.0).to(device)
                prediction = model([tensor])[0]
                labels = prediction["labels"].cpu().numpy()
                scores = prediction["scores"].cpu().numpy()
                boxes = prediction["boxes"].cpu().numpy()
                knife_indices = np.flatnonzero(labels == 49)
                matches = sorted(({"score": float(scores[i]), "box_xyxy": [float(v) for v in boxes[i]]}
                                  for i in knife_indices), key=lambda row: row["score"], reverse=True)
                maximum = max((row["score"] for row in matches if row["score"] >= 0.05), default=0.0)
                rows.append({"seconds": frame_meta["actualSeconds"], "rgbSha256": frame_meta["rgbSha256"],
                             "baselineKnifeScore": base_row["runtimeKnifeMaxAfter0_05"],
                             "zoomKnifeScore": maximum, "zoomKnifeTop": matches[:3]})
            videos.append({"video": name, "frameCount": len(rows),
                           "baselineMax": max(row["baselineKnifeScore"] for row in rows),
                           "zoomMax": max(row["zoomKnifeScore"] for row in rows),
                           "baselineFramesAbove0_20": sum(row["baselineKnifeScore"] >= 0.20 for row in rows),
                           "zoomFramesAbove0_20": sum(row["zoomKnifeScore"] >= 0.20 for row in rows),
                           "zoomFramesAbove0_80": sum(row["zoomKnifeScore"] >= 0.80 for row in rows),
                           "rows": rows})
    result = {"gate": "M337-exact-browser-RGB448-center-75-percent-zoom-ablation",
              "status": "MEASURED_OFFLINE_ONLY", "baselineSha256": sha(args.baseline),
              "checkpointSha256": CHECKPOINT_SHA, "appJsSha256": APP_SHA,
              "zoomInput": {"cropXYXY": [start, start, start + ZOOM_SIDE, start + ZOOM_SIDE],
                            "resize": "OpenCV INTER_LINEAR to 448x448"},
              "device": device, "videos": videos,
              "boundary": "Retrospective, unlabeled, same-scene software input ablation. Not a deployed candidate or accuracy/speed PASS."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_name(args.output.name + f".partial-{os.getpid()}")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, args.output)
    print(json.dumps({"status": result["status"], "device": device,
                      "videos": [{key: video[key] for key in ("video", "frameCount", "baselineMax", "zoomMax",
                                                                  "zoomFramesAbove0_20", "zoomFramesAbove0_80")}
                                 for video in videos]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
