#!/usr/bin/env python3
"""Counterbalanced native-A53/unchanged stable-PL fixture transactions on KV260.

Only the frozen M128 W2/W4 two-descriptor cases are sampled. This does not
repeat M329's seven-case numerical gate or estimate whole-model speedup.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

FIXTURE_SHA = "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9"
BINARY_SHA = "97730113c0c34c99c9b61aaf5ad70ac57c00a6749c89752ea2b510c338f36354"
CPU_OUTPUT_SHA = {
    0: "c03f51cc7cd6d157e04bd0da674ee59652168b58473d6d3b2070f58fe30ec3a0",
    1: "9dfa69036b7974a37ede922ddf46f4d9e9995f6f682e03e72b27e8867d879bb8",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def canonicalize_fp16_ftz(value: bytes) -> bytes:
    words = np.frombuffer(value, dtype=np.uint8).copy().reshape(-1, 8)
    for offset in (0, 4):
        bits = words[:, offset:offset + 2].copy().view("<u2").reshape(-1)
        subnormal = ((bits & np.uint16(0x7C00)) == 0) & ((bits & np.uint16(0x03FF)) != 0)
        bits[subnormal] &= np.uint16(0x8000)
        words[:, offset:offset + 2] = bits.view(np.uint8).reshape(-1, 2)
    return words.tobytes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cpu-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=10)
    args = parser.parse_args()
    if args.pairs != 10 or args.result.exists():
        parser.error("exactly 10 pairs and a new result path are required")
    if platform.machine() != "aarch64" or os.geteuid() != 0:
        parser.error("requires root on AArch64 KV260")

    sys.path.insert(0, str(args.candidate / "runtime"))
    from m120_board_common import (
        BUILD_ID, DMA_NAME, KERNEL_NAME, REG_AP_CTRL, REG_CONFIG, REG_POINTERS,
        physical_address, snapshot, wait_transaction, write_u64,
    )
    from m120_fixture import build_case, load_fixture

    result = {
        "gate": "M331-KV260-counterbalanced-native-CPU-stable-PL-fixture",
        "status": "FAIL",
        "build_id_expected": f"0x{BUILD_ID:08x}",
        "fixture_sha256_expected": FIXTURE_SHA,
        "native_cpu_binary_sha256_expected": BINARY_SHA,
        "pairs_per_case": args.pairs,
        "order": "CPU-PL for even pair indices, PL-CPU for odd pair indices",
        "boundary": "CPU in-memory packed fixture to complete output; PL in-memory packet/weights through staging, sync, DMA and output copy; neither includes file read, overlay load or CMA allocation",
        "limitation": "Implementation-level same-fixture comparison, not full-model or video acceleration. CPU subprocess startup/fixture parse/output-file write excluded from native timer.",
        "cases": [],
    }
    buffers = []
    kernel = dma = None
    safe_to_free = True
    try:
        from pynq import Overlay, allocate

        fixture = args.candidate / "reference/m128_m120_real_record_csim_fixture.bin"
        fixture_bytes = fixture.read_bytes()
        binary = args.cpu_root / "m330_native_fixture_cpu"
        if sha(fixture_bytes) != FIXTURE_SHA or sha(binary.read_bytes()) != BINARY_SHA:
            raise RuntimeError("frozen fixture/native binary hash mismatch")
        result["fixture_sha256"] = sha(fixture_bytes)
        result["native_cpu_binary_sha256"] = sha(binary.read_bytes())
        cases = load_fixture(fixture)
        prepared = [(cases[i], build_case(cases[i], 2)) for i in (0, 1)]
        started = time.perf_counter()
        overlay = Overlay(str((args.candidate / "overlay/m120_m89x2_t32.bit").resolve()), download=True)
        result["overlay_load_ms_excluded"] = (time.perf_counter() - started) * 1000
        kernel = getattr(overlay, KERNEL_NAME)
        dma = getattr(overlay, DMA_NAME)

        for case, built in prepared:
            ordinal = int(case.ordinal)
            expected_ftz = canonicalize_fp16_ftz(bytes(built["expected"]))
            if sha(bytes(built["expected"])) != CPU_OUTPUT_SHA[ordinal]:
                raise RuntimeError(f"frozen CPU reference mismatch case={ordinal}")
            entry = {
                "ordinal": ordinal, "bits": int(case.bits), "identity": built["identity"],
                "descriptor_count": 2, "input_packet_sha256": sha(built["packet"]),
                "weight_shard_sha256": [sha(part) for part in built["weights"]],
                "expected_cpu_output_sha256": CPU_OUTPUT_SHA[ordinal],
                "expected_pl_output_sha256_ftz": sha(expected_ftz), "pairs": [],
            }
            result["cases"].append(entry)
            started = time.perf_counter()
            weight_buffers = [allocate((len(part),), dtype=np.uint8) for part in built["weights"]]
            input_buffer = allocate((len(built["packet"]),), dtype=np.uint8)
            output_buffer = allocate((int(built["output_bytes"]),), dtype=np.uint8)
            buffers = weight_buffers + [input_buffer, output_buffer]
            entry["allocation_ms_excluded"] = (time.perf_counter() - started) * 1000

            def run_cpu(pair_index: int) -> dict:
                output_path = args.result.parent / f"cpu_case{ordinal}_pair{pair_index:02d}.bin"
                if output_path.exists():
                    raise RuntimeError("refusing to overwrite prior CPU output")
                proc = subprocess.run(
                    ["taskset", "-c", "1", str(binary), str(fixture), str(ordinal),
                     "2", "1", str(output_path), "packed"],
                    capture_output=True, text=True, timeout=20, check=True,
                )
                match = re.search(r"^M330_CPU_RUN case=(\d+) repeat=0 ms=([\d.]+) output_bytes=(\d+)$", proc.stdout, re.M)
                if match is None or int(match.group(1)) != ordinal or int(match.group(3)) != len(bytes(built["expected"])):
                    raise RuntimeError(f"bad native CPU timing output case={ordinal} pair={pair_index}")
                observed = output_path.read_bytes()
                if observed != bytes(built["expected"]):
                    raise RuntimeError(f"CPU complete output mismatch case={ordinal} pair={pair_index}")
                return {"packed_compute_ms": float(match.group(2)), "output_sha256": sha(observed),
                        "full_original_fp16_exact": True}

            def run_pl() -> dict:
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
                wait_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                output_buffer.sync_from_device()
                observed = bytes(memoryview(output_buffer)[:int(built["output_bytes"])])
                output_ms = (time.perf_counter() - started) * 1000
                run = {
                    "weight_stage_and_sync_ms": weight_stage_ms,
                    "input_stage_and_sync_ms": input_stage_ms,
                    "register_setup_ms": register_ms,
                    "dma_launch_and_completion_wait_ms": wait_ms,
                    "output_sync_and_copy_ms": output_ms,
                    "transaction_total_ms": (time.perf_counter() - full_start) * 1000,
                    "output_sha256_ftz": sha(observed),
                    "full_fp16_ftz_output_exact": observed == expected_ftz,
                    "snapshot": evidence,
                }
                if not run["full_fp16_ftz_output_exact"]:
                    raise RuntimeError(f"PL complete FTZ output mismatch case={ordinal}")
                return run

            for pair_index in range(args.pairs):
                pair = {"index": pair_index, "execution_order": "CPU-PL" if pair_index % 2 == 0 else "PL-CPU"}
                if pair_index % 2 == 0:
                    pair["cpu"] = run_cpu(pair_index)
                    pair["pl"] = run_pl()
                else:
                    pair["pl"] = run_pl()
                    pair["cpu"] = run_cpu(pair_index)
                entry["pairs"].append(pair)
                atomic_json(args.result, result)
                print(f"M331_PAIR_PASS case={ordinal} pair={pair_index} order={pair['execution_order']} cpu_ms={pair['cpu']['packed_compute_ms']:.6f} pl_ms={pair['pl']['transaction_total_ms']:.6f}", flush=True)
            for buffer in reversed(buffers):
                buffer.freebuffer()
            buffers = []
        result["status"] = "PASS_PAIRED_FIXTURE_AB"
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        if kernel is not None and dma is not None:
            result["failure_snapshot"] = snapshot(kernel, dma)
            safe_to_free = bool(result["failure_snapshot"].get("mm2s_idle")) and bool(
                result["failure_snapshot"].get("s2mm_idle"))
    finally:
        result["dma_safe_to_release"] = safe_to_free
        if safe_to_free:
            for buffer in reversed(buffers):
                buffer.freebuffer()
        atomic_json(args.result, result)
        print(json.dumps({"gate": result["gate"], "status": result["status"],
                          "cases": [len(c["pairs"]) for c in result["cases"]],
                          "error": result.get("error")}), flush=True)
    return 0 if result["status"] == "PASS_PAIRED_FIXTURE_AB" else 1


if __name__ == "__main__":
    raise SystemExit(main())
