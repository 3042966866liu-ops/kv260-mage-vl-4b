#!/usr/bin/env python3
"""Real-KV260 M230-versus-M231 849-token family equivalence/timing gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import traceback
from pathlib import Path

import numpy as np

from m230_prefill_runtime import M230PrefillRuntime
from m231_prefill_runtime import M231PrefillRuntime


def deterministic_input(tokens: int, width: int) -> np.ndarray:
    token = np.arange(tokens, dtype=np.float32)[:, None]
    channel = np.arange(width, dtype=np.float32)[None, :]
    values = np.sin(token * np.float32(0.03125) + channel * np.float32(0.001953125))
    values += np.cos(token * np.float32(0.015625) - channel * np.float32(0.0009765625))
    return (values * np.float32(0.25)).astype(np.float32)


def tensor_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(values, dtype="<f4"))).hexdigest()


def phase_delta(after: dict[str, float], before: dict[str, float]) -> dict[str, float]:
    return {name: float(after[name]) - float(before.get(name, 0.0)) for name in after}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--language", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--language-contract", type=Path, required=True)
    parser.add_argument("--head-contract", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--tokens", type=int, default=849)
    args = parser.parse_args()

    started = time.monotonic()
    runtime = None
    result: dict[str, object] = {
        "gate": "M231-real-KV260-direct-final-buffer-family-equivalence",
        "status": "FAIL",
        "classification": "One real 849-token layer-0 q_proj family on accepted M120 T32; not fixed-text E2E, full video, Web, or real-time evidence.",
    }
    try:
        if args.tokens != 849:
            raise RuntimeError("M231 board gate requires the frozen 849-token workload")
        runtime = M231PrefillRuntime(
            args.overlay,
            args.language,
            args.head,
            args.language_contract,
            args.head_contract,
            weight_mode="staged-low-cma",
        )
        values = deterministic_input(args.tokens, 2560)
        blocks = (args.tokens + 31) // 32

        before = dict(runtime.phase_ms)
        stage_bytes_before = int(runtime.stage_bytes)
        stage_ms_before = float(runtime.stage_ms)
        baseline_started = time.monotonic()
        baseline_update = M230PrefillRuntime.language_family_many(runtime, 0, "q", values)
        baseline_ms = (time.monotonic() - baseline_started) * 1000.0
        baseline_phase = phase_delta(runtime.phase_ms, before)
        baseline_stage_bytes = int(runtime.stage_bytes) - stage_bytes_before
        baseline_stage_ms = float(runtime.stage_ms) - stage_ms_before

        before = dict(runtime.phase_ms)
        stage_bytes_before = int(runtime.stage_bytes)
        stage_ms_before = float(runtime.stage_ms)
        candidate_started = time.monotonic()
        candidate_update = runtime.language_family_many(0, "q", values)
        candidate_ms = (time.monotonic() - candidate_started) * 1000.0
        candidate_phase = phase_delta(runtime.phase_ms, before)
        candidate_stage_bytes = int(runtime.stage_bytes) - stage_bytes_before
        candidate_stage_ms = float(runtime.stage_ms) - stage_ms_before

        name = "model.language_model.layers.0.self_attn.q_proj"
        baseline = np.asarray(baseline_update[name], dtype=np.float32)
        candidate = np.asarray(candidate_update[name], dtype=np.float32)
        exact = bool(np.array_equal(candidate, baseline))
        maximum_abs = float(np.max(np.abs(candidate - baseline)))
        evidence = runtime.evidence()
        family_key = "0:q"
        passed = (
            exact
            and maximum_abs == 0.0
            and candidate.shape == (args.tokens, 4096)
            and int(evidence["host_calls"]) == 2 * blocks
            and int(evidence["family_stage_count"].get(family_key, 0)) == 2
            and int(evidence["family_t32_blocks"].get(family_key, 0)) == 2 * blocks
            and int(evidence["family_output_allocations"].get(family_key, 0)) == 1
            and int(evidence["parse_temporary_result_dicts"]) == 0
            and evidence["build_id"].lower() == "0x4d395832"
            and evidence["model_math_changed"] is False
            and evidence["fpga_transaction_contract_changed"] is False
        )
        result = {
            "gate": "M231-real-KV260-direct-final-buffer-family-equivalence",
            "status": "PASS" if passed else "FAIL",
            "classification": "One real 849-token layer-0 q_proj family on accepted M120 T32; not fixed-text E2E, full video, Web, or real-time evidence.",
            "build_id": evidence["build_id"],
            "tokens": args.tokens,
            "t32_blocks_per_run": blocks,
            "output_shape": list(candidate.shape),
            "m230_wall_ms": baseline_ms,
            "m231_wall_ms": candidate_ms,
            "wall_speedup": baseline_ms / candidate_ms,
            "m230_parse_ms": baseline_phase["parse"],
            "m231_parse_ms": candidate_phase["parse"],
            "parse_speedup": baseline_phase["parse"] / candidate_phase["parse"],
            "m230_phase_ms": baseline_phase,
            "m231_phase_ms": candidate_phase,
            "m230_stage_bytes": baseline_stage_bytes,
            "m231_stage_bytes": candidate_stage_bytes,
            "m230_stage_ms": baseline_stage_ms,
            "m231_stage_ms": candidate_stage_ms,
            "output_bit_exact": exact,
            "maximum_abs_error": maximum_abs,
            "m230_output_sha256_fp32": tensor_sha256(baseline),
            "m231_output_sha256_fp32": tensor_sha256(candidate),
            "host_calls": evidence["host_calls"],
            "expected_host_calls": 2 * blocks,
            "family_output_allocations": evidence["family_output_allocations"],
            "parse_temporary_result_dicts": evidence["parse_temporary_result_dicts"],
            "output_parser": evidence["output_parser"],
            "model_math_changed": False,
            "fpga_transaction_contract_changed": False,
            "cpu_linear_fallback": False,
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
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("M231_BOARD_FAMILY_RESULT_BEGIN", flush=True)
        print(json.dumps(result, indent=2), flush=True)
        print("M231_BOARD_FAMILY_RESULT_END", flush=True)
    print(
        "M231_PARSE_REUSE_FAMILY_BOARD_PASS"
        if result["status"] == "PASS"
        else "M231_PARSE_REUSE_FAMILY_BOARD_FAIL",
        flush=True,
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
