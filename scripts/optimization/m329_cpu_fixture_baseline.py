#!/usr/bin/env python3
"""M120 fixture CPU arithmetic check; timings are not a PL speedup claim.

The input is the frozen M128 real-record fixture used by the M157/M139 board
gate. This program checks the decoded integer-dot implementation against the
same full-output reference before any same-board CPU/PL timing comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_DIR = ROOT / "deployment/mage_vl4b/m120_text4b_runtime"
from m120_group_reference import group_reference  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cpu_output(case, descriptor_count: int, decode_weights) -> tuple[bytes, dict[str, float]]:
    """Run the full selected descriptor(s), including W2/W4 unpack and GEMM."""
    if not 1 <= descriptor_count <= len(case.descriptors):
        raise ValueError("descriptor_count outside fixture")
    groups = case.groups
    activation = np.frombuffer(case.activation, np.uint8).reshape(groups, 32, 80)
    codes = activation[:, :, :64].copy().view(np.int8).transpose(1, 0, 2)
    scales = activation[:, :, 64:66].copy().view("<f2").reshape(groups, 32).T
    output_words = bytearray()
    decode_seconds = 0.0
    gemm_seconds = 0.0
    for descriptor in case.descriptors[:descriptor_count]:
        shard_outputs = []
        for payload in descriptor.shard_records:
            started = time.perf_counter()
            records = np.frombuffer(payload, np.uint8).reshape(groups, 17, 16)
            weights = np.empty((groups, 8, 64), np.int8)
            weight_scales = np.empty((groups, 8), "<f2")
            for group in range(groups):
                compact = records[group, :descriptor.words]
                decoded, _ = decode_weights(compact, case.bits)
                weights[group] = decoded
                tags = np.frombuffer(compact[0].tobytes(), "<u2", count=8)
                weight_scales[group] = (tags & np.uint16(0x7FFF)).view("<f2")
            decode_seconds += time.perf_counter() - started
            started = time.perf_counter()
            shard_outputs.append(group_reference(codes, scales, weights, weight_scales))
            gemm_seconds += time.perf_counter() - started
        for token in range(32):
            for shard in range(4):
                bits = shard_outputs[shard][token].view("<u2")
                for pair in range(4):
                    word = bytearray(8)
                    word[0:2] = int(bits[2 * pair]).to_bytes(2, "little")
                    word[4:6] = int(bits[2 * pair + 1]).to_bytes(2, "little")
                    output_words.extend(word)
    return bytes(output_words), {
        "decode_ms": decode_seconds * 1000,
        "integer_dot_and_accumulate_ms": gemm_seconds * 1000,
    }


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--case-ordinal", type=int, default=0)
    parser.add_argument("--descriptor-count", type=int, required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.repeat < 1 or args.repeat > 20:
        parser.error("repeat must be within 1..20")
    result = {"gate": "M329-M120-same-fixture-CPU-arithmetic", "status": "FAIL",
              "classification": "CPU numerical preparation; not FPGA or same-board speedup evidence",
              "host_machine": platform.machine(), "case_ordinal": args.case_ordinal,
              "descriptor_count": args.descriptor_count,
              "repeat": args.repeat, "runs": []}
    try:
        sys.path.insert(0, str(args.runtime_dir.resolve()))
        from m120_fixture import _decode_weights, build_case, load_fixture

        fixture_bytes = args.fixture.read_bytes()
        fixture_sha = sha256(fixture_bytes)
        if fixture_sha.lower() != args.fixture_sha256.lower():
            raise RuntimeError("fixture SHA-256 mismatch")
        cases = load_fixture(args.fixture)
        if not 0 <= args.case_ordinal < len(cases):
            raise ValueError("case ordinal outside fixture")
        case = cases[args.case_ordinal]
        built = build_case(case, args.descriptor_count)
        expected = bytes(built["expected"])
        result.update(fixture_sha256=fixture_sha, identity=built["identity"],
                      input_packet_sha256=sha256(built["packet"]),
                      weight_shard_sha256=[sha256(part) for part in built["weights"]],
                      expected_output_sha256=sha256(expected), output_bytes=len(expected))
        for _ in range(args.repeat):
            started = time.perf_counter()
            observed, phases = cpu_output(case, args.descriptor_count, _decode_weights)
            phases["total_ms"] = (time.perf_counter() - started) * 1000
            phases["output_sha256"] = sha256(observed)
            phases["full_output_exact"] = observed == expected
            result["runs"].append(phases)
            if observed != expected:
                raise RuntimeError("full CPU output differs from frozen M128 reference")
        result["status"] = "PASS_CPU_NUMERICAL_ONLY"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    if args.result:
        atomic_json(args.result, result)
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["status"] == "PASS_CPU_NUMERICAL_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
