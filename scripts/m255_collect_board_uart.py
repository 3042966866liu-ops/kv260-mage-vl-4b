#!/usr/bin/env python3
"""Collect one hash-bound M255 board-result envelope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--new-manifest-sha256", required=True)
    parser.add_argument("--app-js-sha256", required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    begin, end = "__M255_BOARD_RESULT_BEGIN__", "__M255_BOARD_RESULT_END__"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError("M255 result envelope is missing or ambiguous")
    payload = text.split(begin, 1)[1].split(end, 1)[0].strip()
    result = json.loads(payload)
    passed = (
        result.get("status") == "PASS"
        and result.get("new_manifest_sha256") == args.new_manifest_sha256
        and result.get("served_app_js_sha256") == args.app_js_sha256
        and result.get("fast_runtime_load_count_before") == 1
        and result.get("fast_runtime_load_count_after") == 1
        and result.get("candidate_service_restarted") is False
        and "M255_ACTIVE_SESSION_WEB_FIX_BOARD_PASS" in text
        and "M255_SESSION_ATTACH_HOTFIX_RUNNER_PASS" in text
        and "__M255_RUNNER_RC_0__" in text
    )
    result["collector_status"] = "PASS" if passed else "FAIL"
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M255_BOARD_COLLECT_PASS" if passed else "M255_BOARD_COLLECT_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
