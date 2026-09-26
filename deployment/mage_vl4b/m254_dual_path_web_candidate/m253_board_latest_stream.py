#!/usr/bin/env python3
"""Real KV260 M249 detector + M251 latest-only continuous-source pressure gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np

from fast_frame_pipeline import Detection, FastFramePipeline
from latest_fast_stream import LatestFastSafetyEngine


CHECKPOINT_SHA256 = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
M249_BOARD_RESULT_SHA256 = "e45597c3cc14a68420b09d389dde8c2b1cd81ab23eacc5833b5a527d4f633681"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class SSDLiteDetector:
    def __init__(self, checkpoint: Path, threads: int) -> None:
        self.checkpoint = checkpoint
        self.threads = threads
        self.model = None
        self.torch = None
        self.torchvision_version = None

    def load(self) -> None:
        print("M253_MODEL_IMPORT_BEGIN", flush=True)
        if sha256(self.checkpoint) != CHECKPOINT_SHA256:
            raise RuntimeError("M249 checkpoint hash mismatch")
        import torch
        import torchvision
        from torchvision.models.detection import ssdlite320_mobilenet_v3_large
        torch.set_num_threads(self.threads)
        torch.set_num_interop_threads(1)
        print("M253_MODEL_CONSTRUCT_BEGIN", flush=True)
        model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
        model.load_state_dict(torch.load(self.checkpoint, map_location="cpu", weights_only=True), strict=True)
        model.eval()
        self.model = model
        self.torch = torch
        self.torchvision_version = torchvision.__version__
        print("M253_MODEL_WARM_BEGIN", flush=True)
        with torch.inference_mode():
            warm = torch.zeros((3, 448, 448), dtype=torch.float32)
            prediction = model([warm])[0]
            if not torch.isfinite(prediction["scores"]).all():
                raise RuntimeError("non-finite detector warm-up")
        print("M253_MODEL_WARM_PASS", flush=True)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self.model is None or self.torch is None:
            raise RuntimeError("detector not loaded")
        tensor = self.torch.from_numpy(frame).permute(2, 0, 1).contiguous().float().div_(255.0)
        with self.torch.inference_mode():
            prediction = self.model([tensor])[0]
        labels = prediction["labels"].detach().cpu().numpy()
        scores = prediction["scores"].detach().cpu().numpy()
        boxes = prediction["boxes"].detach().cpu().numpy()
        detections: list[Detection] = []
        for label, score, box in zip(labels, scores, boxes):
            if int(label) not in {1, 49} or float(score) < 0.05:
                continue
            x1, y1, x2, y2 = [float(value) / 448.0 for value in box]
            normalized = (
                min(1.0, max(0.0, x1)), min(1.0, max(0.0, y1)),
                min(1.0, max(0.0, x2)), min(1.0, max(0.0, y2)),
            )
            if normalized[2] <= normalized[0] or normalized[3] <= normalized[1]:
                continue
            detections.append(Detection("person" if int(label) == 1 else "knife", float(score), normalized))
            if len(detections) >= 20:
                break
        return detections

    def close(self) -> None:
        self.model = None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m249-candidate", type=Path, required=True)
    parser.add_argument("--m249-board-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--source-fps", type=float, default=5.0)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-02",
        "gate": "M253-KV260-M249-latest-only-fast-safety-stream",
        "status": "FAIL",
        "classification": (
            "Real KV260 A53 continuous-source pressure, latest-only scheduling and structured safety-event latency; "
            "not camera/Web, target-scene knife/action accuracy, FPGA detector, or full production real-time acceptance."
        ),
        "stable_t32_overlay_preserved": True,
        "boot_dtb_cma_partitions_services_changed": False,
    }
    engine = None
    try:
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError("KV260 AArch64 required")
        if sha256(args.m249_board_result.resolve()) != M249_BOARD_RESULT_SHA256:
            raise RuntimeError("M249 board predecessor hash mismatch")
        predecessor = json.loads(args.m249_board_result.read_text(encoding="utf-8"))
        if predecessor.get("status") != "PASS":
            raise RuntimeError("M249 board predecessor not PASS")
        candidate = args.m249_candidate.resolve()
        fixture_manifest = json.loads((candidate / "fixtures/FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))
        fixtures = [np.load(candidate / "fixtures" / item["path"], allow_pickle=False) for item in fixture_manifest["files"]]
        detector = SSDLiteDetector(candidate / "model/ssdlite320_mobilenet_v3_large_coco-a79551df.pth", args.threads)
        engine = LatestFastSafetyEngine(detector, FastFramePipeline())
        engine.start()
        print("M253_SOURCE_BEGIN", flush=True)
        interval = 1.0 / args.source_fps
        next_tick = time.monotonic()
        for sequence in range(args.frames):
            now_ms = int(time.time() * 1000)
            engine.submit(fixtures[sequence % len(fixtures)], now_ms)
            next_tick += interval
            time.sleep(max(0.0, next_tick - time.monotonic()))
        print(f"M253_SOURCE_PASS frames={args.frames}", flush=True)
        reached_latest = engine.wait_completed(args.frames - 1, timeout_s=15.0)
        status = engine.status()
        records = list(engine.records)
        engine.close()
        engine = None
        maximum_latency = max((item["capture_to_result_ms"] for item in records), default=float("inf"))
        maximum_detector = max((item["detector_ms"] for item in records), default=float("inf"))
        person_results = sum(item["person_count"] > 0 for item in records)
        checks = {
            "m249_predecessor_pass": True,
            "runtime_loaded_once": status["runtime_load_count"] == 1,
            "all_source_frames_accepted": status["frame_slot"]["accepted_frames"] == args.frames,
            "mailbox_capacity_one": status["frame_slot"]["capacity"] == 1,
            "stale_pending_frames_overwritten": status["frame_slot"]["overwritten_pending_frames"] > 0,
            "input_outpaced_inference": 0 < status["processed_frames"] < args.frames,
            "latest_sequence_completed": reached_latest and status["last_completed_sequence"] == args.frames - 1,
            "worker_error_absent": status["error"] is None,
            "every_result_meets_5s": bool(records) and all(item["realtime_deadline_met"] for item in records),
            "person_sanity": person_results >= min(3, len(records)),
        }
        result.update({
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "architecture": platform.machine(),
            "python": sys.version.split()[0],
            "threads": args.threads,
            "source_fps": args.source_fps,
            "source_frames": args.frames,
            "processed_frames": len(records),
            "dropped_or_overwritten_frames": args.frames - len(records),
            "maximum_detector_ms": maximum_detector,
            "maximum_capture_to_result_ms": maximum_latency,
            "target_update_period_ms": 5000,
            "person_result_frames": person_results,
            "final_status": status,
            "records": records,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
            "next_gate": (
                "Integrate this exact latest-only fast runtime with the existing Web/SSE ingress and run labelled target-camera evaluation."
                if all(checks.values()) else
                "Repair and rerun only M253 latest-only board pressure; do not publish the fast Web path."
            ),
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun only M253; do not publish Web or claim continuous real-time performance."
    finally:
        if engine is not None:
            try:
                engine.close()
            except BaseException:
                pass
    result["total_ms"] = (time.monotonic() - started) * 1000.0
    atomic_json(args.result.resolve(), result)
    print("__M253_BOARD_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M253_BOARD_RESULT_END__", flush=True)
    print("M253_KV260_LATEST_FAST_STREAM_PASS" if result["status"] == "PASS" else "M253_KV260_LATEST_FAST_STREAM_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
