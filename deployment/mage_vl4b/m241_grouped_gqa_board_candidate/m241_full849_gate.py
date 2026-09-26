#!/usr/bin/env python3
"""M241 complete 849-token language Prefill promotion gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import traceback
from collections import defaultdict
from pathlib import Path

import numpy as np

from m238_prefill_runtime import M238PrefillRuntime
from m241_video_language_runtime import M241VideoLanguageModel


TOKENS, HIDDEN = 849, 2560
EXPECTED_FAMILIES = 154
EXPECTED_T32_BLOCKS = 4158
EXPECTED_LOGICAL_CALLS = 4166
EXPECTED_GROUPED_ATTENTION_CALLS = 36
M239_PREFILL_WALL_MS = 709754.5216220024
M239_GENERATED_TOKEN_ID = 40183
REQUIRED_WALL_SPEEDUP = 1.003


def deterministic_hidden() -> np.ndarray:
    token = np.arange(TOKENS, dtype=np.float32)[:, None]
    channel = np.arange(HIDDEN, dtype=np.float32)[None, :]
    values = np.sin(token * np.float32(0.015625) + channel * np.float32(0.0009765625))
    values += np.cos(token * np.float32(0.0078125) - channel * np.float32(0.00048828125))
    return (values * np.float32(0.125)).astype(np.float32)


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


class ProfiledM241Model(M241VideoLanguageModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.family_invocations = 0
        self.family_wall_ms: dict[str, float] = {}
        self.layer_family_wall_ms: dict[int, float] = defaultdict(float)

    def _family(self, layer: int, family: str, values: np.ndarray) -> dict[str, np.ndarray]:
        if family in {"q", "qkv"}:
            print(f"M241_LAYER_BEGIN layer={layer} tokens={values.shape[0]}", flush=True)
        started = time.monotonic()
        result = super()._family(layer, family, values)
        elapsed_ms = (time.monotonic() - started) * 1000.0
        key = f"{layer}:{family}"
        self.family_invocations += 1
        self.family_wall_ms[key] = elapsed_ms
        self.layer_family_wall_ms[layer] += elapsed_ms
        print(
            f"M241_FAMILY_PASS ordinal={self.family_invocations}/{EXPECTED_FAMILIES} "
            f"layer={layer} family={family} ms={elapsed_ms:.3f}",
            flush=True,
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "overlay", "language", "head", "language_contract", "head_contract",
        "auxiliary", "result",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    runtime = None
    model = None
    result = {"gate": "M241-real-KV260-complete-849-token-grouped-GQA-Prefill", "status": "FAIL"}
    try:
        runtime = M238PrefillRuntime(
            args.overlay,
            args.language,
            args.head,
            args.language_contract,
            args.head_contract,
            weight_mode="staged-low-cma",
        )
        model = ProfiledM241Model(runtime, args.auxiliary)
        hidden = deterministic_hidden()
        before = runtime.evidence()
        print("M241_PREFILL_BEGIN tokens=849 grouped_gqa=true rope_cache=false", flush=True)
        started = time.monotonic()
        token_id, logits, cache = model.prefill(hidden)
        prefill_ms = (time.monotonic() - started) * 1000.0
        after = runtime.evidence()
        logical_calls = int(after["logical_calls"]) - int(before["logical_calls"])
        physical_calls = int(after["host_calls"]) - int(before["host_calls"])
        t32_blocks = sum(int(value) for value in after["family_t32_blocks"].values())
        stage_count = sum(int(value) for value in after["family_stage_count"].values())
        prefetch_submissions = int(after["pack_prefetch_submissions"]) - int(before["pack_prefetch_submissions"])
        cache_finite = all(np.isfinite(x).all() for x in cache.keys + cache.values)
        cache_shapes_valid = len(cache.keys) == 36 and len(cache.values) == 36 and all(
            x.shape == (TOKENS, 8, 128) for x in cache.keys + cache.values
        )
        wall_speedup = M239_PREFILL_WALL_MS / prefill_ms
        structural = (
            model.family_invocations == EXPECTED_FAMILIES
            and len(model.layer_family_wall_ms) == 36
            and model.grouped_attention_calls == EXPECTED_GROUPED_ATTENTION_CALLS
            and model.rope_cache_used is False
            and logical_calls == EXPECTED_LOGICAL_CALLS
            and t32_blocks == EXPECTED_T32_BLOCKS
            and stage_count == EXPECTED_FAMILIES
            and prefetch_submissions == EXPECTED_T32_BLOCKS
            and physical_calls >= logical_calls
            and int(token_id) == M239_GENERATED_TOKEN_ID
            and np.isfinite(logits).all()
            and cache_finite
            and cache_shapes_valid
            and str(after["build_id"]).lower() == "0x4d395832"
            and after["input_packet_contract_changed"] is False
            and after["fpga_transaction_contract_changed"] is False
            and after["model_math_changed"] is False
        )
        passed = structural and wall_speedup >= REQUIRED_WALL_SPEEDUP
        result = {
            "gate": "M241-real-KV260-complete-849-token-grouped-GQA-Prefill",
            "status": "PASS" if passed else "FAIL_NOT_PROMOTED",
            "classification": "Real-KV260 complete frozen-shape 849-token language-only Prefill using grouped GQA only and accepted reference RoPE; not visual, Web, video, T64, semantic-reference, or real-time evidence.",
            "build_id": after["build_id"],
            "tokens": TOKENS,
            "layers_completed": len(model.layer_family_wall_ms),
            "family_invocations": model.family_invocations,
            "expected_family_invocations": EXPECTED_FAMILIES,
            "grouped_attention_calls": model.grouped_attention_calls,
            "expected_grouped_attention_calls": EXPECTED_GROUPED_ATTENTION_CALLS,
            "grouped_attention_wall_ms": model.grouped_attention_wall_ms,
            "rope_cache_used": model.rope_cache_used,
            "logical_calls": logical_calls,
            "expected_logical_calls": EXPECTED_LOGICAL_CALLS,
            "physical_calls": physical_calls,
            "t32_blocks": t32_blocks,
            "expected_t32_blocks": EXPECTED_T32_BLOCKS,
            "generated_token_id": int(token_id),
            "expected_generated_token_id": M239_GENERATED_TOKEN_ID,
            "generated_token_match": int(token_id) == M239_GENERATED_TOKEN_ID,
            "argmax_logit": float(np.max(logits)),
            "logits_sha256_fp32": array_sha256(np.asarray(logits, np.float32)),
            "logits_finite": bool(np.isfinite(logits).all()),
            "cache_finite": bool(cache_finite),
            "cache_shapes_valid": bool(cache_shapes_valid),
            "prefill_wall_ms": prefill_ms,
            "m239_prefill_wall_ms": M239_PREFILL_WALL_MS,
            "wall_speedup_vs_m239": wall_speedup,
            "required_wall_speedup": REQUIRED_WALL_SPEEDUP,
            "family_wall_total_ms": float(sum(model.family_wall_ms.values())),
            "family_wall_ms": model.family_wall_ms,
            "runtime_phase_ms": after["phase_ms"],
            "runtime_phase_calls": after["phase_calls"],
            "pipeline_retry_launches": after["pipeline_retry_launches"] - before["pipeline_retry_launches"],
            "scale_retry_count": after["scale_retry_count"] - before["scale_retry_count"],
            "cpu_linear_fallback": False,
            "visual_tower_executed": False,
            "semantic_reference_compared": False,
            "model_math_changed": False,
            "fpga_transaction_contract_changed": False,
        }
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
        if runtime is not None:
            result["partial_evidence"] = runtime.evidence()
    finally:
        if model is not None:
            model.close()
        if runtime is not None:
            runtime.close()
        args.result.parent.mkdir(parents=True, exist_ok=True)
        partial = args.result.with_name(args.result.name + ".partial")
        partial.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        partial.replace(args.result)
        print("M241_RESULT_BEGIN", flush=True)
        print(json.dumps(result, indent=2), flush=True)
        print("M241_RESULT_END", flush=True)
    print("M241_COMPLETE_849_PREFILL_PASS" if result["status"] == "PASS" else "M241_COMPLETE_849_PREFILL_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
