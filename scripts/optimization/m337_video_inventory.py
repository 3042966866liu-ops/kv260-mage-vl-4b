#!/usr/bin/env python3
"""Read-only metadata and representative-frame extraction for owner videos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    videos = sorted(args.input.glob("*.mp4"))
    if not videos:
        raise RuntimeError("no MP4 files found")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for video in videos:
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            rows.append({"filename": video.name, "status": "OPEN_FAILED"})
            continue
        try:
            frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            samples = []
            for fraction in (0.05, 0.25, 0.50, 0.75, 0.95):
                index = min(frames - 1, int(round((frames - 1) * fraction)))
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok:
                    samples.append({"frame_index": index, "status": "DECODE_FAILED"})
                    continue
                destination = args.output / f"{video.stem}_{index:06d}.png"
                if not cv2.imwrite(str(destination), frame):
                    raise RuntimeError(f"cannot write frame {destination}")
                samples.append({"frame_index": index, "seconds": index / fps if fps else None,
                                "path": str(destination)})
            rows.append({"filename": video.name, "status": "MEASURED", "frame_count": frames,
                         "fps": fps, "duration_seconds": frames / fps if fps else None,
                         "width": width, "height": height, "samples": samples})
        finally:
            capture.release()
    result = {"gate": "M337-owner-video-read-only-inventory", "videos": rows,
              "scope": "Representative stills only; no full semantic/temporal validation or upload."}
    (args.output / "INVENTORY.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
