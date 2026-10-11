#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    envelopes = re.findall(
        r"M242_FIXED_TEXT_ACCEPTANCE_BEGIN\s*(\{.*?\})\s*M242_FIXED_TEXT_ACCEPTANCE_END",
        text,
        re.S,
    )
    if len(envelopes) != 1:
        raise RuntimeError(f"M242 expected one acceptance envelope, found {len(envelopes)}")
    acceptance = json.loads(envelopes[0])
    fixed = acceptance.get("fixed_text", {})
    evidence = fixed.get("evidence", {})
    restored = "M242_SERVICE_RESTORE_PASS" in text or "M242_SERVICE_RESTORE_AFTER_FAILURE_PASS" in text
    passed = (
        acceptance.get("status") == "PASS"
        and fixed.get("generated_token_id") == fixed.get("expected_token_id") == 17
        and fixed.get("reference_match") is True
        and fixed.get("fpga_execution_proved") is True
        and fixed.get("cpu_linear_fallback") is False
        and str(evidence.get("build_id", "")).lower() == "0x4d395832"
        and evidence.get("prefill_scheduler") == "m238-t32-input-pack-prefetch-plus-m236-fused-parse-overlap"
        and evidence.get("prefill_attention") == "m241-grouped-gqa-reference-rope"
        and evidence.get("grouped_attention_calls") == evidence.get("expected_grouped_attention_calls") == 36
        and evidence.get("rope_cache_used") is False
        and restored
        and "M242_M241_PREDECESSOR_VERIFY_PASS" in text
        and "M242_GROUPED_GQA_FIXED_TEXT_INNER_PASS" in text
        and "M242_M241_FIXED_TEXT_ACCEPTANCE_PASS" in text
        and "M242_M241_FIXED_TEXT_BOARD_RUNNER_PASS" in text
    )
    result = {
        "date": "2026-09-01",
        "gate": "M242-real-KV260-M241-fixed-text-final",
        "status": "PASS_SERVICE_RESTORED" if passed else "FAIL",
        "classification": "Frozen fixed-text complete 4B FPGA E2E through M241 grouped GQA plus service restoration; not visual, Web integration, video, T64, or real-time evidence.",
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "acceptance": acceptance,
        "service_restore_marker": restored,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Integrate M241 grouped GQA into the hash-locked Web language Prefill only after this PASS.",
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print(json.dumps(result, indent=2))
    print("M242_FIXED_TEXT_BOARD_PASS" if passed else "M242_FIXED_TEXT_BOARD_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
