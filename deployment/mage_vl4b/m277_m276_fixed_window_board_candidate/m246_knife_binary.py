#!/usr/bin/env python3
"""Constrained one-token knife decision helpers for M246."""

from __future__ import annotations

import math

import numpy as np


KNIFE_NO_TOKEN_ID = 15
KNIFE_YES_TOKEN_ID = 16
KNIFE_PROMPT = (
    "[TELLME_KNIFE_BINARY_V1] Inspect the four video frames. "
    "Output exactly one character: 1 if any knife is visible, otherwise 0. Answer:"
)


def verify_tokenizer_contract(tokenizer) -> dict:
    no_ids = list(tokenizer.encode("0", add_special_tokens=False).ids)
    yes_ids = list(tokenizer.encode("1", add_special_tokens=False).ids)
    if no_ids != [KNIFE_NO_TOKEN_ID] or yes_ids != [KNIFE_YES_TOKEN_ID]:
        raise RuntimeError(
            f"M246 tokenizer contract mismatch 0={no_ids} 1={yes_ids}"
        )
    if tokenizer.decode([KNIFE_NO_TOKEN_ID], skip_special_tokens=True) != "0":
        raise RuntimeError("M246 token 15 does not decode to 0")
    if tokenizer.decode([KNIFE_YES_TOKEN_ID], skip_special_tokens=True) != "1":
        raise RuntimeError("M246 token 16 does not decode to 1")
    return {"no_token_id": KNIFE_NO_TOKEN_ID, "yes_token_id": KNIFE_YES_TOKEN_ID}


def constrained_knife_decision(logits) -> dict:
    values = np.asarray(logits, dtype=np.float32).reshape(-1)
    if values.size <= KNIFE_YES_TOKEN_ID or not np.isfinite(values).all():
        raise ValueError("M246 requires finite full-vocabulary logits")
    no_logit = float(values[KNIFE_NO_TOKEN_ID])
    yes_logit = float(values[KNIFE_YES_TOKEN_ID])
    margin = yes_logit - no_logit
    score = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, margin))))
    selected = KNIFE_YES_TOKEN_ID if yes_logit >= no_logit else KNIFE_NO_TOKEN_ID
    return {
        "token_id": selected,
        "text": "1" if selected == KNIFE_YES_TOKEN_ID else "0",
        "verdict": "PRESENT" if selected == KNIFE_YES_TOKEN_ID else "ABSENT",
        "knife_score": score,
        "score_kind": "two-token-logit-softmax",
        "score_calibrated": False,
        "yes_logit": yes_logit,
        "no_logit": no_logit,
        "logit_margin_yes_minus_no": margin,
        "full_vocabulary_argmax_token_id": int(np.argmax(values)),
    }

