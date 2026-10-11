#!/usr/bin/env python3
"""Collect authoritative M204 continuous-video UART evidence."""

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--log", type=Path, required=True); parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(); text = args.log.read_text(encoding="utf-8", errors="replace")
    begin, end = "__M204_CONTINUOUS_VIDEO_RESULT_BEGIN__", "__M204_CONTINUOUS_VIDEO_RESULT_END__"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise RuntimeError("M204 UART envelope cardinality mismatch")
    value = json.loads(text.split(begin, 1)[1].split(end, 1)[0].strip())
    if value.get("gate") != "M204-bounded-continuous-video-two-window-reuse":
        raise RuntimeError("M204 result identity mismatch")
    if value.get("status") == "PASS":
        if (value.get("processed_window_count") != 2 or value.get("runtime_load_count") != 1 or
                value.get("runtime_identity_reused") is not True or value.get("total_pl_logical_chain_calls") != 8332 or
                value.get("expected_total_pl_logical_chain_calls") != 8332 or
                "M204_CONTINUOUS_VIDEO_RUNNER_PASS" not in text or "__M204_CONTINUOUS_RUNNER_RC_0__" not in text):
            raise RuntimeError("M204 PASS proof mismatch")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print("M204_CONTINUOUS_UART_COLLECT_PASS" if value.get("status") == "PASS" else "M204_CONTINUOUS_UART_COLLECT_FAIL")
    return 0 if value.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
