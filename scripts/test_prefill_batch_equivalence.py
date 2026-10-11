#!/usr/bin/env python3
"""Check batched causal Prefill against the existing token-serial algorithm."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


class ExactEngine:
    def __init__(self, matrices: dict[str, np.ndarray]):
        self.matrices = matrices
        self.lm_head_info = None

    def finish_prefetch(self):
        pass

    def linear(self, name, activation, next_names=None):
        return self.matrices[name] @ np.asarray(activation, dtype=np.float32)

    def linear_qkv(self, names, activation, next_names=None):
        return tuple(self.linear(name, activation) for name in names)

    def linear_prefill(self, names, activation):
        x = np.asarray(activation, dtype=np.float32)
        key = (names,) if isinstance(names, str) else tuple(names)
        outputs = tuple(x @ self.matrices[name].T for name in key)
        return outputs[0] if isinstance(names, str) else outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.runtime.resolve()))
    from qwen_fpga_runtime import QwenRuntime

    rng = np.random.default_rng(20260822)
    runtime = QwenRuntime.__new__(QwenRuntime)
    runtime.hidden = 64
    runtime.heads = 4
    runtime.kv_heads = 2
    runtime.head_dim = 16
    runtime.layers = 2
    runtime.eps = 1.0e-6
    runtime.theta = 10000.0
    runtime.max_seq_len = 32
    runtime.cfg = {"vocab_size": 97, "eos_token_id": 96}
    runtime.position = 0
    runtime.embedding = (rng.standard_normal((97, 64)) * 0.08).astype(np.float16)
    runtime.k_cache = [np.empty((32, 2, 16), np.float32) for _ in range(2)]
    runtime.v_cache = [np.empty((32, 2, 16), np.float32) for _ in range(2)]
    runtime.lm_head_ms = 0.0
    runtime.lm_head_rescore_ms = 0.0
    runtime.lm_head_calls = 0
    runtime.aux = {"model.norm.weight": np.ones((64,), dtype=np.float16)}
    matrices = {}
    for layer in range(runtime.layers):
        prefix = f"model.layers.{layer}"
        runtime.aux[f"{prefix}.input_layernorm.weight"] = np.ones((64,), np.float16)
        runtime.aux[f"{prefix}.post_attention_layernorm.weight"] = np.ones((64,), np.float16)
        for projection in ("q", "k", "v"):
            output = 64 if projection == "q" else 32
            name = f"{prefix}.self_attn.{projection}_proj.weight"
            matrices[name] = (rng.standard_normal((output, 64)) * 0.03).astype(np.float32)
            runtime.aux[f"{prefix}.self_attn.{projection}_proj.bias"] = (
                rng.standard_normal((output,)) * 0.01
            ).astype(np.float16)
        matrices[f"{prefix}.self_attn.o_proj.weight"] = (
            rng.standard_normal((64, 64)) * 0.03
        ).astype(np.float32)
        for projection in ("gate", "up"):
            matrices[f"{prefix}.mlp.{projection}_proj.weight"] = (
                rng.standard_normal((128, 64)) * 0.03
            ).astype(np.float32)
        matrices[f"{prefix}.mlp.down_proj.weight"] = (
            rng.standard_normal((64, 128)) * 0.03
        ).astype(np.float32)
    runtime.engine = ExactEngine(matrices)

    ids = [3, 11, 29, 5, 83, 17, 41]
    serial_logits = None
    for index, token_id in enumerate(ids):
        serial_logits = runtime.forward_token(
            token_id, compute_logits=index == len(ids) - 1
        )
    serial_k = [cache[: len(ids)].copy() for cache in runtime.k_cache]
    serial_v = [cache[: len(ids)].copy() for cache in runtime.v_cache]

    runtime.position = 0
    runtime.lm_head_ms = 0.0
    runtime.lm_head_rescore_ms = 0.0
    runtime.lm_head_calls = 0
    batch_logits = runtime.prefill_tokens(ids)
    logit_diff = float(np.max(np.abs(batch_logits - serial_logits)))
    k_diff = max(
        float(np.max(np.abs(runtime.k_cache[i][: len(ids)] - serial_k[i])))
        for i in range(runtime.layers)
    )
    v_diff = max(
        float(np.max(np.abs(runtime.v_cache[i][: len(ids)] - serial_v[i])))
        for i in range(runtime.layers)
    )
    passed = logit_diff < 2.0e-5 and k_diff < 2.0e-5 and v_diff < 2.0e-5
    print(
        {
            "gate": "PASS" if passed else "FAIL",
            "tokens": len(ids),
            "max_logit_abs_diff": logit_diff,
            "max_k_cache_abs_diff": k_diff,
            "max_v_cache_abs_diff": v_diff,
        }
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
