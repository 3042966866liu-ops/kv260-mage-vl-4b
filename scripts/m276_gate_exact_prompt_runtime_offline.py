#!/usr/bin/env python3
"""Freeze exact M276 tokenizer geometry and composed runtime without repeating unchanged vision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path[:] = [item for item in sys.path if Path(item or ".").resolve() != _SCRIPT_DIR]

from m246_knife_binary import constrained_knife_decision
from m276_prompt_contract import M276_KNIFE_PROMPT, tokenize


EXPECTED_M273_RUNTIME_SHA256 = "c656fcdd20b93ee6fa6811a50c4857c0932d112bcb84d407813b0c8518b31b7c"
EXPECTED_M275_SHA256 = "234bba1a9b2796a2a231efd539427d39435715bda69a4f401b87f9273defb5bd"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    m273_path = workspace / "deployment/mage_vl4b/M273_EXACT_RUNTIME_OFFLINE_RESULT.json"
    m275_path = workspace / "deployment/mage_vl4b/M275_GPU_EXACT_PROMPT_SWEEP_RESULT.json"
    if sha256(m273_path) != EXPECTED_M273_RUNTIME_SHA256 or sha256(m275_path) != EXPECTED_M275_SHA256:
        raise RuntimeError("M276 predecessor hash mismatch")
    m273 = json.loads(m273_path.read_text(encoding="utf-8"))
    m275 = json.loads(m275_path.read_text(encoding="utf-8"))
    if m273.get("status") != "PASS_OFFLINE_EXACT_BOARD_TTFT_PENDING" or m275.get("selected_for_further_validation") != "tagged_short":
        raise RuntimeError("M276 predecessor status mismatch")
    tokenizer_json = workspace / "deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
    token_ids = tokenize(tokenizer_json, M276_KNIFE_PROMPT, 3.0)
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    image_pad_id = int(tokenizer.token_to_id("<|image_pad|>"))
    if len(token_ids) != 159 or token_ids.count(image_pad_id) != 98:
        raise RuntimeError(f"M276 tokenizer geometry mismatch {len(token_ids)}/{token_ids.count(image_pad_id)}")
    negative = np.zeros(32, dtype=np.float32); negative[15], negative[16] = 2.0, -1.0
    positive = np.zeros(32, dtype=np.float32); positive[15], positive[16] = -1.0, 2.0
    if constrained_knife_decision(negative)["text"] != "0" or constrained_knife_decision(positive)["text"] != "1":
        raise RuntimeError("M276 constrained decision mismatch")
    import m276_m254_video_server  # noqa: F401
    import m222_video_server as composed_m222
    import video_server as composed_server
    if composed_m222.M222PSVisionRuntime.__name__ != "M273LatestPSVisionRuntime":
        raise RuntimeError("M276 vision injection mismatch")
    if composed_server.M120VideoRuntime.__name__ != "M276ShortPromptBinaryRuntime":
        raise RuntimeError("M276 video injection mismatch")
    source_root = workspace / "deployment/mage_vl4b/m276_short_prompt_source"
    source_paths = tuple(sorted(path for path in source_root.iterdir() if path.is_file())) + (Path(__file__).resolve(),)
    result = {
        "date": "2026-09-02",
        "gate": "M276-exact-five-batch-prompt-runtime-offline",
        "status": "PASS_OFFLINE_EXACT_BOARD_TTFT_PENDING",
        "classification": "Exact tokenizer, constrained decision and composed runtime identity over unchanged M273 vision only; not board TTFT or calibrated accuracy.",
        "prompt": M276_KNIFE_PROMPT,
        "prompt_tokens": len(token_ids),
        "visual_tokens": 98,
        "image_pad_tokens": token_ids.count(image_pad_id),
        "t32_batches": 5,
        "logical_calls": 778,
        "logical_call_reduction_vs_m273_percent": 100.0 * (1.0 - 778.0 / 932.0),
        "logical_call_reduction_vs_m269_percent": 100.0 * (1.0 - 778.0 / 1394.0),
        "unchanged_m273_output_sha256_fp32": m273["output_sha256_fp32"],
        "unchanged_m273_output_bit_exact": m273["warm_output_bit_exact_to_cold"],
        "runtime_import_closure_pass": True,
        "composed_vision_runtime": composed_m222.M222PSVisionRuntime.__name__,
        "composed_video_runtime": composed_server.M120VideoRuntime.__name__,
        "predecessor_m273_sha256": sha256(m273_path),
        "predecessor_m275_sha256": sha256(m275_path),
        "source_hashes": {str(path.relative_to(workspace)).replace("\\", "/"): sha256(path) for path in source_paths},
        "active_board_service_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Package with stage-timed isolated KV260 gate; retain M274 until the new package closes.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M276_EXACT_PROMPT_RUNTIME_OFFLINE_PASS prompt_tokens=159 batches=5 calls=778")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
