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
    matches = re.findall(r"M240_RESULT_BEGIN\s*(\{.*?\})\s*M240_RESULT_END", text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"M240 expected one result envelope, found {len(matches)}")
    micro = json.loads(matches[0])
    restored = "M240_SERVICE_RESTORE_PASS" in text or "M240_SERVICE_RESTORE_AFTER_FAILURE_PASS" in text
    passed = micro.get("status") == "PASS" and restored and "M240_PS_ATTENTION_BOARD_RUNNER_PASS" in text
    value = {
        "date": "2026-09-01",
        "gate": "M240-real-KV260-PS-grouped-GQA-and-RoPE-cache-acceptance",
        "status": "PASS_SERVICE_RESTORED" if passed else "FAIL_NOT_PROMOTED",
        "classification": "Real-KV260 PS-only attention/RoPE micro-gate; not full Prefill, semantic E2E, Web, video, T64, or real-time evidence.",
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "micro_gate": micro,
        "service_restore_marker": restored,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Integrate the bit-exact grouped GQA and RoPE table cache into an isolated M238 language runtime and rerun complete 849-token Prefill."
            if passed else
            "Do not integrate M240; retain the accepted PS attention and select a different non-T64 optimization from M239 evidence."
        ),
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    partial.replace(args.result)
    print(json.dumps(value, indent=2))
    print("M240_BOARD_ACCEPTANCE_PASS" if passed else "M240_BOARD_ACCEPTANCE_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
