#!/usr/bin/env python3
"""Collect one M186 PS-vision board result from COM3."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


BEGIN = "__M186_PS_VISION_RESULT_BEGIN__"
END = "__M186_PS_VISION_RESULT_END__"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M184_SHA = "790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    text = args.log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(re.escape(BEGIN) + r"\s*(\{.*?\})\s*" + re.escape(END), text, flags=re.S)
    if len(matches) != 1:
        raise RuntimeError(f"expected one M186 result envelope, observed={len(matches)}")
    result = json.loads(matches[0])
    if result.get("gate") != "M186-M181-fixed-four-frame-PS-vision-board-numerical":
        raise RuntimeError("M186 gate mismatch")
    if result.get("package_manifest_sha256") != PACKAGE_SHA or result.get("m184_formal_result_sha256") != M184_SHA:
        raise RuntimeError("M186 package/predecessor mismatch")
    if result.get("boot_dtb_cma_partitions_services_changed") is not False or result.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M186 stable-state evidence mismatch")
    if result.get("status") not in {"PASS", "FAIL"}:
        raise RuntimeError("M186 invalid status")
    result["uart_log"] = args.log.as_posix()
    result["uart_log_sha256"] = hashlib.sha256(args.log.read_bytes()).hexdigest()
    result["evidence_level"] = "real-KV260 fixed-four-frame PS vision only; not FPGA language/video E2E or Web"
    temporary = args.result.with_name(args.result.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps(result, indent=2))
    print(f"M186_PS_VISION_COLLECT_{result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
