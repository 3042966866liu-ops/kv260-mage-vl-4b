#!/usr/bin/env python3
"""Real KV260 M236-versus-M238 frozen 849-token q-family gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import traceback
from pathlib import Path

import numpy as np

from m236_prefill_runtime import M236PrefillRuntime
from m238_prefill_runtime import M238PrefillRuntime


def deterministic_input(tokens: int, width: int) -> np.ndarray:
    token = np.arange(tokens, dtype=np.float32)[:, None]
    channel = np.arange(width, dtype=np.float32)[None, :]
    values = np.sin(token * np.float32(0.03125) + channel * np.float32(0.001953125))
    values += np.cos(token * np.float32(0.015625) - channel * np.float32(0.0009765625))
    return (values * np.float32(0.25)).astype(np.float32)


def sha(values: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(values, dtype="<f4"))).hexdigest()


def delta(after: dict, before: dict) -> dict:
    return {key: float(after[key]) - float(before.get(key, 0.0)) for key in after}


def main() -> int:
    p = argparse.ArgumentParser()
    for name in ("overlay", "language", "head", "language_contract", "head_contract", "result"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    p.add_argument("--tokens", type=int, default=849)
    a = p.parse_args()
    started = time.monotonic()
    runtime = None
    result = {"gate": "M238-real-KV260-T32-input-pack-prefetch", "status": "FAIL"}
    try:
        if a.tokens != 849:
            raise RuntimeError("M238 requires the frozen 849-token workload")
        runtime = M238PrefillRuntime(
            a.overlay, a.language, a.head, a.language_contract, a.head_contract,
            weight_mode="staged-low-cma",
        )
        values = deterministic_input(a.tokens, 2560)
        blocks = (a.tokens + 31) // 32
        before_phase = dict(runtime.phase_ms)
        before_pipe = runtime.pipeline_submissions
        baseline_started = time.monotonic()
        baseline_update = M236PrefillRuntime.language_family_many(runtime, 0, "q", values)
        baseline_ms = (time.monotonic() - baseline_started) * 1000.0
        baseline_phase = delta(runtime.phase_ms, before_phase)
        baseline_pipeline = runtime.pipeline_submissions - before_pipe

        before_phase = dict(runtime.phase_ms)
        before_pipe = runtime.pipeline_submissions
        before_prefetch = runtime.pack_prefetch_submissions
        before_prepacked = runtime.prepacked_launches
        candidate_started = time.monotonic()
        candidate_update = runtime.language_family_many(0, "q", values)
        candidate_ms = (time.monotonic() - candidate_started) * 1000.0
        candidate_phase = delta(runtime.phase_ms, before_phase)
        candidate_pipeline = runtime.pipeline_submissions - before_pipe
        evidence = runtime.evidence()

        name = "model.language_model.layers.0.self_attn.q_proj"
        baseline = np.asarray(baseline_update[name], dtype=np.float32)
        candidate = np.asarray(candidate_update[name], dtype=np.float32)
        exact = bool(np.array_equal(candidate, baseline))
        maximum_abs = float(np.max(np.abs(candidate - baseline)))
        speedup = baseline_ms / candidate_ms
        prefetch_delta = int(evidence["pack_prefetch_submissions"]) - before_prefetch
        prepacked_delta = int(evidence["prepacked_launches"]) - before_prepacked
        passed = (
            exact and maximum_abs == 0.0 and candidate.shape == (849, 4096)
            and baseline_pipeline == blocks and candidate_pipeline == blocks
            and prefetch_delta == blocks and prepacked_delta == blocks
            and int(evidence["host_calls"]) == 2 * blocks
            and int(evidence["pipeline_retry_launches"]) == 0
            and int(evidence["fused_nonfinite_detections"]) == 0
            and evidence["adaptive_scale_retry_preserved"] is True
            and evidence["standalone_raw_finite_scan"] is False
            and evidence["input_packet_contract_changed"] is False
            and evidence["fpga_transaction_contract_changed"] is False
            and evidence["model_math_changed"] is False
            and str(evidence["build_id"]).lower() == "0x4d395832"
            and speedup >= 1.03
        )
        result = {
            "gate": "M238-real-KV260-T32-input-pack-prefetch",
            "status": "PASS" if passed else "REJECTED_OR_FAIL",
            "classification": "One real 849-token layer-0 q-family T32 host-pipeline comparison; independent of T64; not fixed-text, video, Web, or real-time evidence.",
            "build_id": evidence["build_id"],
            "tokens": a.tokens,
            "t32_blocks_per_run": blocks,
            "m236_wall_ms": baseline_ms,
            "m238_wall_ms": candidate_ms,
            "wall_speedup": speedup,
            "required_wall_speedup": 1.03,
            "m236_phase_ms": baseline_phase,
            "m238_phase_ms": candidate_phase,
            "output_bit_exact": exact,
            "maximum_abs_error": maximum_abs,
            "m236_output_sha256_fp32": sha(baseline),
            "m238_output_sha256_fp32": sha(candidate),
            "host_calls": evidence["host_calls"],
            "expected_host_calls": 2 * blocks,
            "pack_prefetch_submissions": prefetch_delta,
            "prepacked_launches": prepacked_delta,
            "pack_prefetch_wait_ms_total": evidence["pack_prefetch_wait_ms"],
            "pack_prefetch_compute_ms_total": evidence["pack_prefetch_compute_ms"],
            "pipeline_retry_launches": evidence["pipeline_retry_launches"],
            "fused_nonfinite_detections": evidence["fused_nonfinite_detections"],
            "adaptive_scale_retry_preserved": evidence["adaptive_scale_retry_preserved"],
            "cpu_linear_fallback": False,
            "model_math_changed": False,
            "fpga_transaction_contract_changed": False,
            "total_ms": (time.monotonic() - started) * 1000.0,
        }
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        if runtime is not None:
            result["partial_evidence"] = runtime.evidence()
    finally:
        if runtime is not None:
            runtime.close()
        a.result.parent.mkdir(parents=True, exist_ok=True)
        a.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("M238_BOARD_FAMILY_RESULT_BEGIN", flush=True)
        print(json.dumps(result, indent=2), flush=True)
        print("M238_BOARD_FAMILY_RESULT_END", flush=True)
    print("M238_INPUT_PREFETCH_BOARD_PASS" if result["status"] == "PASS" else "M238_INPUT_PREFETCH_BOARD_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
