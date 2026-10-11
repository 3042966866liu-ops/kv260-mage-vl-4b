#!/usr/bin/env python3
"""Extract the M283 result and require exact M254 restoration proof."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    envelopes = re.findall(
        r"__M283_BOARD_RESULT_BEGIN__\s*(.*?)\s*__M283_BOARD_RESULT_END__",
        text,
        flags=re.DOTALL,
    )
    if len(envelopes) != 1:
        raise RuntimeError(f"M283 result envelope count {len(envelopes)}")
    result = json.loads(envelopes[0])
    if result.get("gate") != "M283-BACT-real-KV260-159-160-161-single-observation":
        raise RuntimeError("M283 gate identity mismatch")
    if result.get("package_manifest_sha256") != args.package_manifest_sha256:
        raise RuntimeError("M283 package hash mismatch")
    restore_codes = [int(value) for value in re.findall(r"__M283_RESTORE_RC_(\d+)__", text)]
    if not restore_codes or restore_codes[-1] != 0:
        raise RuntimeError(f"M283 stable restoration not proved: {restore_codes}")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_name(args.result.name + f".partial-{os.getpid()}")
    partial.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(partial, args.result)
    passed = result.get("status") == "PASS_SINGLE_OBSERVATION"
    print(
        f"M283_FORMAL_RESULT_{'PASS' if passed else 'FAIL'} "
        f"calls={result.get('observed_total_logical_fpga_calls')} restore_rc=0"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
