#!/usr/bin/env python3
"""Collect one passing M184 video-package import from a COM3 log."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


BEGIN = "__M184_VIDEO_IMPORT_RESULT_BEGIN__"
END = "__M184_VIDEO_IMPORT_RESULT_END__"
EXPECTED_PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
EXPECTED_M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"
EXPECTED_DESTINATION = "/home/ubuntu/tellme_m120_m89x2_20260901/m181_m120_video_board_candidate"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(re.escape(BEGIN) + r"\s*(\{.*?\})\s*" + re.escape(END), text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"expected one M184 result envelope, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("gate") != "M184-M181-video-direct-Ethernet-board-import":
        raise RuntimeError("M184 result gate mismatch")
    if result.get("status") != "PASS":
        raise RuntimeError(f"M184 import is not PASS: {result.get('error')}")
    if result.get("package_manifest_sha256") != EXPECTED_PACKAGE_SHA or result.get("m182_result_sha256") != EXPECTED_M182_SHA:
        raise RuntimeError("M184 package/predecessor evidence mismatch")
    if result.get("destination") != EXPECTED_DESTINATION or int(result.get("file_count", -1)) != 50:
        raise RuntimeError("M184 destination/closure evidence mismatch")
    if result.get("boot_dtb_cma_partitions_services_changed") is not False or result.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M184 stable-state evidence mismatch")
    result["uart_log"] = args.log.as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    result["evidence_level"] = "hash-verified video-candidate transfer only; not PS-vision, FPGA video E2E, performance or Web"
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print("M184_VIDEO_IMPORT_COLLECT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
