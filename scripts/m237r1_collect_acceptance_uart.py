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
        r"M237R1_ACCEPTANCE_BEGIN\s*(\{.*?\})\s*M237R1_ACCEPTANCE_END", text, re.S
    )
    if len(matches) != 1:
        raise RuntimeError(f"M237R1 expected one acceptance envelope, found {len(matches)}")
    acceptance = json.loads(matches[0])
    service_match = re.search(r"M237R1_SERVICE_HEALTH_PASS pid=(\d+)", text)
    passed = (
        acceptance.get("status") == "PASS"
        and all(acceptance.get("checks", {}).values())
        and service_match is not None
        and "M237R1_MEASUREMENT_IDENTITY_PASS" in text
        and "M237R1_ACCEPTANCE_PASS" in text
        and "M237R1_BOARD_RUNNER_PASS" in text
    )
    result = {
        "date": "2026-09-01",
        "gate": "M237R1-real-KV260-M237-acceptance-repair-final",
        "status": "PASS" if passed else "FAIL",
        "classification": (
            "Acceptance-only repair over immutable M237 fixed-text real-board evidence; "
            "not a new E2E execution, Web, video, or real-time claim."
        ),
        "delta_manifest_sha256": args.expected_manifest_sha256,
        "acceptance": acceptance,
        "service_pid": int(service_match.group(1)) if service_match else None,
        "service_health_marker": service_match is not None,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Integrate M236 into a hash-locked Web runtime and first measure the "
            "fixed 849-token language Prefill without a full visual window."
        ),
    }
    partial = args.result.with_name(args.result.name + ".partial")
    partial.write_text(json.dumps(result, indent=2) + "\n")
    partial.replace(args.result)
    print(json.dumps(result, indent=2))
    print("M237R1_BOARD_PASS" if passed else "M237R1_BOARD_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
