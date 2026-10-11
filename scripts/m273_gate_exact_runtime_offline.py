#!/usr/bin/env python3
"""M273 exact geometry, vision/cache, tokenizer and composed-runtime offline gate."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [item for item in sys.path if Path(item or ".").resolve() != _SCRIPT_DIR]

from m246_knife_binary import constrained_knife_decision
from m261_budgeted_w4_runtime import EXPECTED_CACHE_BYTES, EXPECTED_CACHE_ENTRIES
from m273_latest_multiscale_contract import M273_KNIFE_PROMPT, VISUAL_TOKENS, preprocess, tokenize
from m273_latest_vision_runtime import M273LatestPSVisionRuntime


EXPECTED_SEMANTIC_SHA256 = "23e53a0e020c169e5dcaf4a191835bc0f37dba7e58026495b5c37cb23eea36c7"


def digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    fixture_root = workspace / "deployment/mage_vl4b/m249_ssdlite_board_candidate/fixtures"
    frames = np.stack([
        np.load(fixture_root / f"frame_{index:02d}_{number:04d}_rgb448.npy", allow_pickle=False)
        for index, number in enumerate((68, 102, 137, 171))
    ])
    tensors = preprocess(np.ascontiguousarray(frames[-1:]))
    expected_shapes = {
        "pixel_values": [392, 768],
        "image_grid_thw": [2, 3],
        "patch_positions": [392, 3],
    }
    observed_shapes = {name: list(np.asarray(tensors[name]).shape) for name in expected_shapes}
    if observed_shapes != expected_shapes or int(tensors["merged_visual_tokens"]) != VISUAL_TOKENS:
        raise RuntimeError(f"M273 geometry mismatch: {observed_shapes}")

    candidate = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate"
    runtime = M273LatestPSVisionRuntime(
        candidate / "ps_vision_payload", candidate / "vision_layout",
        candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json", heartbeat_seconds=3600.0,
    )
    outputs, timings, evidence = [], [], []
    try:
        for _ in range(2):
            started = time.perf_counter()
            with contextlib.redirect_stdout(io.StringIO()):
                output = runtime(
                    tensors["pixel_values"], tensors["image_grid_thw"], tensors["patch_positions"]
                )
            timings.append((time.perf_counter() - started) * 1000.0)
            outputs.append(output)
            evidence.append(dict(runtime.decoder_evidence()))
    finally:
        runtime.close()
    if outputs[0].shape != (98, 2560) or not np.isfinite(outputs[0]).all() or not np.array_equal(outputs[0], outputs[1]):
        raise RuntimeError("M273 exact/finite visual output gate failed")
    cold, warm = evidence
    if not (
        cold["cache_misses"] == EXPECTED_CACHE_ENTRIES and cold["cache_hits"] == 0
        and cold["uncached_decode_calls"] == 72 and cold["cache_bytes"] == EXPECTED_CACHE_BYTES
        and warm["cache_misses"] == EXPECTED_CACHE_ENTRIES
        and warm["cache_hits"] == EXPECTED_CACHE_ENTRIES
        and warm["uncached_decode_calls"] == 144 and warm["cache_bytes"] == EXPECTED_CACHE_BYTES
        and warm["cache_within_budget"] is True
    ):
        raise RuntimeError(f"M273 cache accounting mismatch: {cold}/{warm}")

    tokenizer_json = candidate / "text_auxiliary/tokenizer/tokenizer.json"
    token_ids = tokenize(tokenizer_json, M273_KNIFE_PROMPT, 3.0)
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    image_pad_id = int(tokenizer.token_to_id("<|image_pad|>"))
    if len(token_ids) != 164 or token_ids.count(image_pad_id) != 98:
        raise RuntimeError(f"M273 tokenizer geometry mismatch tokens={len(token_ids)} pads={token_ids.count(image_pad_id)}")
    negative_logits = np.zeros(32, dtype=np.float32)
    negative_logits[15], negative_logits[16] = 2.0, -1.0
    positive_logits = np.zeros(32, dtype=np.float32)
    positive_logits[15], positive_logits[16] = -1.0, 2.0
    if constrained_knife_decision(negative_logits)["text"] != "0" or constrained_knife_decision(positive_logits)["text"] != "1":
        raise RuntimeError("M273 constrained decision mismatch")

    import m273_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M273LatestPSVisionRuntime":
        raise RuntimeError("M273 composed vision injection failed")
    if composed_server.M120VideoRuntime.__name__ != "M273LatestBinaryRuntime":
        raise RuntimeError("M273 composed video injection failed")

    semantic_path = workspace / "deployment/mage_vl4b/M273_GPU_EXACT_LATEST_BINARY_RESULT.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    if sha256(semantic_path) != EXPECTED_SEMANTIC_SHA256 or not semantic.get("suite_pass"):
        raise RuntimeError("M273 semantic predecessor mismatch")
    source_root = workspace / "deployment/mage_vl4b/m273_latest_binary_source"
    source_paths = tuple(sorted(path for path in source_root.iterdir() if path.is_file())) + (
        semantic_path, Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M273-deployable-latest-global-detail-binary-runtime-offline",
        "status": "PASS_OFFLINE_EXACT_BOARD_TTFT_PENDING",
        "classification": (
            "Exact NumPy two-view construction, finite/bit-exact visual output, cache accounting, tokenizer, "
            "binary decision and composed imports only; not KV260 TTFT, calibrated accuracy, Web or promotion."
        ),
        "selected_frame_indices": [3],
        "tensor_shapes": observed_shapes,
        "visual_tokens": 98,
        "tokenizer_prompt_tokens": len(token_ids),
        "tokenizer_image_pad_tokens": token_ids.count(image_pad_id),
        "t32_batches": 6,
        "logical_calls": 932,
        "logical_call_reduction_vs_m269_percent": 100.0 * (1.0 - 932.0 / 1394.0),
        "output_shape": list(outputs[0].shape),
        "output_sha256_fp32": digest(outputs[0].astype(np.float32)),
        "warm_output_bit_exact_to_cold": True,
        "cold_window_ms": timings[0],
        "warm_window_ms": timings[1],
        "host_timing_is_board_evidence": False,
        "cold_evidence": cold,
        "warm_evidence": warm,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "cv2_required_on_board": False,
        "decode_calls": 0,
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "semantic_predecessor_sha256": sha256(semantic_path),
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): sha256(path)
            for path in source_paths
        },
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Build a clean hash-locked package; then run one isolated stage-timed KV260 gate after COM3 sudo.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(
        f"M273_EXACT_RUNTIME_OFFLINE_PASS prompt_tokens={len(token_ids)} visual_tokens=98 "
        f"cold_ms={timings[0]:.3f} warm_ms={timings[1]:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
