#!/usr/bin/env python3
"""Fail-closed collection of the M325 COM3 full-session experiment."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        raise RuntimeError("result already exists; refuse overwrite")
    raw = args.log.read_bytes()
    content = raw.decode("utf-8", errors="replace").replace("\r", "")
    pattern = r"__M325_FULL_RESULT_BEGIN__\n(\{[^\n]*\})\n__M325_FULL_RESULT_END__"
    rows = [json.loads(match) for match in re.findall(pattern, content)]
    if len(rows) != 2 or [row.get("mode") for row in rows] != ["stable", "candidate"]:
        raise RuntimeError("expected exactly stable then candidate video results")
    stable, candidate = rows
    if "M325_REUSED_FIXED_TEXT_PASS" not in content:
        raise RuntimeError("validated fixed-text gate reuse missing")
    for marker in ("M277_PACKAGE_VERIFY_PASS", "M254_COMPLETE_DEPENDENCY_PREFLIGHT_PASS",
                   "M136_M120_BOARD_ENV_PASS", "OP01_DECODE_ONE_BOARD_ENV_PASS",
                   "M325_FULL_SESSION_RUNNER_PASS", "M254_KV260_DUAL_PATH_RUNTIME_READY_PASS",
                   "__M325_GATE_RC_0__", "__M325_RESTORE_RC_0__", "__M75C_UART_RC_0__"):
        if marker not in content:
            raise RuntimeError("missing completion marker: " + marker)
    if stable["status"] != "PASS_REFERENCE" or candidate["status"] != "PASS_EXPERIMENTAL":
        raise RuntimeError("board status did not pass")
    if stable["build_id"] != "0x4D395832" or candidate["build_id"] != "0x4F503131":
        raise RuntimeError("Build-ID mismatch")
    if candidate.get("capacity_status") != "STOPPED_BY_USER_NOT_PASS" or candidate["formal_promotion_allowed"]:
        raise RuntimeError("capacity status incorrectly promoted")
    if stable["scope"] != "video" or candidate["scope"] != "video":
        raise RuntimeError("not a video session")
    if candidate.get("stable_reference_exact") is not True:
        raise RuntimeError("candidate reference comparison not exact")
    for key in ("frames_sha256", "prompt_tokens", "generated_tokens", "token_ids",
                "eos_ids", "logits_sha256", "final_kv_sha256", "final_kv_length",
                "logical_fpga_calls", "expected_logical_fpga_calls"):
        if stable[key] != candidate[key]:
            raise RuntimeError("stable/candidate mismatch: " + key)
    if (stable["prompt_tokens"] != 159 or stable["generated_tokens"] != 4 or
            stable["logical_fpga_calls"] != 1264 or stable["eos_ids"] != [1]):
        raise RuntimeError("frozen geometry, call count or EOS changed")
    if len(stable["logits_sha256"]) != 4 or len(stable["final_kv_sha256"]) != 72:
        raise RuntimeError("incomplete numerical evidence")
    if len(set(stable["final_kv_length"])) != 1 or stable["final_kv_length"][0] != 162:
        raise RuntimeError("final KV length not 162")
    for row in rows:
        if row["cleanup"].get("recovery_required") or row["cleanup"].get("errors"):
            raise RuntimeError("unsafe board cleanup")
        if row["logical_fpga_calls"] != row["expected_logical_fpga_calls"]:
            raise RuntimeError("FPGA calls mismatch")
    stable_ttft = stable["first_token_ms"] / 1000
    candidate_ttft = candidate["first_token_ms"] / 1000
    stable_decode = stable["decode_intervals_ms"]
    candidate_decode = candidate["decode_intervals_ms"]
    result = {
        "date": "2026-09-26", "gate": "M325-BACT159-same-session-video-and-Decode-one",
        "status": "PASS_NUMERICAL_EXPERIMENTAL_PERFORMANCE_NOT_FASTER",
        "classification": "real KV260 same-session fixed-video measurement; candidate not formally promoted",
        "uart_log": str(args.log.as_posix()), "uart_log_sha256": sha(raw),
        "board_results": {
            "stable": "/home/ubuntu/tellme_m120_m89x2_20260901/results/m325_full_session_02/video_stable.json",
            "candidate": "/home/ubuntu/tellme_m120_m89x2_20260901/results/m325_full_session_02/video_candidate.json",
        },
        "board_full_result_sha256": {row["mode"]: row["full_board_result_sha256"] for row in rows},
        "reused_fixed_text_gate": True, "same_session_video_and_decode_per_mode": True,
        "stable_service_restored": True, "stable_rollback_preserved": True,
        "prompt_tokens": 159, "visual_tokens": 98, "t32_batches": 5,
        "logical_fpga_calls_per_session": 1264,
        "full_logits_each_step_exact": True, "final_72_kv_hashes_exact": True,
        "final_kv_length": 162, "token_ids": stable["token_ids"], "eos_index": 1,
        "continuation_after_eos": True,
        "measurement_scope": "three forced incremental Decode steps after constrained first token; user-facing answer terminates at EOS",
        "model_runtime_load_excluded": True,
        "stable": {
            "build_id": stable["build_id"], "first_token_s": stable_ttft,
            "vision_s": stable["stage_ms"]["vision"] / 1000,
            "prefill_to_first_token_s": stable["stage_ms"]["prefill_to_first_token"] / 1000,
            "decode_step_s": [x / 1000 for x in stable_decode],
            "three_decode_s": sum(stable_decode) / 1000,
            "three_decode_tokens_per_s": stable["decode_tokens_per_second"],
            "four_token_elapsed_s": stable["token_ready_ms"][-1] / 1000,
        },
        "candidate": {
            "build_id": candidate["build_id"], "first_token_s": candidate_ttft,
            "vision_s": candidate["stage_ms"]["vision"] / 1000,
            "prefill_to_first_token_s": candidate["stage_ms"]["prefill_to_first_token"] / 1000,
            "decode_step_s": [x / 1000 for x in candidate_decode],
            "three_decode_s": sum(candidate_decode) / 1000,
            "three_decode_tokens_per_s": candidate["decode_tokens_per_second"],
            "four_token_elapsed_s": candidate["token_ready_ms"][-1] / 1000,
        },
        "paired_difference": {
            "candidate_minus_stable_ttft_s": candidate_ttft - stable_ttft,
            "candidate_minus_stable_three_decode_s": (sum(candidate_decode) - sum(stable_decode)) / 1000,
            "candidate_over_stable_three_decode_throughput":
                candidate["decode_tokens_per_second"] / stable["decode_tokens_per_second"],
        },
        "capacity_status": "STOPPED_BY_USER_NOT_PASS",
        "formal_candidate_promotion_allowed": False,
        "formal_performance_improvement_proved": False,
        "rejected_attempt": "m325_full_session_01 video stopped before FPGA inference: progress callback accepted one argument but received two; text gates reused after exact verification",
        "next_step": "Keep stable T32 service; if pursuing Decode-one, close RTL capacity gate and repeat order-balanced measurements, preferably with a non-EOS-generating prompt",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M325_COLLECT_PASS " + str(args.result))


if __name__ == "__main__":
    main()
