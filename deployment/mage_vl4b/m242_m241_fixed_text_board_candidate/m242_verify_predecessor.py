#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    measurement = json.loads(args.measurement.read_text(encoding="utf-8"))
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    passed = (
        summary.get("status") == "PASS"
        and canonical_sha(measurement) == summary.get("prefill_gate_canonical_sha256")
        and measurement.get("status") == "PASS"
        and str(measurement.get("build_id", "")).lower() == "0x4d395832"
        and measurement.get("tokens") == 849
        and measurement.get("layers_completed") == 36
        and measurement.get("grouped_attention_calls") == 36
        and measurement.get("rope_cache_used") is False
        and measurement.get("logical_calls") == 4166
        and measurement.get("generated_token_id") == 40183
        and measurement.get("generated_token_match") is True
        and measurement.get("logits_finite") is True
        and measurement.get("cache_finite") is True
        and measurement.get("cpu_linear_fallback") is False
    )
    if not passed:
        raise RuntimeError("M242 exact M241 predecessor identity failed")
    print("M242_M241_PREDECESSOR_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
