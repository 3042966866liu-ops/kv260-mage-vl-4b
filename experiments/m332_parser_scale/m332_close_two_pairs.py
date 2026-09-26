#!/usr/bin/env python3
"""Close the one forward and one reverse M332 fixed-video A/B pair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


RUNS = Path(__file__).resolve().parent
PAIRS = (
    ("M332-parser-scale-video-02", "baseline-then-candidate", ""),
    ("M332-parser-scale-video-03", "candidate-then-baseline", "REVERSE_"),
)
THRESHOLD_MS = 11536.0


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    records = []
    for dirname, order, prefix in PAIRS:
        directory = RUNS
        summary_path = directory / f"{prefix}SUMMARY.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary["status"] != "FAIL_E2E_GAIN":
            raise RuntimeError(f"unexpected pair status: {dirname}")
        if not summary["functional_output_identity"] or not summary["parser_module_identity"]:
            raise RuntimeError(f"functional/module identity failed: {dirname}")
        for variant in ("baseline", "candidate"):
            source = directory / f"{prefix}{variant.upper()}_BOARD_RESULT.json"
            if digest(source) != summary[f"{variant}_board_result_sha256"]:
                raise RuntimeError(f"board result hash changed: {source}")
            if summary[variant]["build_id"] != "0x4D395832":
                raise RuntimeError(f"build identity changed: {dirname}/{variant}")
            if summary[variant]["logical_fpga_calls"] != 778:
                raise RuntimeError(f"call count changed: {dirname}/{variant}")
            if summary[variant]["language_cpu_linear_fallback"] is not False:
                raise RuntimeError(f"CPU fallback detected: {dirname}/{variant}")
        baseline, candidate = summary["baseline"], summary["candidate"]
        if baseline["input_sha256"] != candidate["input_sha256"]:
            raise RuntimeError(f"input changed: {dirname}")
        if abs(summary["first_token_saved_ms"] -
               (baseline["first_token_ms"] - candidate["first_token_ms"])) > 1e-6:
            raise RuntimeError(f"timing arithmetic changed: {dirname}")
        records.append({
            "run": dirname,
            "order": order,
            "summary_sha256": digest(summary_path),
            "input_sha256": baseline["input_sha256"],
            "baseline_first_token_ms": baseline["first_token_ms"],
            "candidate_first_token_ms": candidate["first_token_ms"],
            "saved_ms": summary["first_token_saved_ms"],
            "baseline_vision_ms": baseline["vision_ms"],
            "candidate_vision_ms": candidate["vision_ms"],
            "baseline_language_ms": baseline["language_prefill_to_first_token_ms"],
            "candidate_language_ms": candidate["language_prefill_to_first_token_ms"],
            "language_candidate_minus_baseline_ms":
                candidate["language_prefill_to_first_token_ms"] - baseline["language_prefill_to_first_token_ms"],
            "vision_candidate_minus_baseline_ms": candidate["vision_ms"] - baseline["vision_ms"],
            "baseline_load_to_preprocess_ms": baseline["load_to_preprocess_ms"],
            "candidate_load_to_preprocess_ms": candidate["load_to_preprocess_ms"],
        })
    if records[0]["input_sha256"] != records[1]["input_sha256"]:
        raise RuntimeError("input differed across the two orders")
    savings = [record["saved_ms"] for record in records]
    closure = {
        "gate": "M332-two-order-fixed-video-closure",
        "status": "REJECT_NO_E2E_GAIN",
        "functional_status": "PASS_BOTH_ORDERS",
        "build_id": "0x4D395832",
        "pair_count": 2,
        "records": records,
        "required_min_saved_ms": THRESHOLD_MS,
        "observed_saved_ms": savings,
        "observed_mean_saved_ms": sum(savings) / len(savings),
        "candidate_faster_in_any_pair": any(value > 0 for value in savings),
        "candidate_met_preregistered_gain_in_any_pair": any(value >= THRESHOLD_MS for value in savings),
        "candidate_promoted": False,
        "stable_rollback_preserved": True,
        "subphase_attribution": "Unavailable: the 159-token video logs time language Prefill as a whole, not file I/O, parser, PL wait and PS separately.",
        "limits": "Two order-counterbalanced pairs reject observed end-to-end gain but do not prove a population-level slowdown, identify the cause of timing variance, or measure sustained Decode.",
        "next_step": "Close M332; profile the real 159-token language path by weight I/O, parsing, PL wait and PS before selecting one new bottleneck candidate.",
    }
    output = RUNS / "CLOSURE_REPRODUCED.json"
    output.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(closure, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
