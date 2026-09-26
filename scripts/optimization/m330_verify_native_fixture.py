#!/usr/bin/env python3
"""Fail-closed complete-output comparison for the native M128 CPU baseline."""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_result(path: Path, result: dict) -> None:
    temp = path.with_name(path.name + ".partial-" + str(os.getpid()))
    temp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--case", type=int, required=True)
    p.add_argument("--descriptors", type=int, required=True)
    p.add_argument("--repeats", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--native-log", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    args = p.parse_args()
    if args.result.exists():
        raise RuntimeError("refusing to overwrite existing result")
    result = {
        "gate": "M330-native-CPU-frozen-M128-fixture",
        "status": "FAIL",
        "case_ordinal": args.case,
        "descriptors": args.descriptors,
        "repeats": args.repeats,
        "scope": "same quantized fixture only; not whole-model or video speedup",
    }
    try:
        result.update(verify(args))
        result["status"] = "PASS"
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    atomic_result(args.result, result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["status"] == "PASS" else 1


def verify(args: argparse.Namespace) -> dict:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.runtime))
    from m120_fixture import build_case, load_fixture

    fixture_bytes = args.fixture.read_bytes()
    if digest(fixture_bytes) != "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9":
        raise RuntimeError("frozen fixture SHA-256 mismatch")
    cases = load_fixture(args.fixture)
    if not 0 <= args.case < len(cases):
        raise RuntimeError("case ordinal outside fixture")
    built = build_case(cases[args.case], args.descriptors)
    expected, observed = bytes(built["expected"]), args.output.read_bytes()
    log = args.native_log.read_text(encoding="utf-8")
    pattern = re.compile(r"^M330_CPU_RUN case=(\d+) repeat=(\d+) ms=([0-9.]+) output_bytes=(\d+)$", re.M)
    runs = [m.groups() for m in pattern.finditer(log)]
    if len(runs) != args.repeats or "M330_CPU_COMPLETE case=" + str(args.case) not in log:
        raise RuntimeError("native run count/completion mismatch")
    if observed != expected:
        mismatch = next((i for i, (a, b) in enumerate(zip(observed, expected)) if a != b), None)
        raise RuntimeError(f"full original FP16 output mismatch at byte {mismatch}; observed={digest(observed)} expected={digest(expected)}")
    parsed = []
    for index, (case, repeat, ms, size) in enumerate(runs):
        if (int(case), int(repeat), int(size)) != (args.case, index, len(expected)):
            raise RuntimeError("native run identity mismatch")
        parsed.append(float(ms))
    return {
        "fixture_sha256": digest(fixture_bytes), "case_ordinal": args.case,
        "descriptors": args.descriptors, "repeats": args.repeats,
        "run_ms": parsed, "output_sha256": digest(observed), "output_bytes": len(observed),
        "full_output_exact": True, "comparison": "original FP16 bytes (not PL FTZ)",
    }


if __name__ == "__main__":
    raise SystemExit(main())
