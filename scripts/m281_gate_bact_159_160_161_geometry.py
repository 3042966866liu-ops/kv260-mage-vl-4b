#!/usr/bin/env python3
"""Freeze exact 159/160/161 prompt fixtures before any model or board run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path


EXPECTED_M280_SHA256 = "34b0d848c5023cde985175adab7895a7d3a15dc74555ce62963d08e04f993b36"
TILE = 32
LANGUAGE_FAMILIES = 154
LM_HEAD_CALLS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_sha256(token_ids: list[int]) -> str:
    payload = b"".join(int(value).to_bytes(4, "little", signed=False) for value in token_ids)
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    m280_path = root / "M280_BACT_METHOD_PLAN_RESULT.json"
    if sha256(m280_path) != EXPECTED_M280_SHA256:
        raise RuntimeError("M281 M280 predecessor hash mismatch")
    m280 = json.loads(m280_path.read_text(encoding="utf-8"))
    if m280.get("status") != "PASS_METHOD_PLAN_ONLY":
        raise RuntimeError("M281 requires M280 method-plan PASS")

    source = root / "m281_bact_boundary_source"
    m276_source = root / "m276_short_prompt_source"
    m273_source = root / "m273_latest_binary_source"
    sys.path.insert(0, str(m273_source))
    sys.path.insert(0, str(m276_source))
    sys.path.insert(0, str(source))
    from m281_boundary_contract import PROMPTS, render, tokenize

    tokenizer_json = root / "m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(str(tokenizer_json))
    image_pad_id = int(tokenizer.token_to_id("<|image_pad|>"))
    fixtures = []
    for target in (159, 160, 161):
        prompt = PROMPTS[target]
        token_ids = tokenize(tokenizer_json, prompt)
        token_count = len(token_ids)
        image_pad_count = token_ids.count(image_pad_id)
        if token_count != target:
            raise RuntimeError(
                f"M281 exact boundary geometry mismatch target={target} observed={token_count}"
            )
        if image_pad_count != 98:
            raise RuntimeError(
                f"M281 visual token identity mismatch target={target} observed={image_pad_count}"
            )
        batch_count = math.ceil(token_count / TILE)
        logical_calls = LANGUAGE_FAMILIES * batch_count + LM_HEAD_CALLS
        fixtures.append(
            {
                "target_total_prompt_tokens": target,
                "prompt": prompt,
                "rendered_prompt_sha256": hashlib.sha256(
                    render(prompt).encode("utf-8")
                ).hexdigest(),
                "token_ids_sha256_le_u32": ids_sha256(token_ids),
                "token_count": token_count,
                "visual_tokens": image_pad_count,
                "text_and_template_tokens": token_count - image_pad_count,
                "t32_batches": batch_count,
                "expected_logical_fpga_calls": logical_calls,
            }
        )

    if [item["t32_batches"] for item in fixtures] != [5, 5, 6]:
        raise RuntimeError("M281 159/160/161 batch step mismatch")
    if [item["expected_logical_fpga_calls"] for item in fixtures] != [778, 778, 932]:
        raise RuntimeError("M281 159/160/161 call step mismatch")

    source_paths = tuple(sorted(path for path in source.iterdir() if path.is_file())) + (
        Path(__file__).resolve(),
    )
    result = {
        "date": "2026-09-02",
        "gate": "M281-BACT-controlled-159-160-161-geometry",
        "status": "PASS_OFFLINE_GEOMETRY_ONLY",
        "classification": (
            "Exact tokenizer, visual-token and expected T32 call geometry only; suffixes "
            "are hardware probes, not natural semantic configurations. No model, numerical "
            "accuracy, board timing, power, Web or real-time claim."
        ),
        "tile_granularity": TILE,
        "language_families_per_batch": LANGUAGE_FAMILIES,
        "lm_head_calls": LM_HEAD_CALLS,
        "fixtures": fixtures,
        "observed_batch_step": "160->161 changes 5->6 batches and 778->932 expected logical calls",
        "controlled_variable": "total prompt token count over unchanged two-view/98-visual-token geometry",
        "probe_suffix_semantic_warning": (
            "The x suffixes exist only to isolate execution geometry. They must not be used "
            "as a target-scene accuracy baseline or promoted into the monitoring product."
        ),
        "m280_sha256": sha256(m280_path),
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
            "Run one official-GPU fixed-sample numerical/decision sweep for the three exact "
            "fixtures. Only finite outputs and frozen per-fixture references may unlock a "
            "hash-checked COM3 board timing package."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(partial, args.result)
    print(
        "M281_BACT_GEOMETRY_PASS "
        + " ".join(
            f"{item['token_count']}:{item['t32_batches']}:{item['expected_logical_fpga_calls']}"
            for item in fixtures
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
