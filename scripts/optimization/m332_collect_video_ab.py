#!/usr/bin/env python3
"""Recover two COM3 M332 video results and conservatively score the A/B."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path


def recover(log: Path, expected_sha: str, output: Path) -> dict:
    transcript = log.read_text(encoding="utf-8")
    match = re.search(r"(?m)^([A-Za-z0-9+/]{100,}={0,2})__M75C_UART_RC_0__", transcript)
    if not match:
        raise RuntimeError(f"missing complete base64 result in {log}")
    payload = base64.b64decode(match.group(1), validate=True)
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != expected_sha.lower():
        raise RuntimeError(f"board result hash mismatch: {log}: {actual_sha}")
    result = json.loads(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return result


def summary(result: dict) -> dict:
    proof = result.get("fpga_proof", {})
    token = next((x for x in result.get("final_output", []) if "token_id" in x), {})
    return {
        "status": result.get("status"),
        "m236_module_path": result.get("m236_module_path"),
        "m236_module_sha256": result.get("m236_module_sha256"),
        "input_sha256": result.get("submitted_tensor_sha256"),
        "selected_frame_indices": result.get("selected_frame_indices"),
        "prompt_tokens": result.get("prompt_tokens"),
        "first_token_ms": result.get("first_token_ms"),
        "vision_ms": result.get("stage_timing_ms", {}).get("vision"),
        "language_prefill_to_first_token_ms": result.get("stage_timing_ms", {}).get("language_prefill_to_first_token"),
        "load_to_preprocess_ms": result.get("stage_timing_ms", {}).get("process_start_and_runtime_load_to_preprocess"),
        "token_id": token.get("token_id"),
        "token_text": token.get("text"),
        "knife_verdict": token.get("knife_verdict"),
        "knife_score": token.get("knife_score"),
        "build_id": proof.get("build_id"),
        "logical_fpga_calls": proof.get("pl_logical_chain_calls"),
        "language_cpu_linear_fallback": proof.get("language_cpu_linear_fallback"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-log", required=True, type=Path)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--candidate-log", required=True, type=Path)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    baseline = recover(args.baseline_log, args.baseline_sha256, args.output_dir / "BASELINE_BOARD_RESULT.json")
    candidate = recover(args.candidate_log, args.candidate_sha256, args.output_dir / "CANDIDATE_BOARD_RESULT.json")
    a, b = summary(baseline), summary(candidate)
    keys = ("status", "input_sha256", "selected_frame_indices", "prompt_tokens", "token_id", "token_text",
            "knife_verdict", "knife_score", "build_id", "logical_fpga_calls", "language_cpu_linear_fallback")
    identity = all(a[key] == b[key] for key in keys)
    module_identity = (
        a["m236_module_sha256"] == "d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56"
        and b["m236_module_sha256"] == "7e36223f762cfc04c0fc74e3f468664e05d38b8f8024c8eb194e77cdc12944e8"
    )
    saved_ms = a["first_token_ms"] - b["first_token_ms"]
    threshold_ms = 11536.0
    performance_pass = identity and module_identity and saved_ms >= threshold_ms
    verdict = {
        "gate": "M332-fixed-video-same-input-AB",
        "status": "PASS_E2E_GAIN" if performance_pass else "FAIL_E2E_GAIN",
        "baseline_board_result_sha256": args.baseline_sha256.lower(),
        "candidate_board_result_sha256": args.candidate_sha256.lower(),
        "functional_output_identity": identity,
        "parser_module_identity": module_identity,
        "baseline": a,
        "candidate": b,
        "first_token_saved_ms": saved_ms,
        "preregistered_min_saved_ms": threshold_ms,
        "sample_pairs": 1,
        "performance_noise_resolved": False,
        "deployment_promoted": False,
        "limits": "One same-input A/B pair cannot establish repeatability; one output token/score is not full-logit equality; neither run measures sustained Decode.",
    }
    output = args.output_dir / "SUMMARY.json"
    output.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
