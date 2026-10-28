#!/usr/bin/env python3
"""M120 video language loop with split early Q/KV and exact call accounting."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


BUILD_ID = "0x4D395832"
LAYERS, HIDDEN, HEADS, KV_HEADS, HEAD_DIM = 36, 2560, 32, 8, 128
VOCAB, INTERMEDIATE = 151936, 9728
RMS_EPS, ROPE_THETA = 1.0e-6, 5_000_000.0
IMAGE_PAD_ID, EOS_ID, MAX_CONTEXT = 151655, 151645, 1024
EARLY_SPLIT_LAYERS = 10
LANGUAGE_CHAIN_CALLS_PER_T32_BATCH = 154
LM_HEAD_CHAIN_CALLS = 8
DECODE_CHAIN_CALLS_PER_TOKEN = 162


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rms_norm(values: np.ndarray, weight: np.ndarray) -> np.ndarray:
    x, w = np.asarray(values, np.float32), np.asarray(weight, np.float32)
    variance = np.mean(np.square(x, dtype=np.float32), axis=-1, keepdims=True)
    return (x * (1.0 / np.sqrt(variance + RMS_EPS)) * w).astype(np.float32)


def rotate_half(x: np.ndarray) -> np.ndarray:
    return np.concatenate((-x[..., x.shape[-1] // 2 :], x[..., : x.shape[-1] // 2]), axis=-1)


def apply_rope(q: np.ndarray, k: np.ndarray, positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    inv = 1.0 / (ROPE_THETA ** (np.arange(0, HEAD_DIM, 2, dtype=np.float32) / HEAD_DIM))
    frequency = np.outer(np.asarray(positions, np.float32), inv)
    angle = np.concatenate((frequency, frequency), axis=-1)
    cos, sin = np.cos(angle)[:, None, :], np.sin(angle)[:, None, :]
    return (
        (q * cos + rotate_half(q) * sin).astype(np.float32),
        (k * cos + rotate_half(k) * sin).astype(np.float32),
    )


def causal_attention(q: np.ndarray, k: np.ndarray, v: np.ndarray, query_start: int = 0) -> np.ndarray:
    query_tokens, key_tokens = q.shape[0], k.shape[0]
    output = np.empty((query_tokens, HEADS, HEAD_DIM), dtype=np.float32)
    key_positions = np.arange(key_tokens)
    for head in range(HEADS):
        kv_head = head // (HEADS // KV_HEADS)
        score = (q[:, head] @ k[:, kv_head].T).astype(np.float32, copy=False)
        score /= math.sqrt(HEAD_DIM)
        allowed = key_positions[None, :] <= (query_start + np.arange(query_tokens))[:, None]
        score = np.where(allowed, score, -np.inf)
        score -= np.max(score, axis=1, keepdims=True)
        probability = np.exp(score, dtype=np.float32)
        probability /= np.sum(probability, axis=1, keepdims=True)
        output[:, head] = probability @ v[:, kv_head]
    return output.reshape(query_tokens, HEADS * HEAD_DIM)


def silu(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, np.float32)
    return (x / (1.0 + np.exp(-x))).astype(np.float32)


def expected_physical_calls(prefill_tokens: int, generated_tokens: int) -> int:
    if not 1 <= prefill_tokens <= MAX_CONTEXT:
        raise ValueError("prefill token count is outside the M120 video contract")
    if generated_tokens < 1:
        raise ValueError("generated token count must be positive")
    prefill = math.ceil(prefill_tokens / 32) * LANGUAGE_CHAIN_CALLS_PER_T32_BATCH
    prefill += LM_HEAD_CHAIN_CALLS
    return prefill + (generated_tokens - 1) * DECODE_CHAIN_CALLS_PER_TOKEN


@dataclass
class KVCache:
    keys: list[np.ndarray]
    values: list[np.ndarray]


class M120VideoLanguageModel:
    """PS Transformer control with M120 Linears delegated to one board runtime."""

    def __init__(self, runtime, auxiliary_root: Path):
        self.runtime = runtime
        self.auxiliary_root = Path(auxiliary_root)
        manifest_path = self.auxiliary_root / "M151_M120_TEXT_AUX_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "PASS" or manifest.get("build_id") != BUILD_ID:
            raise RuntimeError("M151 M120 text auxiliary manifest is not accepted")
        embedding = manifest["embedding"]
        if embedding.get("source_bits") != 3 or embedding.get("source_group_size") != 64:
            raise RuntimeError("M151 embedding is not derived from M120 W3-G64")
        embedding_path = self.auxiliary_root / embedding["path"]
        if embedding_path.stat().st_size != int(embedding["bytes"]) or sha256(embedding_path) != embedding["sha256"]:
            raise RuntimeError("M151 M120 embedding identity gate failed")
        norms = manifest["norms"]
        norms_path = self.auxiliary_root / norms["path"]
        if norms_path.stat().st_size != int(norms["bytes"]) or sha256(norms_path) != norms["sha256"]:
            raise RuntimeError("M151 text norm identity gate failed")
        self.embedding = np.memmap(embedding_path, mode="r", dtype="<f2", shape=(VOCAB, HIDDEN))
        self._norm_archive = np.load(norms_path, allow_pickle=False)
        self.norms = {name: self._norm_archive[name] for name in self._norm_archive.files}

    def weight(self, name: str) -> np.ndarray:
        if name not in self.norms:
            raise RuntimeError(f"missing M151 auxiliary tensor: {name}")
        return np.asarray(self.norms[name], np.float32)

    def input_embeddings(self, token_ids: list[int], visual_tokens: np.ndarray) -> np.ndarray:
        ids = np.asarray(token_ids, dtype=np.int64)
        if ids.ndim != 1 or not 1 <= ids.size <= MAX_CONTEXT or ids.min() < 0 or ids.max() >= VOCAB:
            raise ValueError("token IDs are outside the M120 context/vocabulary contract")
        visual = np.asarray(visual_tokens, dtype=np.float32)
        positions = np.flatnonzero(ids == IMAGE_PAD_ID)
        if visual.shape != (positions.size, HIDDEN) or positions.size != 784:
            raise ValueError(f"expected 784x2560 visual tokens for 784 image_pad IDs, got {visual.shape}/{positions.size}")
        hidden = np.asarray(self.embedding[ids], dtype=np.float32).copy()
        hidden[positions] = visual
        return hidden

    def _family(self, layer: int, family: str, values: np.ndarray) -> dict[str, np.ndarray]:
        array = np.asarray(values, dtype=np.float32)
        assembled: dict[str, list[np.ndarray]] = {}
        for start in range(0, array.shape[0], 32):
            batch = self.runtime.language_family(layer, family, array[start : start + 32])
            count = min(32, array.shape[0] - start)
            for name, value in batch.items():
                assembled.setdefault(name, []).append(value[:count])
        return {name: np.concatenate(chunks, axis=0) for name, chunks in assembled.items()}

    def _attention_inputs(self, layer: int, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        prefix = f"model.language_model.layers.{layer}.self_attn"
        if layer < EARLY_SPLIT_LAYERS:
            q_result = self._family(layer, "q", values)
            kv_result = self._family(layer, "kv", values)
            q = q_result[f"{prefix}.q_proj"]
            k = kv_result[f"{prefix}.k_proj"]
            v = kv_result[f"{prefix}.v_proj"]
        else:
            qkv = self._family(layer, "qkv", values)
            q = qkv[f"{prefix}.q_proj"]
            k = qkv[f"{prefix}.k_proj"]
            v = qkv[f"{prefix}.v_proj"]
        return q, k, v

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
            q, k = apply_rope(q, k, positions)
            keys.append(k.copy())
            values.append(v.copy())
            projected = self._family(layer, "attention_out", causal_attention(q, k, v))
            hidden = residual + projected[f"{prefix}.self_attn.o_proj"]
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.post_attention_layernorm.weight"))
            gate_up = self._family(layer, "gate_up", normed)
            down_input = silu(gate_up[f"{prefix}.mlp.gate_proj"]) * gate_up[f"{prefix}.mlp.up_proj"]
            down = self._family(layer, "mlp_down", down_input)
            hidden = residual + down[f"{prefix}.mlp.down_proj"]
            if not np.isfinite(hidden).all():
                raise FloatingPointError(f"non-finite M120 hidden state at layer {layer}")
        final = rms_norm(hidden[-1:], self.weight("model.language_model.norm.weight"))
        logits = self.runtime.lm_head(final)[0]
        return int(np.argmax(logits)), logits, KVCache(keys, values)

    def decode(self, token_id: int, cache: KVCache) -> tuple[int, np.ndarray]:
        if len(cache.keys) != LAYERS or len(cache.values) != LAYERS:
            raise ValueError("M120 KV cache layer count mismatch")
        position = cache.keys[0].shape[0]
        if position >= MAX_CONTEXT:
            raise ValueError("M120 context limit reached")
        hidden = np.asarray(self.embedding[[int(token_id)]], dtype=np.float32).copy()
        for layer in range(LAYERS):
            prefix = f"model.language_model.layers.{layer}"
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.input_layernorm.weight"))
            q_raw, k_raw, v_raw = self._attention_inputs(layer, normed)
            q = q_raw.reshape(1, HEADS, HEAD_DIM)
            k_new = k_raw.reshape(1, KV_HEADS, HEAD_DIM)
            v_new = v_raw.reshape(1, KV_HEADS, HEAD_DIM)
            q = rms_norm(q, self.weight(f"{prefix}.self_attn.q_norm.weight"))
            k_new = rms_norm(k_new, self.weight(f"{prefix}.self_attn.k_norm.weight"))
            q, k_new = apply_rope(q, k_new, np.asarray([position], dtype=np.int64))
            cache.keys[layer] = np.concatenate((cache.keys[layer], k_new), axis=0)
            cache.values[layer] = np.concatenate((cache.values[layer], v_new), axis=0)
            attended = causal_attention(q, cache.keys[layer], cache.values[layer], query_start=position)
            projected = self._family(layer, "attention_out", attended)
            hidden = residual + projected[f"{prefix}.self_attn.o_proj"]
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.post_attention_layernorm.weight"))
            gate_up = self._family(layer, "gate_up", normed)
            down_input = silu(gate_up[f"{prefix}.mlp.gate_proj"]) * gate_up[f"{prefix}.mlp.up_proj"]
            down = self._family(layer, "mlp_down", down_input)
            hidden = residual + down[f"{prefix}.mlp.down_proj"]
            if not np.isfinite(hidden).all():
                raise FloatingPointError(f"non-finite M120 decode hidden state at layer {layer}")
        final = rms_norm(hidden, self.weight("model.language_model.norm.weight"))
        logits = self.runtime.lm_head(final)[0]
        return int(np.argmax(logits)), logits

    def close(self) -> None:
        self._norm_archive.close()
        del self.embedding
