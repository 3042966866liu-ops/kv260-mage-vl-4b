#!/usr/bin/env python3
"""Create deterministic 448x448 RGB fixtures for the M249 KV260 speed gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--indices", type=int, nargs="+", default=[68, 102, 137, 171])
    args = parser.parse_args()
    if not args.video.is_file():
        raise FileNotFoundError(args.video)
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError(f"clean output directory required: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {args.video}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    records = []
    for ordinal, index in enumerate(args.indices):
        if index < 0 or index >= frame_count:
            raise ValueError(f"frame index outside video: {index}/{frame_count}")
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, bgr = capture.read()
        if not ok:
            raise RuntimeError(f"failed reading frame {index}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (448, 448), interpolation=cv2.INTER_AREA)
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        name = f"frame_{ordinal:02d}_{index:04d}_rgb448.npy"
        path = args.output / name
        np.save(path, rgb, allow_pickle=False)
        records.append({
            "ordinal": ordinal,
            "frame_index": index,
            "timestamp_s": index / fps if fps > 0 else None,
            "path": name,
            "shape": list(rgb.shape),
            "dtype": str(rgb.dtype),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    capture.release()

    manifest = {
        "gate": "M249-fixed-RGB448-fixtures",
        "status": "PASS",
        "source_video_sha256": sha256(args.video),
        "frame_count": frame_count,
        "fps": fps,
        "files": records,
    }
    manifest_path = args.output / "FIXTURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print("M249_FIXED_RGB448_FIXTURES_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
