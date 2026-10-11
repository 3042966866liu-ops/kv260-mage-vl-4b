#!/usr/bin/env python3
"""Shared fail-closed MMIO/DMA helpers for the M120/M89X2 board gates."""

from __future__ import annotations

import json
import time


BUILD_ID = 0x4D395832
KERNEL_NAME = "mage_m120_m89x2_0"
DMA_NAME = "axi_dma_prefill"
REG_AP_CTRL, REG_RETURN = 0x00, 0x10
REG_POINTERS = (0x18, 0x24, 0x30, 0x3C)
REG_CONFIG = 0x80
DMA_MM2S_DMASR = 0x04
DMA_S2MM_DMASR = 0x34


def physical_address(buffer) -> int:
    for name in ("device_address", "physical_address"):
        if hasattr(buffer, name):
            return int(getattr(buffer, name))
    raise RuntimeError("buffer exposes no physical address")


def write_u64(kernel, offset: int, value: int) -> None:
    kernel.write(offset, int(value) & 0xFFFFFFFF)
    kernel.write(offset + 4, (int(value) >> 32) & 0xFFFFFFFF)


def _flag(channel, name: str) -> bool:
    try:
        return bool(getattr(channel, name))
    except Exception:
        return False


def snapshot(kernel, dma) -> dict[str, int | bool | str]:
    result: dict[str, int | bool | str] = {}
    try:
        result["ap_ctrl"] = int(kernel.read(REG_AP_CTRL))
        result["kernel_read_error"] = ""
    except Exception as exc:
        result["ap_ctrl"] = -1
        result["kernel_read_error"] = f"{type(exc).__name__}: {exc}"
    try:
        result["ap_return"] = int(kernel.read(REG_RETURN))
        result["return_read_error"] = ""
    except Exception as exc:
        result["ap_return"] = -1
        result["return_read_error"] = f"{type(exc).__name__}: {exc}"
    try:
        result["mm2s_dmasr"] = int(dma.mmio.read(DMA_MM2S_DMASR))
        result["s2mm_dmasr"] = int(dma.mmio.read(DMA_S2MM_DMASR))
        result["dma_read_error"] = ""
    except Exception as exc:
        result["mm2s_dmasr"] = -1
        result["s2mm_dmasr"] = -1
        result["dma_read_error"] = f"{type(exc).__name__}: {exc}"
    result.update(
        {
            "mm2s_idle": _flag(dma.sendchannel, "idle"),
            "mm2s_error": _flag(dma.sendchannel, "error"),
            "s2mm_idle": _flag(dma.recvchannel, "idle"),
            "s2mm_error": _flag(dma.recvchannel, "error"),
        }
    )
    return result


def wait_transaction(kernel, dma, timeout_s: float, identity: str,
                     input_bytes: int, output_bytes: int) -> dict[str, int | bool | str]:
    deadline = time.monotonic() + timeout_s
    kernel_finished = False
    latest: dict[str, int | bool | str] = {}
    while True:
        latest = snapshot(kernel, dma)
        ap_ctrl = int(latest["ap_ctrl"])
        if ap_ctrl >= 0 and (ap_ctrl & 0x2):
            kernel_finished = True
            returned = int(latest["ap_return"])
            if returned != BUILD_ID:
                raise RuntimeError(
                    f"kernel return mismatch identity={identity} input_bytes={input_bytes} "
                    f"output_bytes={output_bytes} snapshot={json.dumps(latest, sort_keys=True)}"
                )
        if bool(latest["mm2s_error"]) or bool(latest["s2mm_error"]):
            raise RuntimeError(
                f"DMA error identity={identity} input_bytes={input_bytes} "
                f"output_bytes={output_bytes} snapshot={json.dumps(latest, sort_keys=True)}"
            )
        if kernel_finished and bool(latest["mm2s_idle"]) and bool(latest["s2mm_idle"]):
            return latest
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"transaction timeout identity={identity} input_bytes={input_bytes} "
                f"output_bytes={output_bytes} snapshot={json.dumps(latest, sort_keys=True)}"
            )
        time.sleep(0.0001)

