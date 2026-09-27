#!/usr/bin/env python3
"""Offline score of fixed, exact-browser RGB448 frames with the frozen M249 model.

This is an input/detector diagnostic, not a labeled accuracy or board gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from torchvision.models.detection import ssdlite320_mobilenet_v3_large


CHECKPOINT_SHA = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
FRAME_BYTES = 448 * 448 * 3
APP_SHA = "3aa35208a7739cb9068796735aec78410f39f94d48041f0b41bf3cf397dfd95e"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite existing result: {args.output}")
    if sha(args.checkpoint) != CHECKPOINT_SHA:
        raise RuntimeError("M249 checkpoint SHA-256 mismatch")
    capture_dirs = sorted(path for path in args.capture_root.iterdir() if path.is_dir())
    if len(capture_dirs) != 6:
        raise RuntimeError(f"expected six capture directories, got {len(capture_dirs)}")

    torch.set_num_threads(4)
    model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    videos = []
    plans = set()
    with torch.inference_mode():
        for directory in capture_dirs:
            capture_path = directory / "RESULT.json"
            capture = json.loads(capture_path.read_text(encoding="utf-8"))
            if capture["status"] != "PASS_BROWSER_TO_LOOPBACK" or capture["appJsSha256"] != APP_SHA:
                raise RuntimeError(f"browser identity mismatch: {directory}")
            if capture.get("samplePlan") not in {None, "fixed5", "all2fps"}:
                raise RuntimeError(f"unknown capture plan: {directory}")
            plans.add(capture.get("samplePlan", "fixed5"))
            expected = 5 if capture.get("samplePlan") in {None, "fixed5"} else len(capture["requestedTimesSeconds"])
            if len(capture["rows"]) != expected:
                raise RuntimeError(f"capture frame count mismatch: {directory}")
            rows = []
            for item in capture["rows"]:
                path = directory / item["rgbFile"]
                raw = path.read_bytes()
                if len(raw) != FRAME_BYTES or sha(path) != item["rgbSha256"]:
                    raise RuntimeError(f"RGB448 identity mismatch: {path}")
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(448, 448, 3)
                tensor = torch.from_numpy(frame.copy()).permute(2, 0, 1).contiguous().float().div_(255.0).to(device)
                prediction = model([tensor])[0]
                labels = prediction["labels"].cpu().numpy()
                scores = prediction["scores"].cpu().numpy()
                boxes = prediction["boxes"].cpu().numpy()
                matches = []
                for index in np.flatnonzero((labels == 1) | (labels == 49)):
                    matches.append({
                        "class": "person" if int(labels[index]) == 1 else "knife",
                        "score": float(scores[index]),
                        "box_xyxy": [float(v) for v in boxes[index]],
                    })
                matches.sort(key=lambda row: row["score"], reverse=True)
                knife = [row["score"] for row in matches if row["class"] == "knife"]
                person = [row["score"] for row in matches if row["class"] == "person"]
                rows.append({
                    "requestedSeconds": item["requestedSeconds"],
                    "actualSeconds": item["actualSeconds"],
                    "rgbSha256": item["rgbSha256"],
                    "rawKnifeMax": max(knife, default=None),
                    "runtimeKnifeMaxAfter0_05": max((v for v in knife if v >= 0.05), default=0.0),
                    "rawPersonMax": max(person, default=None),
                    "topPersonKnife": matches[:6],
                })
            videos.append({
                "video": directory.name + ".mp4",
                "sourceVideoSha256": capture["sourceVideoSha256"],
                "captureResultSha256": sha(capture_path),
                "rows": rows,
                "sampledKnifeScoreMax": max((row["runtimeKnifeMaxAfter0_05"] for row in rows), default=0.0),
                "sampledAlarmFrameCountAt0_80": sum(row["runtimeKnifeMaxAfter0_05"] >= 0.80 for row in rows),
            })
    if len(plans) != 1:
        raise RuntimeError(f"mixed capture plans: {sorted(plans)}")
    result = {
        "gate": "M337-real-video-exact-browser-RGB448-M249-detector",
        "status": "MEASURED_OFFLINE_ONLY",
        "checkpointSha256": CHECKPOINT_SHA,
        "appJsSha256": APP_SHA,
        "device": device,
        "torchVersion": torch.__version__,
        "samplePlan": plans.pop(),
        "unchangedMinDetectionScore": 0.05,
        "unchangedSafeThreshold": 0.20,
        "unchangedAlarmThreshold": 0.80,
        "videos": videos,
        "boundary": "Deterministic browser seeks only. No verified per-window labels, wall-clock stream, KV260 parity, accuracy or auto-alarm PASS.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps({"status": result["status"], "device": device, "frames": sum(len(v["rows"]) for v in videos),
                      "videos": [{"name": v["video"], "max": v["sampledKnifeScoreMax"],
                                  "alarm_frames": v["sampledAlarmFrameCountAt0_80"]} for v in videos]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
