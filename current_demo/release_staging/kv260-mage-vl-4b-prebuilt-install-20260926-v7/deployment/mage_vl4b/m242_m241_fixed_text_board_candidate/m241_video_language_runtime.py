#!/usr/bin/env python3
"""M241: M230/M238 language model with grouped GQA in Prefill only.

The accepted RoPE implementation is intentionally retained because the M240
real-A53 measurement rejected RoPE table caching as slower.
"""

from __future__ import annotations

import math
import time

import numpy as np

from m230_video_language_runtime import M230VideoLanguageModel
from video_language_runtime import (
    HEADS,
    HEAD_DIM,
    HIDDEN,
    KV_HEADS,
    LAYERS,
    MAX_CONTEXT,
    KVCache,
    apply_rope,
    rms_norm,
    silu,
)


def causal_attention_grouped(
    q: np.ndarray, k: np.ndarray, v: np.ndarray, query_start: int = 0
) -> np.ndarray:
    query_tokens, key_tokens = q.shape[0], k.shape[0]
    output = np.empty((query_tokens, HEADS, HEAD_DIM), dtype=np.float32)
    allowed = np.arange(key_tokens)[None, :] <= (
        query_start + np.arange(query_tokens)
    )[:, None]
    group = HEADS // KV_HEADS
    scale = np.float32(math.sqrt(HEAD_DIM))
    for kv_head in range(KV_HEADS):
        begin = kv_head * group
        end = begin + group
        queries = np.ascontiguousarray(q[:, begin:end, :].transpose(1, 0, 2))
        scores = np.matmul(queries, k[:, kv_head].T).astype(np.float32, copy=False)
        scores /= scale
        scores = np.where(allowed[None, :, :], scores, -np.inf)
        scores -= np.max(scores, axis=2, keepdims=True)
        probability = np.exp(scores, dtype=np.float32)
        probability /= np.sum(probability, axis=2, keepdims=True)
        attended = np.matmul(probability, v[:, kv_head]).astype(np.float32, copy=False)
        output[:, begin:end, :] = attended.transpose(1, 0, 2)
    return output.reshape(query_tokens, HEADS * HEAD_DIM)


class M241VideoLanguageModel(M230VideoLanguageModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouped_attention_calls = 0
        self.grouped_attention_wall_ms = 0.0
        self.rope_cache_used = False

    def prefill(self, hidden: np.ndarray) -> tuple[int, np.ndarray, KVCache]:
        hidden = np.asarray(hidden, dtype=np.float32)
        if hidden.ndim != 2 or hidden.shape[1] != HIDDEN or not 1 <= hidden.shape[0] <= MAX_CONTEXT:
            raise ValueError("prefill hidden state is outside the M120 video contract")
        tokens = hidden.shape[0]
        positions = np.arange(tokens, dtype=np.int64)
        keys: list[np.ndarray] = []
        values: list[np.ndarray] = []
        for layer in range(LAYERS):
            prefix = f"model.language_model.layers.{layer}"
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.input_layernorm.weight"))
            q_raw, k_raw, v_raw = self._attention_inputs(layer, normed)
            q = q_raw.reshape(tokens, HEADS, HEAD_DIM)
            k = k_raw.reshape(tokens, KV_HEADS, HEAD_DIM)
            v = v_raw.reshape(tokens, KV_HEADS, HEAD_DIM)
            q = rms_norm(q, self.weight(f"{prefix}.self_attn.q_norm.weight"))
            k = rms_norm(k, self.weight(f"{prefix}.self_attn.k_norm.weight"))
            # Keep the accepted per-layer RoPE path; M240 rejected table caching.
            q, k = apply_rope(q, k, positions)
            keys.append(k.copy())
            values.append(v.copy())
            attention_started = time.monotonic()
            attended = causal_attention_grouped(q, k, v)
            self.grouped_attention_wall_ms += (time.monotonic() - attention_started) * 1000.0
            self.grouped_attention_calls += 1
            projected = self._family(layer, "attention_out", attended)
            hidden = residual + projected[f"{prefix}.self_attn.o_proj"]
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.post_attention_layernorm.weight"))
            gate_up = self._family(layer, "gate_up", normed)
            down_input = silu(gate_up[f"{prefix}.mlp.gate_proj"]) * gate_up[f"{prefix}.mlp.up_proj"]
            down = self._family(layer, "mlp_down", down_input)
            hidden = residual + down[f"{prefix}.mlp.down_proj"]
            if not np.isfinite(hidden).all():
                raise FloatingPointError(f"non-finite M241 hidden state at layer {layer}")
        final = rms_norm(hidden[-1:], self.weight("model.language_model.norm.weight"))
        logits = self.runtime.lm_head(final)[0]
        return int(np.argmax(logits)), logits, KVCache(keys, values)
