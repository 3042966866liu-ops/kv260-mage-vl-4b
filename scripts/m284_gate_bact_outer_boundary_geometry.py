#!/usr/bin/env python3
"""Freeze exact 127/128/129 and 191/192/193 BACT hardware probes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path


EXPECTED_M282_SHA256 = "a42cde7a03d944f66f9fdad362ce60036393b82188f724fdb8c61236b97a2cbf"
TILE = 32
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_sha256(token_ids: list[int]) -> str:
    payload = b"".join(int(value).to_bytes(4, "little") for value in token_ids)
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    predecessor = root / "M282_GPU_BACT_159_160_161_RESULT.json"
    if sha256(predecessor) != EXPECTED_M282_SHA256:
        raise RuntimeError("M284 M282 predecessor hash mismatch")
    if json.loads(predecessor.read_text(encoding="utf-8")).get("status") != "PASS_SMALL_SCREEN":
        raise RuntimeError("M284 requires M282 small-screen PASS")

    source = root / "m284_bact_outer_boundaries_source"
    sys.path[:0] = [
        str(source),
        str(root / "m276_short_prompt_source"),
        str(root / "m273_latest_binary_source"),
    ]
    from m284_outer_boundary_contract import PROBES, render, tokenize
    from tokenizers import Tokenizer

    tokenizer_json = root / "m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    image_pad_id = int(tokenizer.token_to_id("<|image_pad|>"))
    fixtures = []
    for target in sorted(PROBES):
        probe = PROBES[target]
        view_count = int(probe["view_count"])
        prompt = str(probe["prompt"])
        token_ids = tokenize(tokenizer_json, prompt, view_count)
        visual_tokens = token_ids.count(image_pad_id)
        expected_visual_tokens = 49 * view_count
        if len(token_ids) != target:
            raise RuntimeError(f"M284 token mismatch target={target} observed={len(token_ids)}")
        if visual_tokens != expected_visual_tokens:
            raise RuntimeError(
                f"M284 visual-token mismatch target={target} "
                f"expected={expected_visual_tokens} observed={visual_tokens}"
            )
        batches = math.ceil(target / TILE)
        fixtures.append({
            "target_total_prompt_tokens": target,
            "view_count": view_count,
            "visual_tokens": visual_tokens,
            "text_and_template_tokens": target - visual_tokens,
            "prompt": prompt,
            "rendered_prompt_sha256": hashlib.sha256(
                render(prompt, view_count).encode("utf-8")
            ).hexdigest(),
            "token_ids_sha256_le_u32": ids_sha256(token_ids),
            "t32_batches": batches,
            "expected_logical_fpga_calls": LANGUAGE_FAMILIES * batches + LM_HEAD_CALLS,
        })

    observed = {
        item["target_total_prompt_tokens"]: (
            item["t32_batches"], item["expected_logical_fpga_calls"]
        )
        for item in fixtures
    }
    expected = {
        127: (4, 624), 128: (4, 624), 129: (5, 778),
        191: (6, 932), 192: (6, 932), 193: (7, 1086),
    }
    if observed != expected:
        raise RuntimeError(f"M284 staircase mismatch observed={observed}")

    source_paths = tuple(sorted(path for path in source.iterdir() if path.is_file())) + (
        Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M284-BACT-controlled-outer-boundary-geometry",
        "status": "PASS_OFFLINE_GEOMETRY_ONLY",
        "classification": (
            "Exact tokenizer, view-count, visual-token and T32 call geometry only. "
            "Repeated x suffixes isolate the hardware staircase and are not natural "
            "monitoring configurations, accuracy evidence, board timing or a real-time claim."
        ),
        "tile_granularity": TILE,
        "language_families_per_batch": LANGUAGE_FAMILIES,
        "lm_head_calls": LM_HEAD_CALLS,
        "fixtures": fixtures,
        "observed_batch_steps": [
            "128->129 changes 4->5 batches and 624->778 expected logical calls",
            "192->193 changes 6->7 batches and 932->1086 expected logical calls",
        ],
        "controlled_variables": {
            "within_each_triplet": "unchanged view geometry; total prompt length only",
            "between_triplets": "one view around 128; two views around 192",
        },
        "m282_sha256": sha256(predecessor),
        "tokenizer_json_sha256": sha256(tokenizer_json),
        "source_hashes": {
            str(path.relative_to(workspace)).replace("\\", "/"): sha256(path)
            for path in source_paths
        },
        "model_execution_run": False,
        "board_execution_run": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Run an official-GPU fixed-sample numerical/decision screen separately for "
            "each triplet before designing any COM3 board package."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print(
        "M284_BACT_OUTER_GEOMETRY_PASS "
        + " ".join(
            f"{item['target_total_prompt_tokens']}:"
            f"{item['t32_batches']}:{item['expected_logical_fpga_calls']}"
            for item in fixtures
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
