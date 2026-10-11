#!/usr/bin/env python3
"""Extract and validate the M271 board result without hiding a failed gate."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    envelopes = re.findall(
        r"__M271_BOARD_RESULT_BEGIN__\s*(.*?)\s*__M271_BOARD_RESULT_END__",
        text,
        flags=re.DOTALL,
    )
    if len(envelopes) != 1:
        raise RuntimeError(f"M271 result envelope count {len(envelopes)}")
    result = json.loads(envelopes[0])
    if result.get("gate") != "M271-M269-real-KV260-fixed-window-binary-TTFT":
        raise RuntimeError("M271 gate identity mismatch")
    if result.get("package_manifest_sha256") != args.package_manifest_sha256:
        raise RuntimeError("M271 result package hash mismatch")
    if result.get("status") not in {
        "PASS_FUNCTIONAL_FASTER_THAN_M244",
        "FAIL_FUNCTIONAL_OR_SPEED",
    }:
        raise RuntimeError("M271 result status invalid")
    restore_codes = [int(value) for value in re.findall(r"__M271_RESTORE_RC_(\d+)__", text)]
    if not restore_codes or restore_codes[-1] != 0:
        raise RuntimeError(f"M271 stable M254 restoration not proved: {restore_codes}")
    atomic_json(args.result, result)
    passed = result["status"].startswith("PASS")
    print(
        "M271_FORMAL_RESULT_" + ("PASS" if passed else "FAIL")
        + f" status={result['status']} first_token_ms={result.get('first_token_ms')}"
        + f" total_ms={result.get('total_ms')} restore_rc=0"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
