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
    matches = re.findall(
        r"M239_PROFILE_RESULT_BEGIN\s*(\{.*?\})\s*M239_PROFILE_RESULT_END",
        text,
        flags=re.S,
    )
    if len(matches) != 1:
        raise RuntimeError(f"M239 expected one profile envelope, found {len(matches)}")
    profile = json.loads(matches[0])
    restored = "M239_SERVICE_RESTORE_PASS" in text or "M239_SERVICE_RESTORE_AFTER_FAILURE_PASS" in text
    measured = (
        profile.get("status") == "MEASURED"
        and restored
        and "M239_COMPLETE_849_PROFILE_BOARD_RUNNER_PASS" in text
    )
    value = {
        "date": "2026-09-01",
        "gate": "M239-real-KV260-complete-849-token-language-prefill-profile-acceptance",
        "status": "MEASURED_SERVICE_RESTORED" if measured else "FAIL",
        "classification": "Real KV260 complete 849-token language-only Prefill profile using M238; measurement evidence only, not a semantic, visual, Web, T64, or real-time PASS.",
        "candidate_build_id": profile.get("build_id"),
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "profile": profile,
        "service_restore_marker": restored,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Use measured phase and family totals to select one isolated non-T64 optimization; do not promote Web or claim full-model speedup from this profile alone.",
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print(json.dumps(value, indent=2))
    print("M239_BOARD_PROFILE_ACCEPTANCE_PASS" if measured else "M239_BOARD_PROFILE_ACCEPTANCE_FAIL")
    return 0 if measured else 1


if __name__ == "__main__":
    raise SystemExit(main())
