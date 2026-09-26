#!/usr/bin/env python3
"""Fixed 30-token/one-token M120/M89X2 text E2E gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from board_runtime import M120BoardRuntime


LAYERS, HIDDEN, HEADS, KV_HEADS, HEAD_DIM = 36, 2560, 32, 8, 128
VOCAB, INTERMEDIATE = 151936, 9728
RMS_EPS, ROPE_THETA = 1.0e-6, 5_000_000.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rms_norm(values: np.ndarray, weight: np.ndarray) -> np.ndarray:
    x, w = np.asarray(values, np.float32), np.asarray(weight, np.float32)
    variance = np.mean(np.square(x, dtype=np.float32), axis=-1, keepdims=True)
    return (x * (1.0 / np.sqrt(variance + RMS_EPS)) * w).astype(np.float32)


def rotate_half(x: np.ndarray) -> np.ndarray:
    return np.concatenate((-x[..., x.shape[-1] // 2:], x[..., :x.shape[-1] // 2]), axis=-1)


def apply_rope(q: np.ndarray, k: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tokens = q.shape[0]
    inv = 1.0 / (ROPE_THETA ** (np.arange(0, HEAD_DIM, 2, dtype=np.float32) / HEAD_DIM))
    freq = np.outer(np.arange(tokens, dtype=np.float32), inv)
    angle = np.concatenate((freq, freq), axis=-1)
    cos, sin = np.cos(angle)[:, None, :], np.sin(angle)[:, None, :]
    return ((q * cos + rotate_half(q) * sin).astype(np.float32),
            (k * cos + rotate_half(k) * sin).astype(np.float32))


def attention(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    tokens = q.shape[0]
    k = np.repeat(k, HEADS // KV_HEADS, axis=1)
    v = np.repeat(v, HEADS // KV_HEADS, axis=1)
    scores = np.einsum("thd,shd->hts", q, k, optimize=True) / math.sqrt(HEAD_DIM)
    scores += np.triu(np.full((tokens, tokens), -np.inf, dtype=np.float32), k=1)[None]
    scores -= np.max(scores, axis=-1, keepdims=True)
    probability = np.exp(scores, dtype=np.float32)
    probability /= np.sum(probability, axis=-1, keepdims=True)
    return np.einsum("hts,shd->thd", probability, v, optimize=True).reshape(tokens, HEADS * HEAD_DIM).astype(np.float32)


def silu(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, np.float32)
    return (x / (1.0 + np.exp(-x))).astype(np.float32)


class FixedTextModel:
    def __init__(self, runtime: M120BoardRuntime, auxiliary: dict[str, np.ndarray], embedding_ids: list[int]):
        self.runtime, self.aux = runtime, auxiliary
        rows = np.asarray(auxiliary["model.language_model.embed_tokens.weight"], np.float32)
        self.embedding = {int(token): rows[index] for index, token in enumerate(embedding_ids)}

    def weight(self, name: str) -> np.ndarray:
        if name not in self.aux:
            raise RuntimeError(f"missing auxiliary tensor: {name}")
        return np.asarray(self.aux[name], np.float32)

    def run(self, token_ids: list[int]) -> tuple[int, np.ndarray, list[float]]:
        hidden = np.stack([self.embedding[int(token)] for token in token_ids]).astype(np.float32)
        layer_ms = []
        for layer in range(LAYERS):
            started = time.monotonic()
            prefix = f"model.language_model.layers.{layer}"
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.input_layernorm.weight"))
            if layer < 10:
                qkv = {}
                qkv.update(self.runtime.language_family(layer, "q", normed))
                qkv.update(self.runtime.language_family(layer, "kv", normed))
            else:
                qkv = self.runtime.language_family(layer, "qkv", normed)
            query = qkv[f"{prefix}.self_attn.q_proj"][:len(token_ids)].reshape(-1, HEADS, HEAD_DIM)
            key = qkv[f"{prefix}.self_attn.k_proj"][:len(token_ids)].reshape(-1, KV_HEADS, HEAD_DIM)
            value = qkv[f"{prefix}.self_attn.v_proj"][:len(token_ids)].reshape(-1, KV_HEADS, HEAD_DIM)
            query = rms_norm(query, self.weight(f"{prefix}.self_attn.q_norm.weight"))
            key = rms_norm(key, self.weight(f"{prefix}.self_attn.k_norm.weight"))
            query, key = apply_rope(query, key)
            projected = self.runtime.language_family(layer, "attention_out", attention(query, key, value))
            hidden = residual + projected[f"{prefix}.self_attn.o_proj"][:len(token_ids)]
            residual = hidden
            normed = rms_norm(hidden, self.weight(f"{prefix}.post_attention_layernorm.weight"))
            gate_up = self.runtime.language_family(layer, "gate_up", normed)
            gate = gate_up[f"{prefix}.mlp.gate_proj"][:len(token_ids)]
            up = gate_up[f"{prefix}.mlp.up_proj"][:len(token_ids)]
            down = self.runtime.language_family(layer, "mlp_down", silu(gate) * up)
            hidden = residual + down[f"{prefix}.mlp.down_proj"][:len(token_ids)]
            if not np.isfinite(hidden).all():
                raise FloatingPointError(f"non-finite hidden at layer {layer}")
            layer_ms.append((time.monotonic() - started) * 1000.0)
        hidden = rms_norm(hidden, self.weight("model.language_model.norm.weight"))
        logits = self.runtime.lm_head(hidden[-1:])[0]
        if logits.shape != (VOCAB,) or not np.isfinite(logits).all():
            raise RuntimeError("invalid lm_head output")
        return int(np.argmax(logits)), logits, layer_ms


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--overlay", type=Path, required=True)
    p.add_argument("--language", type=Path, required=True)
    p.add_argument("--head", type=Path, required=True)
    p.add_argument("--language-contract", type=Path, required=True)
    p.add_argument("--head-contract", type=Path, required=True)
    p.add_argument("--auxiliary", type=Path, required=True)
    p.add_argument("--auxiliary-manifest", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--weight-mode", choices=("resident-high-ddr", "staged-low-cma"),
                   default="staged-low-cma")
    args = p.parse_args()
    started = time.monotonic()
    result = {"gate": "M120-fixed-text-E2E", "status": "FAIL"}
    runtime = None
    auxiliary_npz = None
    try:
        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        token_ids = [int(v) for v in reference["prompt_token_ids"]]
        expected = [int(v) for v in reference["generated_token_ids"]]
        if len(token_ids) != 30 or len(expected) != 1:
            raise RuntimeError("only the frozen 30-token/one-token gate is accepted")
        aux_manifest = json.loads(args.auxiliary_manifest.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS" or aux_manifest.get("payload_sha256") != sha256(args.auxiliary):
            raise RuntimeError("auxiliary payload identity gate failed")
        auxiliary_npz = np.load(args.auxiliary, allow_pickle=False)
        auxiliary = {name: auxiliary_npz[name] for name in auxiliary_npz.files}
        runtime = M120BoardRuntime(args.overlay, args.language, args.head,
                                   args.language_contract, args.head_contract,
                                   weight_mode=args.weight_mode)
        model = FixedTextModel(runtime, auxiliary,
                               [int(v) for v in aux_manifest["selected_embedding_ids"]])
        generated, logits, layer_ms = model.run(token_ids)
        evidence = runtime.evidence()
        expected_calls = 154 + 8
        expected_macros = (runtime.language_contract.payload["contract"]["total_expected_macros"] +
                           runtime.head_contract.payload["contract"]["total_expected_macros"])
        hardware_ok = (
            evidence.get("logical_calls") == expected_calls
            and evidence.get("logical_expected_macros") == expected_macros
            and int(evidence.get("host_calls", -1)) >= expected_calls
            and int(evidence.get("expected_macros", -1)) >= expected_macros
            and evidence.get("activation_scale_policy")
            == "adaptive-power-of-two-finite-retry-v1"
        )
        passed = generated == expected[0] and hardware_ok
        result = {
            "gate": "M120-fixed-text-E2E", "status": "PASS" if passed else "FAIL",
            "classification": "fixed-reference first board gate; not arbitrary Web chat",
            "generated_token_id": generated, "expected_token_id": expected[0],
            "reference_match": generated == expected[0], "fpga_execution_proved": hardware_ok,
            "cpu_linear_fallback": False, "evidence": evidence,
            "expected_calls": expected_calls, "expected_macros": expected_macros,
            "timing": {"layer_ms": layer_ms, "language_ms": sum(layer_ms),
                       "total_ms": (time.monotonic() - started) * 1000.0,
                       "argmax_logit": float(logits[generated])},
        }
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["cpu_linear_fallback"] = False
        if runtime is not None:
            result["partial_evidence"] = runtime.evidence()
        result["traceback"] = traceback.format_exc()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
    finally:
        if runtime is not None:
            runtime.close()
        if auxiliary_npz is not None:
            auxiliary_npz.close()
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    print("M120_FIXED_TEXT_E2E_PASS" if result["status"] == "PASS" else "M120_FIXED_TEXT_E2E_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
