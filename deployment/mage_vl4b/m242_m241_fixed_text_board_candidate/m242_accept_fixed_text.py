#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed", type=Path, required=True)
    parser.add_argument("--accepted-fixed-reference", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    fixed = json.loads(args.fixed.read_text(encoding="utf-8"))
    reference = json.loads(args.accepted_fixed_reference.read_text(encoding="utf-8"))
    evidence = fixed.get("evidence", {})
    attempts = evidence.get("scale_attempts", [])
    retry_launches = int(evidence.get("pipeline_retry_launches", -1))
    nonfinite = int(evidence.get("fused_nonfinite_detections", -2))
    retry_count = int(evidence.get("scale_retry_count", -3))
    attempts_with_retry = sum(max(0, len(x.get("attempted_shifts", [])) - 1) for x in attempts)
    selected_final = all(
        x.get("attempted_shifts") and x.get("selected_shift") == x.get("attempted_shifts")[-1]
        for x in attempts
    )
    retry_ok = (
        retry_launches >= 0
        and retry_launches == nonfinite == retry_count == attempts_with_retry
        and int(evidence.get("host_calls", -1)) == int(evidence.get("logical_calls", -2)) + retry_launches
        and selected_final
    )
    checks = {
        "inner_pass": fixed.get("status") == "PASS",
        "token_17_exact": fixed.get("generated_token_id") == reference.get("generated_token_id") == 17,
        "expected_token_17": fixed.get("expected_token_id") == reference.get("expected_token_id") == 17,
        "reference_match": fixed.get("reference_match") is True,
        "fpga_execution_proved": fixed.get("fpga_execution_proved") is True,
        "no_cpu_linear_fallback": fixed.get("cpu_linear_fallback") is False,
        "build_id_exact": str(evidence.get("build_id", "")).lower() == "0x4d395832",
        "scheduler_exact": evidence.get("prefill_scheduler") == "m238-t32-input-pack-prefetch-plus-m236-fused-parse-overlap",
        "grouped_gqa_exact": evidence.get("prefill_attention") == "m241-grouped-gqa-reference-rope",
        "grouped_attention_calls": evidence.get("grouped_attention_calls") == evidence.get("expected_grouped_attention_calls") == 36,
        "reference_rope_retained": evidence.get("rope_cache_used") is False,
        "retry_bookkeeping_resolved": retry_ok,
        "no_standalone_raw_scan": evidence.get("standalone_raw_finite_scan") is False,
        "adaptive_retry_preserved": evidence.get("adaptive_scale_retry_preserved") is True,
        "model_math_contract_unchanged": evidence.get("model_math_changed") is False,
        "fpga_transaction_contract_unchanged": evidence.get("fpga_transaction_contract_changed") is False,
    }
    passed = all(checks.values())
    result = {
        "gate": "M242-real-KV260-M241-fixed-text-acceptance",
        "status": "PASS" if passed else "FAIL",
        "classification": "Frozen fixed-text complete 4B FPGA E2E through M241 grouped GQA; not visual, Web, video, T64, or real-time evidence.",
        "checks": checks,
        "fixed_text": fixed,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print("M242_FIXED_TEXT_ACCEPTANCE_BEGIN")
    print(json.dumps(result, indent=2))
    print("M242_FIXED_TEXT_ACCEPTANCE_END")
    print("M242_M241_FIXED_TEXT_ACCEPTANCE_PASS" if passed else "M242_M241_FIXED_TEXT_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
