#!/usr/bin/env python3
"""Extract M277 result and require proof that stable M254 was restored."""

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
        r"__M277_BOARD_RESULT_BEGIN__\s*(.*?)\s*__M277_BOARD_RESULT_END__",
        text,
        flags=re.DOTALL,
    )
    if len(envelopes) != 1:
        raise RuntimeError(f"M277 result envelope count {len(envelopes)}")
    result = json.loads(envelopes[0])
    if result.get("gate") != "M277-M276-real-KV260-fixed-window-binary-TTFT":
        raise RuntimeError("M277 gate identity mismatch")
    if result.get("package_manifest_sha256") != args.package_manifest_sha256:
        raise RuntimeError("M277 package hash mismatch")
    restore_codes = [int(value) for value in re.findall(r"__M277_RESTORE_RC_(\d+)__", text)]
    if not restore_codes or restore_codes[-1] != 0:
        raise RuntimeError(f"M277 stable restoration not proved: {restore_codes}")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_name(args.result.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    passed = str(result.get("status", "")).startswith("PASS")
    print(
        f"M277_FORMAL_RESULT_{'PASS' if passed else 'FAIL'} "
        f"first_token_ms={result.get('first_token_ms')} "
        f"total_ms={result.get('total_ms')} restore_rc=0"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

