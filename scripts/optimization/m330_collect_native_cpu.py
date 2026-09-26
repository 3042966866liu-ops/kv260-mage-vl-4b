#!/usr/bin/env python3
"""Collect the M330 CPU-only COM3 evidence without inventing PL pairs."""
import argparse
import hashlib
import json
import os
import re
import statistics
from pathlib import Path

EXPECTED = {
    0: "c03f51cc7cd6d157e04bd0da674ee59652168b58473d6d3b2070f58fe30ec3a0",
    1: "9dfa69036b7974a37ede922ddf46f4d9e9995f6f682e03e72b27e8867d879bb8",
}
FIXTURE = "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board-log", type=Path, required=True)
    parser.add_argument("--detail-log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        raise RuntimeError("refusing to overwrite M330 result")
    board = args.board_log.read_text(encoding="utf-8", errors="replace")
    detail = args.detail_log.read_text(encoding="utf-8", errors="replace")
    if "M330_NATIVE_A53_NUMERICAL_PASS" not in board or "__M75C_UART_RC_0__" not in board:
        raise RuntimeError("board runner completion/exit marker missing")
    payloads = []
    for line in board.splitlines():
        if line.startswith("{") and '"gate": "M330-native-CPU-frozen-M128-fixture"' in line:
            payloads.append(json.loads(line))
    if len(payloads) != 4:
        raise RuntimeError(f"expected four native result payloads, got {len(payloads)}")
    setup_pattern = re.compile(r"^M330_CPU_SETUP case=(\d+) mode=(packed|predecoded) ms=([\d.]+) predecoded_bytes=(\d+)$", re.M)
    setups = {(int(i), mode): (float(ms), int(size)) for i, mode, ms, size in setup_pattern.findall(detail)}
    if len(setups) != 4:
        raise RuntimeError(f"expected four setup records, got {len(setups)}")
    expected_order = [(0, "packed"), (1, "packed"), (0, "predecoded"), (1, "predecoded")]
    summaries = []
    for payload, (ordinal, mode) in zip(payloads, expected_order):
        if (payload["case_ordinal"], payload["status"], payload["fixture_sha256"],
                payload["output_sha256"], payload["full_output_exact"], payload["repeats"]) != (
                ordinal, "PASS", FIXTURE, EXPECTED[ordinal], True, 10):
            raise RuntimeError(f"M330 identity or numerical mismatch: {ordinal} {mode}")
        times = payload["run_ms"]
        if len(times) != 10 or any(x <= 0 for x in times):
            raise RuntimeError("invalid native timing sample")
        setup_ms, predecoded_bytes = setups[(ordinal, mode)]
        summaries.append({
            "ordinal": ordinal, "bits": 2 if ordinal == 0 else 4,
            "mode": mode, "descriptors": 2, "setup_ms_excluded": setup_ms,
            "predecoded_bytes": predecoded_bytes, "run_ms": times,
            "median_ms": statistics.median(times), "range_ms": [min(times), max(times)],
            "full_original_fp16_exact": True, "output_sha256": payload["output_sha256"],
        })
    result = {
        "gate": "M330-KV260-native-A53-CPU-only-frozen-fixture",
        "status": "PASS_NATIVE_CPU_ONLY",
        "board": "KV260 Cortex-A53; one thread pinned to core 1",
        "compiler": "g++ 11.4.0; -O3 -std=c++17 -ffp-contract=off -fno-fast-math -march=armv8-a+simd",
        "fixture_sha256": FIXTURE,
        "reused_existing_evidence": "M329 seven CPU numerical cases and two PL cases; no PL rerun in M330",
        "new_evidence_scope": "two representative W2/W4 native CPU cases, 10 repeats each, packed and predecoded",
        "not_proved": "fair paired CPU/PL speedup, full-model acceleration, video E2E benefit",
        "summaries": summaries,
        "uart_log_sha256": {"board": sha(args.board_log), "detail": sha(args.detail_log)},
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps({"status": result["status"], "medians": [(s["ordinal"], s["mode"], s["median_ms"]) for s in summaries]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
