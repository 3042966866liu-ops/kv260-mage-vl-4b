#!/usr/bin/env python3
"""Export fixed source frames and their approximate 448px browser-center views.

Diagnostic images only; OpenCV resize is not asserted byte-identical to Canvas.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--indices", type=int, nargs="+", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open {args.video}")
    try:
        for index in args.indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, bgr = capture.read()
            if not ok:
                raise RuntimeError(f"cannot decode frame {index}")
            height, width = bgr.shape[:2]
            side = min(height, width)
            x, y = (width - side) // 2, (height - side) // 2
            crop = cv2.resize(bgr[y:y + side, x:x + side], (448, 448))
            for suffix, data in (("source", bgr), ("input_approx", crop)):
                path = args.output / f"frame_{index:04d}_{suffix}.png"
                success, encoded = cv2.imencode(".png", data)
                if not success:
                    raise RuntimeError(f"cannot encode {path}")
                path.write_bytes(encoded.tobytes())
                print(path)
    finally:
        capture.release()


if __name__ == "__main__":
    main()
