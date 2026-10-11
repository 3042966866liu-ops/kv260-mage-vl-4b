#!/usr/bin/env python3
"""M268 use the hash-locked M253 detector to select M267 detail views."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from m264_gpu_resolution_semantic_suite import build_samples, sha256
from m267_gpu_multiscale_binary_knife_gate import prepare


CHECKPOINT_SHA256 = "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2"
PERSON_LABEL = 1
KNIFE_LABEL = 49
PERSON_ROI_THRESHOLD = 0.50
KNIFE_ROI_THRESHOLD = 0.05
OUTPUT_SIZE = 224
MIN_CROP_SIDE = 224.0
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def area_resize(frame: np.ndarray, size: int = OUTPUT_SIZE) -> np.ndarray:
    return cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA).astype(np.uint8, copy=False)


def square_expand(box: np.ndarray, width: int, height: int, minimum_side: float) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = [float(value) for value in box]
    center_x = 0.5 * (x1 + x2)
    center_y = 0.5 * (y1 + y2)
    side = max(x2 - x1, y2 - y1, minimum_side) * 1.25
    side = min(float(min(width, height)), side)
    left = max(0.0, min(float(width) - side, center_x - 0.5 * side))
    top = max(0.0, min(float(height) - side, center_y - 0.5 * side))
    right = left + side
    bottom = top + side
    return tuple(int(round(value)) for value in (left, top, right, bottom))


def detect(detector, torch, frame: np.ndarray) -> list[dict]:
    tensor = torch.from_numpy(frame).permute(2, 0, 1).contiguous().float().div_(255.0)
    with torch.inference_mode():
        prediction = detector([tensor])[0]
    labels = prediction["labels"].detach().cpu().numpy()
    scores = prediction["scores"].detach().cpu().numpy()
    boxes = prediction["boxes"].detach().cpu().numpy()
    values = []
    for label, score, box in zip(labels, scores, boxes):
        label = int(label)
        score = float(score)
        if label == PERSON_LABEL and score >= PERSON_ROI_THRESHOLD:
            values.append({"label": "person", "score": score, "box": [float(x) for x in box]})
        elif label == KNIFE_LABEL and score >= KNIFE_ROI_THRESHOLD:
            values.append({"label": "knife", "score": score, "box": [float(x) for x in box]})
        if len(values) >= 20:
            break
    return values


def select_roi(frame: np.ndarray, detections: list[dict]) -> tuple[np.ndarray, dict]:
    height, width, _ = frame.shape
    knives = sorted((item for item in detections if item["label"] == "knife"), key=lambda x: -x["score"])
    people = sorted((item for item in detections if item["label"] == "person"), key=lambda x: -x["score"])
    if knives:
        chosen = np.asarray(knives[0]["box"], dtype=np.float32)
        source = "knife"
        if people:
            person = np.asarray(people[0]["box"], dtype=np.float32)
            chosen = np.asarray([
                min(chosen[0], person[0]), min(chosen[1], person[1]),
                max(chosen[2], person[2]), max(chosen[3], person[3]),
            ], dtype=np.float32)
            source = "knife-person-union"
    elif people:
        chosen = np.asarray(people[0]["box"], dtype=np.float32)
        source = "person"
    else:
        side = float(min(width, height, 320))
        chosen = np.asarray([
            0.5 * (width - side), 0.5 * (height - side),
            0.5 * (width + side), 0.5 * (height + side),
        ], dtype=np.float32)
        source = "center-fallback"
    left, top, right, bottom = square_expand(chosen, width, height, MIN_CROP_SIDE)
    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        raise RuntimeError("M268 selected an empty ROI")
    return area_resize(crop), {
        "source": source,
        "crop_xyxy_pixels": [left, top, right, bottom],
        "detections": detections,
    }


def fast_roi_views(detector, torch, frames_448: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    views = []
    evidence = []
    for frame in frames_448:
        detections = detect(detector, torch, frame)
        detail, selected = select_roi(frame, detections)
        views.extend([area_resize(frame), detail])
        evidence.append(selected)
    return np.stack(views), evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--m267", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    model_path = args.model.resolve()
    examples = args.examples.resolve()
    m267_path = args.m267.resolve()
    m267 = json.loads(m267_path.read_text(encoding="utf-8"))
    if m267.get("status") != "PASS_SMALL_LABELLED_BINARY_MULTISCALE_SUITE_BOARD_PENDING":
        raise RuntimeError("M268 requires the frozen M267 binary multiscale PASS")

    m246_root = workspace / "deployment/mage_vl4b/m246_knife_binary_source"
    sys.path.insert(0, str(m246_root))
    from m246_knife_binary import (  # pylint: disable=import-error,import-outside-toplevel
        KNIFE_NO_TOKEN_ID,
        KNIFE_PROMPT,
        KNIFE_YES_TOKEN_ID,
    )

    import torch
    import torchvision
    from torchvision.models.detection import ssdlite320_mobilenet_v3_large
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M268 requires the existing WSL CUDA environment")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    checkpoint = (
        workspace / "deployment/mage_vl4b/m249_ssdlite_board_candidate/model/"
        "ssdlite320_mobilenet_v3_large_coco-a79551df.pth"
    )
    if sha256(checkpoint) != CHECKPOINT_SHA256:
        raise RuntimeError("M268 M253 detector checkpoint hash mismatch")
    detector = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    detector.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    detector.eval()
    with torch.inference_mode():
        warm = detector([torch.zeros((3, 448, 448), dtype=torch.float32)])[0]
        if not torch.isfinite(warm["scores"]).all():
            raise RuntimeError("M268 detector warm-up is non-finite")

    samples = build_samples(workspace, examples)
    prepared_samples = []
    for sample in samples:
        views, roi_evidence = fast_roi_views(detector, torch, sample.frames_448)
        prepared_samples.append((sample, views, roi_evidence))
    detector = None

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    no_ids = list(processor.tokenizer.encode("0", add_special_tokens=False))
    yes_ids = list(processor.tokenizer.encode("1", add_special_tokens=False))
    if no_ids != [KNIFE_NO_TOKEN_ID] or yes_ids != [KNIFE_YES_TOKEN_ID]:
        raise RuntimeError(f"M268 tokenizer contract mismatch 0={no_ids} 1={yes_ids}")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        quantization_config=quant,
        device_map="auto",
        low_cpu_mem_usage=True,
    ).eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0
    torch.cuda.reset_peak_memory_stats()

    records = []
    for sample, views, roi_evidence in prepared_samples:
        expected = 1 if sample.expected.knife == "有" else 0
        preprocess_started = time.perf_counter()
        inputs = prepare(processor, views, KNIFE_PROMPT)
        preprocess_ms = (time.perf_counter() - preprocess_started) * 1000.0
        shapes = {key: list(value.shape) for key, value in inputs.items() if hasattr(value, "shape")}
        moved = {key: value.to("cuda") if hasattr(value, "to") else value for key, value in inputs.items()}
        started = time.perf_counter()
        with torch.inference_mode():
            output = model(**moved, use_cache=False)
        forward_ms = (time.perf_counter() - started) * 1000.0
        logits = output.logits[0, -1].float()
        no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
        yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
        decision = 1 if yes_logit >= no_logit else 0
        records.append({
            "name": sample.name,
            "expected": expected,
            "decision": decision,
            "pass": decision == expected,
            "no_logit": no_logit,
            "yes_logit": yes_logit,
            "margin_yes_minus_no": yes_logit - no_logit,
            "score_calibrated": False,
            "prompt_tokens": int(moved["input_ids"].shape[1]),
            "tensor_shapes": shapes,
            "roi_evidence": roi_evidence,
            "preprocess_ms": preprocess_ms,
            "forward_ms": forward_ms,
        })

    suite_pass = len(records) == 4 and all(record["pass"] for record in records)
    prompt_counts = sorted({record["prompt_tokens"] for record in records})
    projected = None
    if len(prompt_counts) == 1:
        prompt_tokens = prompt_counts[0]
        batches = math.ceil(prompt_tokens / 32)
        calls = batches * LANGUAGE_FAMILIES + LM_HEAD_CALLS
        projected = {
            "official_processor_prompt_tokens": prompt_tokens,
            "t32_batches_from_official_prompt": batches,
            "logical_calls_from_official_prompt": calls,
            "call_reduction_vs_M264_official_448_prompt_percent": 100.0 * (1.0 - calls / 2318.0),
            "not_board_measurement": True,
        }
    status = (
        "PASS_HASH_LOCKED_FAST_ROI_BINARY_SUITE_BOARD_PENDING"
        if suite_pass
        else "FAIL_HASH_LOCKED_FAST_ROI_BINARY_SUITE"
    )
    result = {
        "date": "2026-09-02",
        "gate": "M268-hash-locked-M253-ROI-constrained-4B-knife-review",
        "status": status,
        "classification": (
            "Small labelled official Mage-VL NF4/BF16 binary regression screen with real M253 "
            "detector ROI logic; not calibrated accuracy, KV260 semantics, or FPGA speed."
        ),
        "predecessor": str(m267_path),
        "predecessor_sha256": sha256(m267_path),
        "detector": {
            "name": "SSDLite320 MobileNetV3 Large COCO_V1",
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": sha256(checkpoint),
            "torchvision": torchvision.__version__,
            "person_roi_threshold": PERSON_ROI_THRESHOLD,
            "knife_roi_threshold": KNIFE_ROI_THRESHOLD,
            "roi_priority": ["knife-person-union", "person", "center-fallback"],
            "minimum_crop_side_pixels": MIN_CROP_SIDE,
        },
        "architecture_decision": m267["architecture_decision"],
        "prompt": KNIFE_PROMPT,
        "visual_tokens": 196,
        "records": records,
        "suite_pass": suite_pass,
        "projected_schedule": projected,
        "model": "microsoft/Mage-VL",
        "checkpoint": str(model_path),
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "gpu_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "threshold_calibrated": False,
        "semantic_accuracy_passed": False,
        "semantic_accuracy_reason": (
            "Four examples are a regression screen only; M252 held-out target-camera metrics remain required."
        ),
        "host_gpu_timing_is_board_evidence": False,
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "If PASS, create a clean M259+M261+M268 delta and wait for COM3 for isolated KV260 "
            "memory, exact identity, binary semantics and complete TTFT."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(
        f"M268_FAST_ROI_BINARY_{'PASS' if suite_pass else 'FAIL'} "
        f"passed={sum(record['pass'] for record in records)}/{len(records)}"
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
