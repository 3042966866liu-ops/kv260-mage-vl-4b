#!/usr/bin/env python3
"""Freeze exact prompt/view geometry for BACT pilot prediction collection.

This script loads only the local processor/tokenizer.  It never reads human
labels or filename hints and never loads the model.  The action probes are
separate constrained one-token probes because the deployed knife probe has a
binary head; both tasks are evaluated under the same visual configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image


BASELINE_IDS = {
    "fixed_high_quality": "high-284",
    "fixed_ratio_visual_pruning": "ratio-164",
    "token_count_aware": "count-144",
    "bact": "bact-159",
}
TARGET_TOKENS = {
    "fixed_high_quality": 284,
    "fixed_ratio_visual_pruning": 164,
    "token_count_aware": 144,
    "bact": 159,
}
VIEW_INDICES = {
    "fixed_high_quality": [0, 1, 2, 3],
    "fixed_ratio_visual_pruning": [2, 3],
    "token_count_aware": [2, 3],
    "bact": [2, 3],
}
ACTION_NAMES = ("WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING")
ACTION_OUTPUT_WORDS = {
    "WORKING": "work",
    "IDLE": "idle",
    "WALKING": "walk",
    "FALLING": "fall",
    "FIGHTING": "fight",
}
ACTION_PROMPT = "Action? Reply one: work idle walk fall fight:"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def prepare(processor, views: np.ndarray, prompt: str):
    images = [Image.fromarray(frame, mode="RGB") for frame in views]
    messages = [
        {
            "role": "user",
            "content": [{"type": "video"}, {"type": "text", "text": prompt}],
        }
    ]
    rendered = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return processor(
        text=[rendered], videos=[images], return_tensors="pt", padding=True
    )


def prompt_tokens(processor, view_count: int, prompt: str) -> int:
    dummy = np.zeros((view_count, 224, 224, 3), dtype=np.uint8)
    return int(prepare(processor, dummy, prompt)["input_ids"].shape[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    sys.path[:0] = [
        str(root / "m273_latest_binary_source"),
        str(root / "m246_knife_binary_source"),
        str(root / "m276_short_prompt_source"),
    ]
    from m246_knife_binary import (
        KNIFE_NO_TOKEN_ID,
        KNIFE_PROMPT,
        KNIFE_YES_TOKEN_ID,
    )
    from m273_latest_multiscale_contract import M273_KNIFE_PROMPT
    from m276_prompt_contract import M276_KNIFE_PROMPT
    from transformers import AutoProcessor

    model_path = args.model.resolve()
    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True
    )
    digit_contract = {}
    for digit in range(2):
        ids = list(processor.tokenizer.encode(str(digit), add_special_tokens=False))
        if ids != [15 + digit]:
            raise RuntimeError(f"digit token contract mismatch digit={digit} ids={ids}")
        digit_contract[str(digit)] = ids[0]
    action_token_ids = {}
    action_token_contract = {}
    for action, word in ACTION_OUTPUT_WORDS.items():
        ids = list(processor.tokenizer.encode(word, add_special_tokens=False))
        if len(ids) != 1:
            raise RuntimeError(f"action output must be one token action={action} word={word} ids={ids}")
        action_token_ids[action] = int(ids[0])
        action_token_contract[action] = {"word": word, "tokenId": int(ids[0])}
    if len(set(action_token_ids.values())) != len(ACTION_NAMES):
        raise RuntimeError("action output token IDs must be distinct")

    knife_prompts = {
        "fixed_high_quality": KNIFE_PROMPT,
        # M289 incorrectly reused V1 here and observed 170.  M272/M280 froze
        # the V2 two-view candidate at the real 164-token geometry.
        "fixed_ratio_visual_pruning": M273_KNIFE_PROMPT,
        "token_count_aware": "Knife visible? Answer only 1 or 0:",
        "bact": M276_KNIFE_PROMPT,
    }
    candidates = {}
    for name, candidate_id in BASELINE_IDS.items():
        view_indices = VIEW_INDICES[name]
        view_count = len(view_indices)
        target = TARGET_TOKENS[name]
        knife_prompt = knife_prompts[name]
        knife_tokens = prompt_tokens(processor, view_count, knife_prompt)
        if knife_tokens != target:
            raise RuntimeError(
                f"knife geometry mismatch {name}: expected={target} observed={knife_tokens}"
            )
        action_tokens = prompt_tokens(processor, view_count, ACTION_PROMPT)
        if action_tokens <= view_count * 49:
            raise RuntimeError(f"action prompt geometry is invalid {name}")
        batches = math.ceil(target / 32)
        candidates[name] = {
            "candidateId": candidate_id,
            "targetPromptTokensPerProbe": target,
            "visualTokens": view_count * 49,
            "viewIndices": view_indices,
            "viewCount": view_count,
            "knifePrompt": knife_prompt,
            "knifePromptTokens": knife_tokens,
            "actionPrompt": ACTION_PROMPT,
            "actionPromptTokens": action_tokens,
            "actionPromptUsesNeutralPadding": False,
            "actionPromptGeometryPurpose": (
                "Fixed auxiliary semantic probe; not used as the candidate's board-cost identity."
            ),
            "t32BatchesPerProbe": batches,
            "logicalFpgaCallsPerProbe": 154 * batches + 8,
            "probeCountPerClip": 2,
            "semanticEvaluationBackend": "exact M120 mixed-weight plus A8-G64 software reference",
            "boardTimingClaimAllowed": False,
        }

    m280 = root / "M280_BACT_METHOD_PLAN_RESULT.json"
    m288 = root / "M288_BACT_SELECTOR_RESULT.json"
    m289 = root / "M289_M120_A8_FOUR_BASELINE_SCREEN_RESULT.json"
    result = {
        "schema": "tellme-bact-four-baseline-prediction-geometry-v1",
        "date": "2026-09-03",
        "gate": "M306-four-baseline-prediction-geometry-freeze",
        "status": "PASS_EXACT_GEOMETRY_AND_TASK_TOKEN_CONTRACT",
        "classification": (
            "Tokenizer/view/task-head geometry for offline semantic prediction collection. "
            "This is not human-labelled accuracy, KV260 execution, timing, power or real-time evidence."
        ),
        "baselineIds": BASELINE_IDS,
        "candidates": candidates,
        "knifeTokenIds": {"no": KNIFE_NO_TOKEN_ID, "yes": KNIFE_YES_TOKEN_ID},
        "actionTokenIds": action_token_ids,
        "actionClassLegend": {
            action: ACTION_OUTPUT_WORDS[action] for action in ACTION_NAMES
        },
        "binaryDigitTokenizerContract": digit_contract,
        "actionTokenizerContract": action_token_contract,
        "tasks": {
            "knife": "one-token 0/1 logit margin; per-baseline threshold frozen on calibration only",
            "action": (
                "separate fixed-prompt one-token work/idle/walk/fall/fight logits; used only as an "
                "offline semantic constraint, with no padding and no board-timing claim"
            ),
        },
        "m289WiringCorrection": {
            "historicalResultPreserved": True,
            "historicalFixedRatioObservedTokens": 170,
            "cause": "M289 used the V1 high-quality prompt instead of the frozen M272/M280 V2 two-view prompt",
            "correctedFixedRatioCandidateId": "ratio-164",
        },
        "predecessors": {
            "M280": {"path": str(m280.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(m280)},
            "M288": {"path": str(m288.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(m288)},
            "M289": {"path": str(m289.relative_to(workspace)).replace("\\", "/"), "sha256": sha256(m289)},
        },
        "humanLabelsRead": False,
        "filenameHintsRead": False,
        "modelLoaded": False,
        "boardExecutionRun": False,
        "activeM254M256Changed": False,
        "bootDtbCmaPartitionsChanged": False,
        "stableRollbackPreserved": True,
        "sourceSha256": sha256(Path(__file__).resolve()),
        "nextGate": (
            "Use this immutable geometry plus the M296 source manifest to collect raw knife/action logits "
            "for all 12 clips without reading human labels or filename hints."
        ),
    }
    atomic_json(args.result.resolve(), result)
    print("M306_FOUR_BASELINE_PREDICTION_GEOMETRY_PASS candidates=4 tasks=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
