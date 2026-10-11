#!/usr/bin/env python3
"""Stable M120 KV260 fixture timing, separate from overlay load and allocation.

The same frozen M128 fixture is used by the M329 CPU numerical diagnostic.
This measures this PL host implementation, not a model-wide acceleration.
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


FIXTURE_SHA256 = "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonicalize_fp16_ftz(value: bytes) -> bytes:
    words = np.frombuffer(value, dtype=np.uint8).copy().reshape(-1, 8)
    for start in (0, 4):
        bits = words[:, start:start + 2].copy().view("<u2").reshape(-1)
        subnormal = ((bits & np.uint16(0x7C00)) == 0) & ((bits & np.uint16(0x03FF)) != 0)
        bits[subnormal] &= np.uint16(0x8000)
        words[:, start:start + 2] = bits.view(np.uint8).reshape(-1, 2)
    return words.tobytes()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1 or args.repeat > 10:
        parser.error("repeat must be within 1..10")
    if args.result.exists():
        parser.error("result already exists")

    sys.path.insert(0, str(args.candidate / "runtime"))
    from m120_board_common import (
        BUILD_ID, DMA_NAME, KERNEL_NAME, REG_AP_CTRL, REG_CONFIG, REG_POINTERS,
        physical_address, snapshot, wait_transaction, write_u64,
    )
    from m120_fixture import build_case, load_fixture

    result = {
        "gate": "M329-M120-stable-PL-same-fixture-timing",
        "status": "FAIL",
        "classification": "Stable KV260 PL fixture timing only; no full-model speedup claim",
        "host_machine": platform.machine(),
        "build_id_expected": f"0x{BUILD_ID:08x}",
        "fixture_sha256_expected": FIXTURE_SHA256,
        "repeat": args.repeat,
        "cases": [],
    }
    buffers = []
    dma = kernel = None
    safe_to_free = True
    try:
        from pynq import Overlay, allocate

        fixture = args.candidate / "reference/m128_m120_real_record_csim_fixture.bin"
        fixture_bytes = fixture.read_bytes()
        if sha256(fixture_bytes) != FIXTURE_SHA256:
            raise RuntimeError("fixture SHA-256 mismatch")
        cases = load_fixture(fixture)
        built_cases = [(cases[ordinal], build_case(cases[ordinal], 2)) for ordinal in (0, 1)]
        result["fixture_sha256"] = sha256(fixture_bytes)
        started = time.perf_counter()
        overlay = Overlay(str((args.candidate / "overlay/m120_m89x2_t32.bit").resolve()), download=True)
        result["overlay_load_ms"] = (time.perf_counter() - started) * 1000
        kernel = getattr(overlay, KERNEL_NAME)
        dma = getattr(overlay, DMA_NAME)

        for case, built in built_cases:
            expected = canonicalize_fp16_ftz(bytes(built["expected"]))
            entry = {
                "ordinal": case.ordinal,
                "bits": case.bits,
                "identity": built["identity"],
                "input_packet_sha256": sha256(built["packet"]),
                "weight_shard_sha256": [sha256(part) for part in built["weights"]],
                "expected_output_sha256_ftz": sha256(expected),
                "input_bytes": len(built["packet"]),
                "output_bytes": int(built["output_bytes"]),
                "runs": [],
            }
            result["cases"].append(entry)
            allocation_start = time.perf_counter()
            weight_buffers = [allocate((len(part),), dtype=np.uint8) for part in built["weights"]]
            input_buffer = allocate((len(built["packet"]),), dtype=np.uint8)
            output_buffer = allocate((int(built["output_bytes"]),), dtype=np.uint8)
            buffers = weight_buffers + [input_buffer, output_buffer]
            entry["allocation_ms_excluded"] = (time.perf_counter() - allocation_start) * 1000
            for _ in range(args.repeat):
                full_start = time.perf_counter()
                started = time.perf_counter()
                for part, buffer in zip(built["weights"], weight_buffers):
                    buffer[:] = np.frombuffer(part, dtype=np.uint8)
                    buffer.sync_to_device()
                weight_stage_ms = (time.perf_counter() - started) * 1000

                started = time.perf_counter()
                input_buffer[:] = np.frombuffer(built["packet"], dtype=np.uint8)
                input_buffer.sync_to_device()
                input_stage_ms = (time.perf_counter() - started) * 1000

                started = time.perf_counter()
                for register, buffer in zip(REG_POINTERS, weight_buffers):
                    write_u64(kernel, register, physical_address(buffer))
                kernel.write(REG_CONFIG, int(built["config"]))
                register_ms = (time.perf_counter() - started) * 1000

                started = time.perf_counter()
                dma.recvchannel.transfer(output_buffer, nbytes=int(built["output_bytes"]))
                kernel.write(REG_AP_CTRL, 1)
                dma.sendchannel.transfer(input_buffer, nbytes=len(built["packet"]))
                evidence = wait_transaction(kernel, dma, 10.0, str(built["identity"]),
                                            len(built["packet"]), int(built["output_bytes"]))
                device_wait_ms = (time.perf_counter() - started) * 1000

                started = time.perf_counter()
                output_buffer.sync_from_device()
                observed = bytes(memoryview(output_buffer)[:int(built["output_bytes"])])
                output_sync_ms = (time.perf_counter() - started) * 1000
                run = {
                    "weight_stage_and_sync_ms": weight_stage_ms,
                    "input_stage_and_sync_ms": input_stage_ms,
                    "register_setup_ms": register_ms,
                    "dma_launch_and_completion_wait_ms": device_wait_ms,
                    "output_sync_and_copy_ms": output_sync_ms,
                    "total_ms": (time.perf_counter() - full_start) * 1000,
                    "observed_output_sha256": sha256(observed),
                    "full_output_ftz_exact": observed == expected,
                    "snapshot": evidence,
                }
                entry["runs"].append(run)
                atomic_json(args.result, result)
                if observed != expected:
                    raise RuntimeError(f"FTZ output mismatch identity={built['identity']}")
            for buffer in reversed(buffers):
                buffer.freebuffer()
            buffers = []
        result["status"] = "PASS_STABLE_PL_FIXTURE_TIMING"
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        if dma is not None and kernel is not None:
            result["failure_snapshot"] = snapshot(kernel, dma)
            safe_to_free = bool(result["failure_snapshot"].get("mm2s_idle")) and bool(
                result["failure_snapshot"].get("s2mm_idle"))
    finally:
        result["dma_safe_to_release"] = safe_to_free
        if safe_to_free:
            for buffer in reversed(buffers):
                buffer.freebuffer()
        atomic_json(args.result, result)
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["status"] == "PASS_STABLE_PL_FIXTURE_TIMING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
