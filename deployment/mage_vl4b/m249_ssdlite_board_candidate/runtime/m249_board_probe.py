#!/usr/bin/env python3
"""Hash-locked KV260 A53 speed probe for the M249 SSDLite fast safety path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

import numpy as np


CHECKPOINT_SHA256 = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
FIXTURE_VIDEO_SHA256 = "10574ca38dd1d1d682277bd70dde067e9b78fcf1d0677e160e57d635769bd0a0"
PERSON_LABEL = 1
KNIFE_LABEL = 49
PERSON_THRESHOLD = 0.50
KNIFE_THRESHOLD = 0.20
FAST_PATH_TARGET_MS = 5000.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--allow-host-codepath", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    candidate = args.candidate.resolve()
    result = {
        "date": "2026-09-02",
        "gate": "M249-KV260-A53-SSDLite-person-knife-speed",
        "status": "FAIL",
        "classification": (
            "Fixed-frame KV260 A53 detector speed and functional sanity evidence only; "
            "not target-scene accuracy, action recognition, FPGA execution, Web or continuous-stream PASS."
        ),
        "board_state_changed": False,
        "stable_t32_overlay_preserved": True,
    }
    try:
        architecture = platform.machine().lower()
        is_board_architecture = architecture in {"aarch64", "arm64"}
        if not is_board_architecture and not args.allow_host_codepath:
            raise RuntimeError(f"KV260 AArch64 required, observed: {platform.machine()}")
        if args.threads < 1 or args.threads > 4:
            raise RuntimeError("thread count must be in [1,4]")
        checkpoint = candidate / "model/ssdlite320_mobilenet_v3_large_coco-a79551df.pth"
        fixture_manifest_path = candidate / "fixtures/FIXTURE_MANIFEST.json"
        if sha256(checkpoint) != CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint hash mismatch")
        fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
        if fixture_manifest.get("status") != "PASS" or fixture_manifest.get("source_video_sha256") != FIXTURE_VIDEO_SHA256:
            raise RuntimeError("fixture identity mismatch")
        fixture_entries = fixture_manifest.get("files")
        if not isinstance(fixture_entries, list) or len(fixture_entries) != 4:
            raise RuntimeError("exactly four fixed fixtures required")
        for item in fixture_entries:
            path = candidate / "fixtures" / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"fixture closure mismatch: {item['path']}")

        import torch
        import torchvision
        from torchvision.models.detection import ssdlite320_mobilenet_v3_large

        torch.set_num_threads(args.threads)
        torch.set_num_interop_threads(1)
        model_load_started = time.monotonic()
        model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
        model.eval()
        model_load_ms = (time.monotonic() - model_load_started) * 1000.0

        tensors = []
        for item in fixture_entries:
            frame = np.load(candidate / "fixtures" / item["path"], allow_pickle=False)
            if frame.shape != (448, 448, 3) or frame.dtype != np.uint8:
                raise RuntimeError(f"invalid fixture tensor: {item['path']}")
            tensors.append(torch.from_numpy(frame).permute(2, 0, 1).contiguous().float().div_(255.0))

        print("M249_MODEL_READY", flush=True)
        with torch.inference_mode():
            warm_started = time.monotonic()
            warm_prediction = model([tensors[0]])[0]
            warmup_ms = (time.monotonic() - warm_started) * 1000.0
            if not torch.isfinite(warm_prediction["scores"]).all():
                raise RuntimeError("non-finite warm-up output")
            records = []
            for item, tensor in zip(fixture_entries, tensors):
                frame_started = time.monotonic()
                prediction = model([tensor])[0]
                elapsed_ms = (time.monotonic() - frame_started) * 1000.0
                labels = prediction["labels"].detach().cpu().numpy()
                scores = prediction["scores"].detach().cpu().numpy()
                boxes = prediction["boxes"].detach().cpu().numpy()
                if not np.isfinite(scores).all() or not np.isfinite(boxes).all():
                    raise RuntimeError(f"non-finite output: {item['path']}")
                person_scores = scores[labels == PERSON_LABEL]
                knife_scores = scores[labels == KNIFE_LABEL]
                record = {
                    "frame_index": item["frame_index"],
                    "fixture_sha256": item["sha256"],
                    "inference_ms": elapsed_ms,
                    "person_top_score": float(person_scores.max()) if person_scores.size else None,
                    "person_count_score_ge_0_50": int(np.count_nonzero(person_scores >= PERSON_THRESHOLD)),
                    "knife_top_score": float(knife_scores.max()) if knife_scores.size else None,
                    "knife_count_score_ge_0_20": int(np.count_nonzero(knife_scores >= KNIFE_THRESHOLD)),
                }
                records.append(record)
                print(
                    f"M249_FRAME_MEASURED index={item['frame_index']} elapsed_ms={elapsed_ms:.3f} "
                    f"persons={record['person_count_score_ge_0_50']} knives={record['knife_count_score_ge_0_20']}",
                    flush=True,
                )

        timings = [record["inference_ms"] for record in records]
        person_frames = sum(record["person_count_score_ge_0_50"] > 0 for record in records)
        median_ms = float(np.median(np.asarray(timings, dtype=np.float64)))
        maximum_ms = float(max(timings))
        deadline_pass = maximum_ms <= FAST_PATH_TARGET_MS
        sanity_pass = person_frames >= 3
        accepted = deadline_pass and sanity_pass
        result.update({
            "gate": (
                "M249-KV260-A53-SSDLite-person-knife-speed"
                if is_board_architecture
                else "M249-host-codepath-SSDLite-person-knife"
            ),
            "status": (
                "PASS" if accepted and is_board_architecture
                else "PASS_HOST_CODEPATH" if accepted
                else "FAIL"
            ),
            "architecture": platform.machine(),
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "threads": args.threads,
            "model_checkpoint_sha256": CHECKPOINT_SHA256,
            "fixture_manifest_sha256": sha256(fixture_manifest_path),
            "model_load_ms": model_load_ms,
            "warmup_ms": warmup_ms,
            "timing": {
                "median_frame_ms": median_ms,
                "maximum_frame_ms": maximum_ms,
                "fast_path_target_ms": FAST_PATH_TARGET_MS,
                "deadline_pass": deadline_pass,
            },
            "functional_sanity": {
                "person_frames_score_ge_0_50": person_frames,
                "required_person_frames": 3,
                "pass": sanity_pass,
                "thresholds_calibrated": False,
            },
            "records": records,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
            "next_gate": (
                "Connect detector events to the M248 safety contract and measure a latest-only continuous stream."
                if accepted and is_board_architecture
                else "Run the unchanged hash-locked candidate on the KV260 A53."
                if accepted
                else "Do not integrate Web; profile or replace the detector at the failed M249 speed/sanity level."
            ),
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun only M249; do not integrate Web or claim real-time detection."
    result["total_ms"] = (time.monotonic() - started) * 1000.0
    atomic_json(args.result.resolve(), result)
    print("__M249_BOARD_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M249_BOARD_RESULT_END__", flush=True)
    if result["status"] == "PASS":
        print("M249_KV260_SSDLITE_SPEED_PASS", flush=True)
    elif result["status"] == "PASS_HOST_CODEPATH":
        print("M249_HOST_CODEPATH_PASS", flush=True)
    else:
        print("M249_KV260_SSDLITE_SPEED_FAIL", flush=True)
    return 0 if result["status"] in {"PASS", "PASS_HOST_CODEPATH"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
