#!/usr/bin/env python3
"""Fail-closed PYNQ runtime for the M120/M89X2 mixed-precision T32 candidate."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "support"))
from contract_runtime import RuntimeContract, merge_outputs, pack_chain_input, parse_chain_output, require_complete


BUILD_ID = 0x4F503131  # M120/M89X21, deadlock-fixed revision
# Host-side compatibility correction for the retained X1 half datapath.  A
# power-of-two factor keeps activation scales and per-group terms out of the
# FP16 subnormal range; parsed results are divided by the exact same factor.
MAX_ACTIVATION_SCALE_SHIFT = 6
MIN_ACTIVATION_SCALE_SHIFT = 0
# Keep the largest active-token activation scale below this value before the
# hardware multiply/accumulate.  This avoids a known Layer-6 MLP-down overflow
# without choosing a lower shift for the small Layer-0/QKV cases.  The returned
# tensor is still checked and retried at successively lower power-of-two shifts,
# so this heuristic is an efficiency hint rather than the safety boundary.
MAX_TRANSMITTED_ACTIVE_SCALE = 512.0
POOL_BASE = 0x808000000
POOL_SIZE = 0x68000000
HIGH_END = POOL_BASE + POOL_SIZE
LOW_END = 0x80000000
REG_AP_CTRL, REG_RETURN = 0x00, 0x10
REG_POINTERS = (0x18, 0x24, 0x30, 0x3C)
# Pinned to 0x80 so the HLS slave and retained KV260 SmartConnect both expose
# an 8-bit AXI-Lite address channel.  This is an ABI-only reservation.
REG_CONFIG = 0x80
DMA_MM2S_DMASR = 0x04
DMA_S2MM_DMASR = 0x34


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(16 << 20), b""):
            h.update(block)
    return h.hexdigest()


def physical_address(buffer) -> int:
    for name in ("device_address", "physical_address"):
        if hasattr(buffer, name):
            return int(getattr(buffer, name))
    raise RuntimeError("buffer exposes no physical address")


def write_u64(kernel, offset: int, value: int) -> None:
    kernel.write(offset, int(value) & 0xFFFFFFFF)
    kernel.write(offset + 4, (int(value) >> 32) & 0xFFFFFFFF)


@dataclass
class VerifiedLayout:
    root: Path
    manifest: dict
    manifest_sha256: str


def verify_layout(root: Path, expected_sha: str, expected_modules: int) -> VerifiedLayout:
    root = Path(root)
    manifest_path = root / "SIXPORT_LAYOUT_MANIFEST.json"
    observed = sha256(manifest_path)
    if observed != expected_sha:
        raise RuntimeError(f"layout manifest hash mismatch {observed} != {expected_sha}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-fourport-group-major-v1":
        raise RuntimeError("unsupported four-port layout format")
    if int(manifest.get("module_count", -1)) != expected_modules:
        raise RuntimeError("layout module count mismatch")
    if len(manifest.get("files", [])) != 4:
        raise RuntimeError("layout must contain exactly four shards")
    for index, item in enumerate(manifest["files"]):
        if item["path"] != f"weights{index}.bin":
            raise RuntimeError("layout shard order mismatch")
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"layout shard identity mismatch: {path}")
    return VerifiedLayout(root, manifest, observed)


def copy_to_buffer(path: Path, buffer) -> None:
    cursor = 0
    with path.open("rb", buffering=0) as f:
        while block := f.read(16 << 20):
            buffer[cursor:cursor + len(block)] = np.frombuffer(block, dtype=np.uint8)
            cursor += len(block)
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    if cursor != path.stat().st_size:
        raise RuntimeError(f"short layout copy: {path}")
    buffer.sync_to_device()


def copy_window_to_buffer(path: Path, offset: int, size: int, buffer) -> None:
    cursor = 0
    with path.open("rb", buffering=0) as f:
        f.seek(offset)
        while cursor < size:
            block = f.read(min(16 << 20, size - cursor))
            if not block:
                raise RuntimeError(f"short staged layout read: {path}")
            buffer[cursor:cursor + len(block)] = np.frombuffer(block, dtype=np.uint8)
            cursor += len(block)
    if cursor != size:
        raise RuntimeError(f"staged layout size mismatch: {path}")
    buffer.sync_to_device()


def chain_window(layout: VerifiedLayout, chain: dict) -> tuple[int, int]:
    """Return an exact common four-shard window as (base_words, bytes)."""
    tiles = {}
    for module in layout.manifest["modules"]:
        for tile in module["tiles"]:
            tiles[(module["module"], int(tile["tile_index"]))] = tile
    low, high = None, 0
    for descriptor in chain["descriptors"]:
        key = (descriptor.get("module", "lm_head"), int(descriptor["tile_index"]))
        if key not in tiles:
            raise RuntimeError(f"descriptor tile missing from layout: {key}")
        tile = tiles[key]
        offsets = [int(value) for value in tile["shard_offsets"]]
        if len(offsets) != 4 or len(set(offsets)) != 1:
            raise RuntimeError(f"staged mode requires equal four-shard offsets: {key}")
        start = offsets[0]
        size = int(tile["record_bytes_per_shard"])
        if start % 16 or size <= 0 or size % 16:
            raise RuntimeError(f"unaligned staged tile: {key}")
        if int(descriptor["offset_words"]) != start // 16:
            raise RuntimeError(f"descriptor/layout offset mismatch: {key}")
        low = start if low is None else min(low, start)
        high = max(high, start + size)
    if low is None or high <= low:
        raise RuntimeError("empty staged chain window")
    return low // 16, high - low


def allocate_layout(layout: VerifiedLayout, allocator, start: int, end: int) -> list:
    buffers = []
    try:
        for item in layout.manifest["files"]:
            size = int(item["bytes"])
            buffer = allocator((size,), dtype=np.uint8)
            address = physical_address(buffer)
            if address < start or address + size > end:
                raise RuntimeError(f"layout buffer outside required window: 0x{address:x}+{size}")
            copy_to_buffer(layout.root / item["path"], buffer)
            buffers.append(buffer)
        return buffers
    except Exception:
        for buffer in reversed(buffers):
            buffer.freebuffer()
        raise


def _channel_flag(channel, name: str) -> bool:
    try:
        return bool(getattr(channel, name))
    except Exception:
        return False


def transaction_snapshot(kernel, dma) -> dict[str, int | bool | str]:
    """Capture fail-closed MMIO evidence without assuming an interrupt path."""
    try:
        ap_ctrl = int(kernel.read(REG_AP_CTRL))
    except Exception as exc:
        ap_ctrl = -1
        kernel_read_error = f"{type(exc).__name__}: {exc}"
    else:
        kernel_read_error = ""
    try:
        returned = int(kernel.read(REG_RETURN))
    except Exception as exc:
        returned = -1
        return_read_error = f"{type(exc).__name__}: {exc}"
    else:
        return_read_error = ""
    try:
        mm2s_dmasr = int(dma.mmio.read(DMA_MM2S_DMASR))
        s2mm_dmasr = int(dma.mmio.read(DMA_S2MM_DMASR))
    except Exception as exc:
        mm2s_dmasr = s2mm_dmasr = -1
        dma_read_error = f"{type(exc).__name__}: {exc}"
    else:
        dma_read_error = ""
    return {
        "ap_ctrl": ap_ctrl,
        "ap_return": returned,
        "mm2s_dmasr": mm2s_dmasr,
        "s2mm_dmasr": s2mm_dmasr,
        "mm2s_idle": _channel_flag(dma.sendchannel, "idle"),
        "mm2s_error": _channel_flag(dma.sendchannel, "error"),
        "s2mm_idle": _channel_flag(dma.recvchannel, "idle"),
        "s2mm_error": _channel_flag(dma.recvchannel, "error"),
        "kernel_read_error": kernel_read_error,
        "return_read_error": return_read_error,
        "dma_read_error": dma_read_error,
    }


def wait_transaction(kernel, dma, timeout_s: float) -> dict[str, int | bool | str]:
    """Observe kernel and both DMA channels together so early kernel errors surface."""
    deadline = time.monotonic() + timeout_s
    kernel_finished = False
    returned = None
    while True:
        # AP_DONE is clear-on-read.  Do not take and discard a snapshot before
        # this loop: a fast minimal transaction can finish before host polling,
        # and that discarded read would erase the only completion edge.
        latest = transaction_snapshot(kernel, dma)
        ap_ctrl = int(latest["ap_ctrl"])
        # AP_DONE is clear-on-read and is the only unambiguous completion edge.
        # AP_IDLE can still be high for a short interval immediately after the
        # AP_START write, so treating IDLE as completion creates a false return.
        if ap_ctrl >= 0 and (ap_ctrl & 0x2):
            kernel_finished = True
            returned = int(latest["ap_return"])
            if returned != BUILD_ID:
                raise RuntimeError(
                    "M120/M89X2 kernel returned before output completion: "
                    f"0x{returned & 0xffffffff:08x}; snapshot={json.dumps(latest, sort_keys=True)}"
                )
        if bool(latest["mm2s_error"]) or bool(latest["s2mm_error"]):
            raise RuntimeError(f"M120/M89X2 DMA error; snapshot={json.dumps(latest, sort_keys=True)}")
        if kernel_finished and bool(latest["mm2s_idle"]) and bool(latest["s2mm_idle"]):
            return latest
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"M120/M89X2 transaction timeout after {timeout_s:.3f}s; "
                f"snapshot={json.dumps(latest, sort_keys=True)}"
            )
        time.sleep(0.0001)


class M120BoardRuntime:
    def __init__(self, overlay_path: Path, language_root: Path, head_root: Path,
                 language_contract_path: Path, head_contract_path: Path,
                 weight_mode: str = "staged-low-cma"):
        from pynq import Overlay, allocate
        from reserved_ddr_pool import ReservedDDRPool

        self.allocate = allocate
        self.language_contract = RuntimeContract.load(
            language_contract_path, "PASS_M120_154_HOMOGENEOUS_LANGUAGE_CHAINS")
        self.head_contract = RuntimeContract.load(
            head_contract_path, "PASS_M120_W4_LMHEAD_8_CHAINS")
        language_sha = self.language_contract.payload["source_manifest_sha256"]
        head_sha = self.head_contract.payload["source_manifest_sha256"]
        self.language_layout = verify_layout(language_root, language_sha, 252)
        self.head_layout = verify_layout(head_root, head_sha, 1)
        if weight_mode not in ("resident-high-ddr", "staged-low-cma"):
            raise ValueError(f"unsupported weight mode: {weight_mode}")
        self.weight_mode = weight_mode
        self.overlay = Overlay(str(Path(overlay_path).resolve()), download=True)
        self.kernel = self.overlay.op01_decode_one_0
        self.dma = self.overlay.axi_dma_prefill
        self.language_buffers = []
        self.head_buffers = []
        self.staged_buffers = []
        self.stage_bytes = 0
        self.stage_ms = 0.0
        self.maximum_weight_window_bytes = 0
        if self.weight_mode == "resident-high-ddr":
            self.high_pool = ReservedDDRPool(POOL_BASE, POOL_SIZE, "/dev/tellme_reserved1664")
            self.language_buffers = allocate_layout(
                self.language_layout, self.high_pool.allocate, POOL_BASE, HIGH_END)
            self.head_buffers = allocate_layout(self.head_layout, allocate, 0, LOW_END)
        else:
            windows = [chain_window(self.language_layout, chain)[1]
                       for chain in self.language_contract.chains]
            windows += [chain_window(self.head_layout, chain)[1]
                        for chain in self.head_contract.chains]
            self.maximum_weight_window_bytes = max(windows)
            self.staged_buffers = [allocate((self.maximum_weight_window_bytes,), dtype=np.uint8)
                                   for _ in range(4)]
            for buffer in self.staged_buffers:
                if physical_address(buffer) + self.maximum_weight_window_bytes > LOW_END:
                    raise RuntimeError("staged weight buffer outside low DDR")
        maximum_input = max(int(c["input_bytes"]) for c in
                            self.language_contract.chains + self.head_contract.chains)
        maximum_output = max(int(c["output_bytes"]) for c in
                             self.language_contract.chains + self.head_contract.chains)
        self.input_buffer = allocate((maximum_input,), dtype=np.uint8)
        self.output_buffer = allocate((maximum_output,), dtype=np.uint8)
        if physical_address(self.input_buffer) + maximum_input > LOW_END:
            raise RuntimeError("input DMA buffer outside low DDR")
        if physical_address(self.output_buffer) + maximum_output > LOW_END:
            raise RuntimeError("output DMA buffer outside low DDR")
        self.host_calls = 0
        self.expected_macros = 0
        self.logical_calls = 0
        self.logical_expected_macros = 0
        self.scale_retry_count = 0
        self.scale_shift_counts = {str(shift): 0 for shift in range(
            MIN_ACTIVATION_SCALE_SHIFT, MAX_ACTIVATION_SCALE_SHIFT + 1)}
        self.scale_attempts = []

    def _stage(self, layout: VerifiedLayout, chain: dict) -> tuple[list, int]:
        base_words, window_bytes = chain_window(layout, chain)
        started = time.monotonic()
        for item, buffer in zip(layout.manifest["files"], self.staged_buffers):
            copy_window_to_buffer(layout.root / item["path"], base_words * 16,
                                  window_bytes, buffer)
        self.stage_bytes += 4 * window_bytes
        self.stage_ms += (time.monotonic() - started) * 1000.0
        return self.staged_buffers, base_words

    @staticmethod
    def _initial_scale_shift(values: np.ndarray) -> int:
        array = np.asarray(values, dtype=np.float32)
        if not np.isfinite(array).all():
            raise FloatingPointError("non-finite family input")
        maximum = float(np.max(np.abs(array))) if array.size else 0.0
        if maximum == 0.0:
            return MAX_ACTIVATION_SCALE_SHIFT
        # Quantization scale is max_abs/127.  Select the largest power-of-two
        # shift whose active-token transmitted scale stays under the headroom
        # target.  Output finiteness below remains the hard guarantee.
        ratio = MAX_TRANSMITTED_ACTIVE_SCALE * 127.0 / maximum
        shift = math.floor(math.log2(ratio)) if ratio > 0.0 else MIN_ACTIVATION_SCALE_SHIFT
        return max(MIN_ACTIVATION_SCALE_SHIFT,
                   min(MAX_ACTIVATION_SCALE_SHIFT, int(shift)))

    @staticmethod
    def _all_outputs_finite(outputs: dict[str, np.ndarray]) -> bool:
        return bool(outputs) and all(np.isfinite(value).all() for value in outputs.values())

    @staticmethod
    def _written_outputs_finite(chain: dict, outputs: dict[str, np.ndarray]) -> bool:
        """Validate only descriptor-owned rows in a sparse chain result.

        Language chains normally cover every row of their output modules, but
        each LM-head chain owns only one vocabulary slice.  parse_chain_output
        deliberately leaves not-yet-owned rows as NaN so merge_outputs can
        detect overlap and require_complete can reject gaps after all slices
        are assembled.  Those structural sentinels are not FPGA output data.
        """
        if not outputs:
            return False
        checked = 0
        for descriptor in chain.get("descriptors", []):
            name = descriptor.get("module", "lm_head")
            if name not in outputs:
                return False
            value = np.asarray(outputs[name])
            start = int(descriptor["row_start"])
            valid = int(descriptor["valid_rows"])
            stop = start + valid
            if value.ndim != 2 or value.shape[0] != 32 or valid <= 0 or value.shape[1] < stop:
                return False
            if not np.isfinite(value[:, start:stop]).all():
                return False
            checked += value.shape[0] * valid
        return checked > 0

    def _execute(self, chain: dict, values: np.ndarray, buffers: list,
                 descriptor_offset_base_words: int = 0) -> dict[str, np.ndarray]:
        output_bytes = int(chain["output_bytes"])
        initial_shift = self._initial_scale_shift(values)
        attempted = []
        for shift in range(initial_shift, MIN_ACTIVATION_SCALE_SHIFT - 1, -1):
            packet = pack_chain_input(chain, values, descriptor_offset_base_words,
                                      activation_scale_shift=shift)
            input_bytes = len(packet)
            self.input_buffer[:input_bytes] = np.frombuffer(packet, dtype=np.uint8)
            self.input_buffer.sync_to_device()
            for register, buffer in zip(REG_POINTERS, buffers):
                write_u64(self.kernel, register, physical_address(buffer))
            self.kernel.write(REG_CONFIG, int(chain["config_u32"], 16))
            self.dma.recvchannel.transfer(self.output_buffer, nbytes=output_bytes)
            self.kernel.write(REG_AP_CTRL, 1)
            self.dma.sendchannel.transfer(self.input_buffer, nbytes=input_bytes)
            snapshot = wait_transaction(self.kernel, self.dma, 10.0)
            returned = int(snapshot["ap_return"])
            if returned != BUILD_ID:
                raise RuntimeError(f"M120/M89X2 build/status mismatch: 0x{returned:08x}")
            self.output_buffer.sync_from_device()
            self.host_calls += 1
            self.expected_macros += int(chain["expected_macros"])
            attempted.append(shift)
            outputs = parse_chain_output(
                chain, memoryview(self.output_buffer)[:output_bytes], output_scale_shift=shift)
            if self._written_outputs_finite(chain, outputs):
                self.logical_calls += 1
                self.logical_expected_macros += int(chain["expected_macros"])
                self.scale_retry_count += len(attempted) - 1
                self.scale_shift_counts[str(shift)] += 1
                self.scale_attempts.append({
                    "chain_index": int(chain["chain_index"]),
                    "layer": int(chain["layer"]) if chain.get("layer") is not None else None,
                    "family": chain.get("family", "lm_head"),
                    "initial_shift": initial_shift,
                    "attempted_shifts": attempted,
                    "selected_shift": shift,
                    "input_max_abs": float(np.max(np.abs(np.asarray(values, dtype=np.float32)))),
                })
                return outputs
        self.scale_retry_count += max(0, len(attempted) - 1)
        self.scale_attempts.append({
            "chain_index": int(chain["chain_index"]),
            "layer": int(chain["layer"]) if chain.get("layer") is not None else None,
            "family": chain.get("family", "lm_head"),
            "initial_shift": initial_shift,
            "attempted_shifts": attempted,
            "selected_shift": None,
            "input_max_abs": float(np.max(np.abs(np.asarray(values, dtype=np.float32)))),
        })
        raise FloatingPointError(
            f"non-finite FPGA output after adaptive shifts {attempted}; "
            f"layer={chain.get('layer')} family={chain.get('family', 'lm_head')}"
        )

    def language_family(self, layer: int, family: str, values: np.ndarray) -> dict[str, np.ndarray]:
        matches = [c for c in self.language_contract.chains
                   if int(c["layer"]) == int(layer) and c["family"] == family]
        if len(matches) != 1:
            raise RuntimeError(f"language chain lookup failed: layer={layer} family={family}")
        chain = matches[0]
        if self.weight_mode == "staged-low-cma":
            buffers, base_words = self._stage(self.language_layout, chain)
            return self._execute(chain, values, buffers, base_words)
        return self._execute(chain, values, self.language_buffers)

    def lm_head(self, values: np.ndarray) -> np.ndarray:
        assembled: dict[str, np.ndarray] = {}
        for chain in self.head_contract.chains:
            if self.weight_mode == "staged-low-cma":
                buffers, base_words = self._stage(self.head_layout, chain)
                update = self._execute(chain, values, buffers, base_words)
            else:
                update = self._execute(chain, values, self.head_buffers)
            merge_outputs(assembled, update)
        width = int(self.head_layout.manifest["modules"][0]["shape"][0])
        require_complete(assembled, {"lm_head": width})
        return assembled["lm_head"]

    def evidence(self) -> dict:
        result = {"build_id": f"0x{BUILD_ID:08x}", "host_calls": self.host_calls,
                  "expected_macros": self.expected_macros,
                  "logical_calls": self.logical_calls,
                  "logical_expected_macros": self.logical_expected_macros,
                  "weight_mode": self.weight_mode, "stage_bytes": self.stage_bytes,
                  "stage_ms": self.stage_ms,
                  "activation_scale_policy": "adaptive-power-of-two-finite-retry-v1",
                  "maximum_activation_scale_shift": MAX_ACTIVATION_SCALE_SHIFT,
                  "minimum_activation_scale_shift": MIN_ACTIVATION_SCALE_SHIFT,
                  "maximum_transmitted_active_scale": MAX_TRANSMITTED_ACTIVE_SCALE,
                  "scale_retry_count": self.scale_retry_count,
                  "scale_shift_counts": self.scale_shift_counts,
                  "scale_attempts": self.scale_attempts,
                  "maximum_weight_window_bytes_per_shard": self.maximum_weight_window_bytes}
        if hasattr(self, "high_pool"):
            result["language_high_pool"] = self.high_pool.summary()
        return result

    def close(self) -> None:
        for buffer in (getattr(self, "output_buffer", None), getattr(self, "input_buffer", None)):
            if buffer is not None:
                buffer.freebuffer()
        for buffer in reversed(getattr(self, "head_buffers", [])):
            buffer.freebuffer()
        for buffer in reversed(getattr(self, "language_buffers", [])):
            buffer.freebuffer()
        for buffer in reversed(getattr(self, "staged_buffers", [])):
            buffer.freebuffer()
        if hasattr(self, "high_pool"):
            self.high_pool.close()
