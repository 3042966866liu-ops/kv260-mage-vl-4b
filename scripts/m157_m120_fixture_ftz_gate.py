#!/usr/bin/env python3
"""Exact M120 descriptor/chain board gate under the frozen FP16 FTZ contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonicalize(value: bytes) -> tuple[bytes, int]:
    words = np.frombuffer(value, dtype=np.uint8).copy().reshape(-1, 8)
    count = 0
    for start in (0, 4):
        bits = words[:, start:start + 2].copy().view("<u2").reshape(-1)
        subnormal = ((bits & np.uint16(0x7C00)) == 0) & ((bits & np.uint16(0x03FF)) != 0)
        count += int(np.count_nonzero(subnormal))
        bits[subnormal] &= np.uint16(0x8000)
        words[:, start:start + 2] = bits.view(np.uint8).reshape(-1, 2)
    return words.tobytes(), count


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--level", choices=("single-descriptor", "single-chain"), required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    buffers = []
    sys.path.insert(0, str(args.candidate / "runtime"))
    from m120_board_common import (
        BUILD_ID, DMA_NAME, KERNEL_NAME, REG_AP_CTRL, REG_CONFIG, REG_POINTERS,
        physical_address, wait_transaction, write_u64,
    )
    from m120_fixture import build_case, load_fixture

    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": f"M157-M120-{args.level}-FP16-FTZ",
        "status": "FAIL",
        "classification": "Exact real-board packed-weight gate under a predeclared FP16 subnormal-to-signed-zero output contract.",
    }
    try:
        from pynq import Overlay, allocate

        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        if policy.get("status") != "PASS_POLICY_FROZEN_BEFORE_ACCEPTANCE_RERUN":
            raise RuntimeError("M157 FTZ policy is not frozen")
        contract = policy["contracts"][args.level]
        descriptor_count = int(contract["descriptor_count"])
        fixture = args.candidate / "reference/m128_m120_real_record_csim_fixture.bin"
        built = build_case(load_fixture(fixture)[0], descriptor_count)
        original = bytes(built["expected"])
        expected, subnormal_count = canonicalize(original)
        if sha256_bytes(original) != contract["original_sha256"]:
            raise RuntimeError("original golden identity mismatch")
        if sha256_bytes(expected) != contract["canonical_sha256"] or subnormal_count != int(contract["canonicalized_subnormal_count"]):
            raise RuntimeError("canonical FTZ golden identity mismatch")

        overlay = Overlay(str((args.candidate / "overlay/m120_m89x2_t32.bit").resolve()), download=True)
        kernel = getattr(overlay, KERNEL_NAME)
        dma = getattr(overlay, DMA_NAME)
        weight_buffers = [allocate((len(value),), dtype=np.uint8) for value in built["weights"]]
        input_buffer = allocate((len(built["packet"]),), dtype=np.uint8)
        output_buffer = allocate((int(built["output_bytes"]),), dtype=np.uint8)
        buffers.extend(weight_buffers + [input_buffer, output_buffer])
        for source, buffer in zip(built["weights"], weight_buffers):
            buffer[:] = np.frombuffer(source, dtype=np.uint8)
            buffer.sync_to_device()
        input_buffer[:] = np.frombuffer(built["packet"], dtype=np.uint8)
        input_buffer.sync_to_device()
        for register, buffer in zip(REG_POINTERS, weight_buffers):
            write_u64(kernel, register, physical_address(buffer))
        kernel.write(REG_CONFIG, int(built["config"]))
        dma.recvchannel.transfer(output_buffer, nbytes=int(built["output_bytes"]))
        kernel.write(REG_AP_CTRL, 1)
        dma.sendchannel.transfer(input_buffer, nbytes=len(built["packet"]))
        evidence = wait_transaction(
            kernel, dma, 10.0, str(built["identity"]), len(built["packet"]), int(built["output_bytes"])
        )
        output_buffer.sync_from_device()
        observed = bytes(memoryview(output_buffer)[: int(built["output_bytes"])])
        if observed != expected:
            mismatch = next((index for index, pair in enumerate(zip(observed, expected)) if pair[0] != pair[1]), -1)
            raise RuntimeError(
                f"FTZ canonical output mismatch first_byte={mismatch} observed_sha256={sha256_bytes(observed)} expected_sha256={sha256_bytes(expected)}"
            )
        result.update(
            {
                "status": "PASS",
                "identity": built["identity"],
                "build_id": f"0x{BUILD_ID:08x}",
                "descriptor_count": descriptor_count,
                "input_bytes": len(built["packet"]),
                "output_bytes": int(built["output_bytes"]),
                "original_output_sha256": sha256_bytes(original),
                "canonical_output_sha256": sha256_bytes(expected),
                "observed_output_sha256": sha256_bytes(observed),
                "canonicalized_subnormal_count": subnormal_count,
                "tolerance_used": False,
                "full_canonical_output_bit_exact": True,
                "fpga_transaction_executed": True,
                "snapshot": evidence,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run corrected single-chain only." if args.level == "single-descriptor" else "M140 corrected chain PASS may unlock M150/M154 transfer preparation.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = f"Remain at {args.level}; do not advance."
    finally:
        for buffer in reversed(buffers):
            buffer.freebuffer()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result, result)
        print(json.dumps(result, indent=2), flush=True)
    marker = args.level.upper().replace("-", "_")
    print(f"M157_M120_{marker}_FTZ_GATE_" + ("PASS" if result["status"] == "PASS" else "FAIL"))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
