#!/usr/bin/env python3
"""Minimal one-descriptor hardware isolation for the M89-X shell."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    runtime_dir = args.candidate / "runtime"
    sys.path.insert(0, str(runtime_dir))
    from board_runtime import (BUILD_ID, REG_AP_CTRL, REG_CONFIG, REG_POINTERS,
                               physical_address, wait_transaction, write_u64)
    from contract_runtime import pack_chain_input, parse_chain_output
    from pynq import Overlay, allocate

    started = time.monotonic()
    buffers = []
    result = {"gate": "M89-X-minimal-1g-8r-1d", "status": "FAIL"}
    try:
        overlay = Overlay(str((args.candidate / "overlay/m89x_t32.bit").resolve()), download=True)
        kernel = overlay.mage_m89x_t32_0
        dma = overlay.axi_dma_prefill
        chain = {
            "groups": 1,
            "bits": 2,
            "descriptor_count": 1,
            "config_u32": "0x00010201",
            "input_bytes": (1 + 32 * 5) * 16,
            "output_bytes": 32 * 4 * 4 * 8,
            "descriptors": [{
                "encoded_u64": "0x0000080800000000",
                "module": "minimal",
                "row_start": 0,
                "rows_per_shard": 8,
                "valid_rows": 32,
                "output_bytes": 32 * 4 * 4 * 8,
            }],
        }
        values = np.zeros((32, 64), dtype=np.float32)
        packet = pack_chain_input(chain, values)
        weights = [allocate((9 * 16,), dtype=np.uint8) for _ in range(4)]
        buffers.extend(weights)
        input_buffer = allocate((len(packet),), dtype=np.uint8)
        output_buffer = allocate((chain["output_bytes"],), dtype=np.uint8)
        buffers.extend((input_buffer, output_buffer))
        for buffer in weights:
            buffer[:] = 0
            buffer.sync_to_device()
        input_buffer[:] = np.frombuffer(packet, dtype=np.uint8)
        input_buffer.sync_to_device()
        addresses = [physical_address(buffer) for buffer in weights]
        for register, address in zip(REG_POINTERS, addresses):
            write_u64(kernel, register, address)
        kernel.write(REG_CONFIG, int(chain["config_u32"], 16))
        dma.recvchannel.transfer(output_buffer, nbytes=chain["output_bytes"])
        kernel.write(REG_AP_CTRL, 1)
        dma.sendchannel.transfer(input_buffer, nbytes=len(packet))
        snapshot = wait_transaction(kernel, dma, 5.0)
        output_buffer.sync_from_device()
        output = parse_chain_output(chain, memoryview(output_buffer))
        values_out = output["minimal"]
        if snapshot["ap_return"] != BUILD_ID:
            raise RuntimeError(f"minimal Build ID mismatch: {snapshot}")
        if values_out.shape != (32, 32) or not np.isfinite(values_out).all():
            raise RuntimeError("minimal output shape/finite gate failed")
        if np.count_nonzero(values_out) != 0:
            raise RuntimeError("zero-input minimal output is not zero")
        result = {
            "gate": "M89-X-minimal-1g-8r-1d",
            "status": "PASS",
            "build_id": f"0x{BUILD_ID:08x}",
            "weight_addresses": [f"0x{value:x}" for value in addresses],
            "input_address": f"0x{physical_address(input_buffer):x}",
            "output_address": f"0x{physical_address(output_buffer):x}",
            "snapshot": snapshot,
            "total_ms": (time.monotonic() - started) * 1000.0,
        }
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["total_ms"] = (time.monotonic() - started) * 1000.0
    finally:
        for buffer in reversed(buffers):
            buffer.freebuffer()
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    print("M89X_MINIMAL_KERNEL_SMOKE_PASS" if result["status"] == "PASS"
          else "M89X_MINIMAL_KERNEL_SMOKE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
