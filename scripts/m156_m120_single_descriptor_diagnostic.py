#!/usr/bin/env python3
"""Measure the exact real-board M120 single-descriptor numerical difference."""

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


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def decode_output(value: bytes) -> tuple[np.ndarray, np.ndarray]:
    words = np.frombuffer(value, dtype=np.uint8).reshape(-1, 8)
    padding = words[:, [2, 3, 6, 7]].copy()
    first = words[:, 0:2].copy().view("<u2").reshape(-1)
    second = words[:, 4:6].copy().view("<u2").reshape(-1)
    bits = np.empty((words.shape[0] * 2,), dtype="<u2")
    bits[0::2] = first
    bits[1::2] = second
    return bits, padding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    buffers = []
    runtime = args.candidate / "runtime"
    sys.path.insert(0, str(runtime))
    from m120_board_common import (
        BUILD_ID, DMA_NAME, KERNEL_NAME, REG_AP_CTRL, REG_CONFIG, REG_POINTERS,
        physical_address, wait_transaction, write_u64,
    )
    from m120_fixture import build_case, load_fixture

    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M156-M120-single-descriptor-difference-diagnostic",
        "status": "FAIL",
        "classification": "Same M139 real-board single-descriptor measurement without an inferred acceptance threshold; not chain, layer or E2E evidence.",
    }
    try:
        from pynq import Overlay, allocate

        fixture = args.candidate / "reference/m128_m120_real_record_csim_fixture.bin"
        built = build_case(load_fixture(fixture)[0], 1)
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
        expected = bytes(built["expected"])
        observed_bits, observed_padding = decode_output(observed)
        expected_bits, expected_padding = decode_output(expected)
        observed_values = observed_bits.view("<f2").astype(np.float32)
        expected_values = expected_bits.view("<f2").astype(np.float32)
        delta = observed_values.astype(np.float64) - expected_values.astype(np.float64)
        finite = bool(np.isfinite(observed_values).all() and np.isfinite(expected_values).all())
        differing_bytes = np.flatnonzero(np.frombuffer(observed, dtype=np.uint8) != np.frombuffer(expected, dtype=np.uint8))
        differing_values = np.flatnonzero(observed_bits != expected_bits)
        details = []
        for index in differing_values[:32]:
            word, half = divmod(int(index), 2)
            token, within_token = divmod(word, 16)
            shard, pair = divmod(within_token, 4)
            details.append(
                {
                    "value_index": int(index),
                    "token": token,
                    "shard": shard,
                    "lane": pair * 2 + half,
                    "expected_fp16_bits": int(expected_bits[index]),
                    "observed_fp16_bits": int(observed_bits[index]),
                    "expected": float(expected_values[index]),
                    "observed": float(observed_values[index]),
                    "abs_error": float(abs(delta[index])),
                }
            )
        expected_norm = float(np.linalg.norm(expected_values.astype(np.float64)))
        observed_norm = float(np.linalg.norm(observed_values.astype(np.float64)))
        per_token = []
        for token in range(32):
            start, stop = token * 32, (token + 1) * 32
            local = delta[start:stop]
            per_token.append(
                {
                    "token": token,
                    "fp16_exact_count": int(np.count_nonzero(observed_bits[start:stop] == expected_bits[start:stop])),
                    "max_abs": float(np.max(np.abs(local))),
                    "rmse": float(np.sqrt(np.mean(np.square(local)))),
                }
            )
        result.update(
            {
                "status": "MEASURED",
                "identity": built["identity"],
                "build_id": f"0x{BUILD_ID:08x}",
                "descriptor_count": 1,
                "input_bytes": len(built["packet"]),
                "output_bytes": int(built["output_bytes"]),
                "observed_sha256": sha256_bytes(observed),
                "expected_sha256": sha256_bytes(expected),
                "fpga_transaction_executed": True,
                "snapshot": evidence,
                "metrics": {
                    "finite": finite,
                    "element_count": int(observed_bits.size),
                    "fp16_exact_count": int(np.count_nonzero(observed_bits == expected_bits)),
                    "fp16_exact_fraction": float(np.mean(observed_bits == expected_bits)),
                    "differing_value_count": int(differing_values.size),
                    "differing_byte_count": int(differing_bytes.size),
                    "first_differing_byte": int(differing_bytes[0]) if differing_bytes.size else -1,
                    "max_abs": float(np.max(np.abs(delta))),
                    "mean_abs": float(np.mean(np.abs(delta))),
                    "rmse": float(np.sqrt(np.mean(np.square(delta)))),
                    "relative_l2": float(np.linalg.norm(delta) / max(expected_norm, 1.0e-30)),
                    "cosine": float(np.vdot(observed_values.astype(np.float64), expected_values.astype(np.float64)) / max(observed_norm * expected_norm, 1.0e-30)),
                    "observed_padding_nonzero": int(np.count_nonzero(observed_padding)),
                    "expected_padding_nonzero": int(np.count_nonzero(expected_padding)),
                },
                "first_differences": details,
                "per_token": per_token,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "acceptance_note": "Measurement only. Do not infer or relax a threshold from this result.",
                "next_gate": "Classify the exact numerical pattern, predeclare an acceptance or repair rule, then rerun single-descriptor only.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M156 at single-descriptor only."
    finally:
        for buffer in reversed(buffers):
            buffer.freebuffer()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result, result)
        print(json.dumps(result, indent=2), flush=True)
    print("M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_MEASURED" if result["status"] == "MEASURED" else "M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_FAIL")
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
