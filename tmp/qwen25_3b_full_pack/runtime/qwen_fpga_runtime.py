#!/usr/bin/env python3
"""Qwen decoder runtime with every Transformer Linear on KV260 PL."""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import numpy as np

from prefill_packet import (
    ACTIVATION_RECORD_BYTES as PREFILL_ACTIVATION_BYTES,
    WEIGHT_BYTES as PREFILL_WEIGHT_BYTES,
    quantize_activation_records,
)

try:
    from prefill_native import (
        quantize_activation_records as _native_quantize_activation_records,
        silu_mul as _native_silu_mul,
    )

    PREFILL_ELEMENTWISE_MODE = "a53-openmp4-fused-silu-mul-v1"
    PREFILL_ACTIVATION_MODE = "a53-openmp4-w4a8-records-v1"
except ImportError:
    _native_silu_mul = None
    _native_quantize_activation_records = None
    PREFILL_ELEMENTWISE_MODE = "numpy-fused-silu-mul-fallback"
    PREFILL_ACTIVATION_MODE = "numpy-w4a8-records-fallback"


WEIGHT_BYTES = 288
ACTIVATION_BYTES = 128
RESULT_BYTES = 32
# The shared kernel is the Decode path as well as the Prefill path.  Keep the
# host validation ceiling aligned with the HLS interface so 7B's 296-group
# down projection remains tileable; allocation still follows the loaded model.
HARDWARE_MAX_INPUT_GROUPS = 512
HARDWARE_MAX_OUTPUT_BLOCKS = 2046
HARDWARE_MAX_MACROS = 524288
# The Vivado AXI DMA is configured with c_sg_length_width=26.  Keep every
# simple-mode transfer below that register's representable byte count; wider
# future models are split along the output dimension instead of depending on
# one model-specific CMA/DMA packet size.
HARDWARE_MAX_DMA_BYTES = (1 << 26) - 1
BUILD_ID = 0x51317342
PREFILL_BUILD_ID = 0x51317342
PREFILL_MAX_TOKENS = 64
PREFILL_MAX_INPUT_GROUPS = 512
PREFILL_MAX_OUTPUT_BLOCKS = 560
RUNTIME_OPTIMIZATION = (
    "async-weight-prefetch-v1+triple-output-block-v1+banked-bram-v1+"
    "output-tiling-v1+fpga-lm-head-w4g64-v1+fp16-rescore256-v1+"
    "sequence-batched-prefill-w4a8-s64-l40-wbmu+shared-single-token-w4a8-v1+"
    "prefill-double-cma-v1+lm-head-double-cma-v1+packed-dot-meta-dataflow-v1"
)
LM_HEAD_SHORTLIST = 256


def _model_index_path(root: Path) -> Path:
    matches = sorted((Path(root) / "model").glob("*_mixed_gs_index.json"))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one Mixed-GS model index, found {len(matches)}"
        )
    return matches[0]


class MixedGSEngine:
    def __init__(self, root: Path, download: bool = True, stage: str = "prefill"):
        from pynq import Overlay, allocate

        self.root = Path(root)
        if stage not in ("prefill", "decode", "shared"):
            raise ValueError("stage must be prefill, decode, or shared")
        self.stage = "shared"
        self.index = json.loads(_model_index_path(self.root).read_text())
        self.linears = {item["name"]: item for item in self.index["linears"]}
        linear_name = Path(self.index["linear_file"]["path"]).name
        self.weights = np.memmap(self.root / "model" / linear_name, dtype=np.uint8, mode="r")
        lm_head_indexes = sorted((self.root / "lm_head").glob("*_lm_head_w4g64.json"))
        if len(lm_head_indexes) > 1:
            raise RuntimeError(f"expected at most one LM-head index, found {len(lm_head_indexes)}")
        self.lm_head_info = (
            json.loads(lm_head_indexes[0].read_text()) if lm_head_indexes else None
        )
        self.lm_head_weights = None
        if self.lm_head_info is not None:
            weight_name = lm_head_indexes[0].with_suffix(".mgs").name
            weight_path = lm_head_indexes[0].parent / weight_name
            if weight_path.stat().st_size != int(self.lm_head_info["bytes"]):
                raise RuntimeError("LM-head packed weight size does not match metadata")
            self.lm_head_weights = np.memmap(weight_path, dtype=np.uint8, mode="r")
        overlay_name = "qwen25_shared_l40.xsa"
        self.overlay = Overlay(str(self.root / "overlay" / overlay_name), download=download)
        self.dma = None
        self.kernel = None
        self.prefill_dma = self.overlay.axi_dma_prefill
        self.prefill_kernel = self.overlay.qwen25_prefill_w4a8_0
        model_max_groups = max(int(x["input_groups"]) for x in self.linears.values())
        if model_max_groups > HARDWARE_MAX_INPUT_GROUPS:
            raise ValueError(
                f"model requires {model_max_groups} input groups; "
                f"hardware supports {HARDWARE_MAX_INPUT_GROUPS}"
            )
        self.max_macros = HARDWARE_MAX_MACROS
        model_max_output_blocks = min(
            HARDWARE_MAX_OUTPUT_BLOCKS,
            max(int(x["output_blocks"]) for x in self.linears.values()),
        )
        lm_head_tile_blocks = 0
        lm_head_tx_bytes = 0
        if self.lm_head_info is not None:
            lm_groups = int(self.lm_head_info["input_groups"])
            lm_head_tile_blocks = min(
                int(self.lm_head_info["output_blocks"]),
                self._tile_block_limit(lm_groups),
            )
            lm_head_tx_bytes = lm_groups * (
                ACTIVATION_BYTES + lm_head_tile_blocks * WEIGHT_BYTES
            )
        self.max_output_blocks = max(model_max_output_blocks, lm_head_tile_blocks)
        model_max_tx_bytes = max(
            int(x["input_groups"]) *
            (
                ACTIVATION_BYTES
                + min(
                    int(x["output_blocks"]),
                    self._tile_block_limit(int(x["input_groups"])),
                )
                * WEIGHT_BYTES
            )
            for x in self.linears.values()
        )
        self.max_tx_bytes = max(model_max_tx_bytes, lm_head_tx_bytes)
        # Two independent CMA buffers let the CPU assemble the next static
        # weight packet while PL/DMA consumes the current packet.
        self.tx_buffers = []
        # A dedicated LM-head CMA tile preserves the next-token weight prefetch
        # already occupying one of the two Transformer packet buffers.
        self.lm_head_tx = None
        self.rx = (
            allocate(shape=(self.max_output_blocks * 8,), dtype=np.float32)
            if stage == "decode"
            else None
        )
        max_prefill_tx_bytes = max(
            int(item["input_groups"])
            * (
                PREFILL_MAX_TOKENS * PREFILL_ACTIVATION_BYTES
                + min(int(item["output_blocks"]), PREFILL_MAX_OUTPUT_BLOCKS)
                * PREFILL_WEIGHT_BYTES
            )
            for item in self.linears.values()
        )
        if self.lm_head_info is not None:
            lm_groups = int(self.lm_head_info["input_groups"])
            lm_blocks = min(
                int(self.lm_head_info["output_blocks"]),
                self._prefill_tile_block_limit(lm_groups, 1),
            )
            max_prefill_tx_bytes = max(
                max_prefill_tx_bytes,
                lm_groups
                * (PREFILL_ACTIVATION_BYTES + lm_blocks * PREFILL_WEIGHT_BYTES),
            )
        # Ping-pong CMA packets allow the A53 to assemble tile N+1 while the
        # DMA and PL consume tile N.  Memory stays bounded by two maximum
        # tiles, independent of layer/model size.
        self.prefill_tx_buffers = [
            allocate(shape=(max_prefill_tx_bytes,), dtype=np.uint8)
            for _ in range(2)
        ]
        # Keep the legacy alias for the LM-head path, which is deliberately
        # left unchanged in this first incremental optimization.
        self.prefill_tx = self.prefill_tx_buffers[0]
        self.prefill_rx = allocate(
            shape=(PREFILL_MAX_TOKENS * PREFILL_MAX_OUTPUT_BLOCKS * 8,),
            dtype=np.float32,
        )
        self._prefetch_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="qwen-weight-prefetch"
        )
        self._prefetch_future: Future | None = None
        self._prefetch_key: tuple[str, ...] | None = None
        self.reset_profile()

    def reset_profile(self):
        self.profile = {
            "linear_calls": 0,
            "qkv_batch_calls": 0,
            "tiled_linear_calls": 0,
            "tiled_kernel_calls": 0,
            "lm_head_kernel_calls": 0,
            "lm_head_packet_ms": 0.0,
            "lm_head_packet_exposed_ms": 0.0,
            "lm_head_packet_overlap_tiles": 0,
            "linear_total_ms": 0.0,
            "packet_prepare_ms": 0.0,
            "activation_prepare_ms": 0.0,
            "weight_prefetch_copy_ms": 0.0,
            "weight_prefetch_wait_ms": 0.0,
            "weight_prefetch_launches": 0,
            "weight_prefetch_hits": 0,
            "weight_prefetch_misses": 0,
            "contiguous_ms": 0.0,
            "tx_copy_ms": 0.0,
            "sync_to_device_ms": 0.0,
            "kernel_setup_ms": 0.0,
            "dma_wait_ms": 0.0,
            "sync_from_device_ms": 0.0,
            "result_copy_ms": 0.0,
            "reduce_ms": 0.0,
            "stream_input_bytes": 0,
            "stream_output_bytes": 0,
            "prefill_linear_calls": 0,
            "prefill_kernel_calls": 0,
            "prefill_activation_quant_ms": 0.0,
            "prefill_packet_prepare_ms": 0.0,
            "prefill_packet_exposed_ms": 0.0,
            "prefill_packet_overlap_launches": 0,
            "prefill_sync_to_device_ms": 0.0,
            "prefill_kernel_setup_ms": 0.0,
            "prefill_dma_wait_ms": 0.0,
            "prefill_sync_from_device_ms": 0.0,
            "prefill_result_copy_ms": 0.0,
            "prefill_stream_input_bytes": 0,
            "prefill_stream_output_bytes": 0,
        }

    def profile_snapshot(self) -> dict[str, int | float]:
        return dict(self.profile)

    def close(self):
        self.finish_prefetch()
        self._prefetch_executor.shutdown(wait=True)
        for tx in self.tx_buffers:
            tx.freebuffer()
        if self.lm_head_tx is not None:
            self.lm_head_tx.freebuffer()
        if self.rx is not None:
            self.rx.freebuffer()
        for tx in self.prefill_tx_buffers:
            tx.freebuffer()
        if self.prefill_rx is not None:
            self.prefill_rx.freebuffer()

    def counters(self) -> tuple[int, int]:
        return self.prefill_counters()

    def prefill_counters(self) -> tuple[int, int]:
        if self.prefill_kernel is None:
            raise RuntimeError("Prefill counters requested while Decode overlay is active")
        return int(self.prefill_kernel.read(0x48)), int(self.prefill_kernel.read(0x58))

    @staticmethod
    def _prefill_tile_block_limit(input_groups: int, token_count: int) -> int:
        groups = int(input_groups)
        tokens = int(token_count)
        if groups < 1 or groups > PREFILL_MAX_INPUT_GROUPS:
            raise ValueError(f"Prefill input group count {groups} is outside hardware range")
        if tokens < 1 or tokens > PREFILL_MAX_TOKENS:
            raise ValueError(f"Prefill token count {tokens} is outside hardware range")
        dma_blocks = (
            HARDWARE_MAX_DMA_BYTES // groups
            - tokens * PREFILL_ACTIVATION_BYTES
        ) // PREFILL_WEIGHT_BYTES
        return min(PREFILL_MAX_OUTPUT_BLOCKS, dma_blocks)

    @staticmethod
    def _normalise_key(names: str | tuple[str, ...]) -> tuple[str, ...]:
        return (names,) if isinstance(names, str) else tuple(names)

    @staticmethod
    def _tile_block_limit(input_groups: int) -> int:
        groups = int(input_groups)
        if groups < 1 or groups > HARDWARE_MAX_INPUT_GROUPS:
            raise ValueError(f"input group count {groups} is outside hardware range")
        dma_blocks = (
            HARDWARE_MAX_DMA_BYTES // groups - ACTIVATION_BYTES
        ) // WEIGHT_BYTES
        return min(
            HARDWARE_MAX_OUTPUT_BLOCKS,
            HARDWARE_MAX_MACROS // groups,
            dma_blocks,
        )

    def _prefetch_supported(self, names: str | tuple[str, ...]) -> bool:
        key = self._normalise_key(names)
        items = [self.linears[name] for name in key]
        groups = int(items[0]["input_groups"])
        return (
            all(int(item["input_groups"]) == groups for item in items)
            and sum(int(item["output_blocks"]) for item in items)
            <= self._tile_block_limit(groups)
        )

    def _prepare_weight_packet(self, key: tuple[str, ...], buffer_index: int):
        """Populate only the static weight regions of one CMA packet."""
        started = time.perf_counter()
        items = [self.linears[name] for name in key]
        groups = int(items[0]["input_groups"])
        if any(int(item["input_groups"]) != groups for item in items):
            raise ValueError("batched linears must have identical input group counts")
        total_blocks = sum(int(item["output_blocks"]) for item in items)
        if total_blocks > self._tile_block_limit(groups):
            raise ValueError(
                f"{total_blocks} output blocks exceed one hardware tile for {groups} groups"
            )
        if groups * total_blocks > self.max_macros:
            raise ValueError(
                f"macro count {groups * total_blocks} exceeds allocated range"
            )
        stride = ACTIVATION_BYTES + total_blocks * WEIGHT_BYTES
        tx_bytes = groups * stride
        if tx_bytes > self.max_tx_bytes:
            raise ValueError(f"stream size {tx_bytes} exceeds allocated range")
        stream = self.tx_buffers[buffer_index][:tx_bytes].reshape(groups, stride)
        layouts = []
        block_cursor = 0
        for item in items:
            blocks = int(item["output_blocks"])
            start = int(item["offset"])
            stop = start + int(item["bytes"])
            byte_start = ACTIVATION_BYTES + block_cursor * WEIGHT_BYTES
            byte_stop = byte_start + blocks * WEIGHT_BYTES
            stream[:, byte_start:byte_stop] = self.weights[start:stop].reshape(groups, -1)
            layouts.append((block_cursor, block_cursor + blocks))
            block_cursor += blocks
        copy_ms = (time.perf_counter() - started) * 1000.0
        return key, buffer_index, groups, total_blocks, tuple(layouts), tx_bytes, copy_ms

    def _collect_prefetch(self, count_wait: bool = True):
        if self._prefetch_future is None:
            return None
        started = time.perf_counter()
        packet = self._prefetch_future.result()
        wait_ms = (time.perf_counter() - started) * 1000.0
        self.profile["weight_prefetch_copy_ms"] += float(packet[-1])
        if count_wait:
            self.profile["weight_prefetch_wait_ms"] += wait_ms
        self._prefetch_future = None
        self._prefetch_key = None
        return packet

    def finish_prefetch(self) -> None:
        """Drain an outstanding worker before reset, close, or raw-stream use."""
        self._collect_prefetch(count_wait=True)

    def _acquire_weight_packet(self, names: str | tuple[str, ...]):
        key = self._normalise_key(names)
        if self._prefetch_future is not None and self._prefetch_key == key:
            packet = self._collect_prefetch(count_wait=True)
            self.profile["weight_prefetch_hits"] += 1
            return packet
        if self._prefetch_future is not None:
            self._collect_prefetch(count_wait=True)
        packet = self._prepare_weight_packet(key, 0)
        self.profile["weight_prefetch_copy_ms"] += float(packet[-1])
        self.profile["weight_prefetch_misses"] += 1
        return packet

    def _launch_prefetch(
        self, names: str | tuple[str, ...] | None, current_buffer_index: int
    ) -> None:
        if names is None:
            return
        if not self._prefetch_supported(names):
            return
        if self._prefetch_future is not None:
            raise RuntimeError("weight prefetch launched before previous packet was consumed")
        key = self._normalise_key(names)
        next_buffer_index = 1 - int(current_buffer_index)
        self._prefetch_key = key
        self._prefetch_future = self._prefetch_executor.submit(
            self._prepare_weight_packet, key, next_buffer_index
        )
        self.profile["weight_prefetch_launches"] += 1

    def _run_tx_buffer(
        self, tx: np.ndarray, tx_bytes: int, groups: int, blocks: int
    ) -> np.ndarray:
        groups = int(groups)
        blocks = int(blocks)
        count = groups * blocks
        if groups < 1 or groups > HARDWARE_MAX_INPUT_GROUPS:
            raise ValueError(f"input group count {groups} is outside hardware range")
        if blocks < 1 or blocks > self._tile_block_limit(groups):
            raise ValueError(f"output block count {blocks} is outside one hardware tile")
        if count < 1 or count > self.max_macros:
            raise ValueError(f"macro count {count} is outside allocated range")
        if tx_bytes > self.max_tx_bytes:
            raise ValueError(f"stream size {tx_bytes} exceeds allocated range")
        rx_bytes = blocks * RESULT_BYTES
        started = time.perf_counter()
        tx.sync_to_device()
        self.profile["sync_to_device_ms"] += (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        self.kernel.write(0x10, groups)
        self.kernel.write(0x18, blocks)
        self.dma.recvchannel.transfer(self.rx, nbytes=rx_bytes)
        self.kernel.write(0x00, 1)
        self.dma.sendchannel.transfer(tx, nbytes=tx_bytes)
        self.profile["kernel_setup_ms"] += (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        self.dma.sendchannel.wait()
        self.dma.recvchannel.wait()
        self.profile["dma_wait_ms"] += (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        self.rx.sync_from_device()
        self.profile["sync_from_device_ms"] += (time.perf_counter() - started) * 1000.0
        status = int(self.kernel.read(0x20))
        if status != 0:
            raise RuntimeError(f"Mixed-GS kernel status={status}")
        observed_build_id = int(self.kernel.read(0x30))
        if observed_build_id != BUILD_ID:
            raise RuntimeError(f"PL build ID mismatch: 0x{observed_build_id:08x}")
        started = time.perf_counter()
        result = np.array(self.rx[: blocks * 8], dtype=np.float32, copy=True).reshape(blocks, 8)
        self.profile["result_copy_ms"] += (time.perf_counter() - started) * 1000.0
        self.profile["stream_input_bytes"] += tx_bytes
        self.profile["stream_output_bytes"] += rx_bytes
        return result

    def run_linear_stream(
        self, stream: np.ndarray, input_groups: int, output_blocks: int
    ) -> np.ndarray:
        self.finish_prefetch()
        started = time.perf_counter()
        stream = np.ascontiguousarray(stream, dtype=np.uint8).reshape(-1)
        self.profile["contiguous_ms"] += (time.perf_counter() - started) * 1000.0
        groups = int(input_groups)
        blocks = int(output_blocks)
        tx_bytes = groups * (ACTIVATION_BYTES + blocks * WEIGHT_BYTES)
        if stream.size != tx_bytes:
            raise ValueError(f"expected {tx_bytes} stream bytes, got {stream.size}")
        tx = self.tx_buffers[0]
        started = time.perf_counter()
        tx[:tx_bytes] = stream
        self.profile["tx_copy_ms"] += (time.perf_counter() - started) * 1000.0
        return self._run_tx_buffer(tx, tx_bytes, groups, blocks)

    def _prepare_lm_head_packet(
        self,
        buffer_index: int,
        records: np.ndarray,
        matrix: np.ndarray,
        groups: int,
        block_start: int,
        block_stop: int,
    ) -> tuple[int, int, int, int, float]:
        """Assemble one vocabulary tile in a selected shared CMA buffer."""
        started = time.perf_counter()
        tile_blocks = block_stop - block_start
        stride = PREFILL_ACTIVATION_BYTES + tile_blocks * PREFILL_WEIGHT_BYTES
        tx_bytes = groups * stride
        tx = self.prefill_tx_buffers[buffer_index]
        if tx_bytes > tx.size:
            raise ValueError("LM-head stream size exceeds CMA allocation")
        stream = tx[:tx_bytes].reshape(groups, stride)
        stream[:, :PREFILL_ACTIVATION_BYTES] = records.reshape(
            groups, PREFILL_ACTIVATION_BYTES
        )
        stream[:, PREFILL_ACTIVATION_BYTES:] = matrix[
            :, block_start:block_stop, :
        ].reshape(groups, tile_blocks * PREFILL_WEIGHT_BYTES)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return buffer_index, tile_blocks, tx_bytes, block_start, elapsed_ms

    def linear_lm_head(self, activation: np.ndarray) -> np.ndarray:
        """Run the output-tiled LM head through the shared token_count=1 kernel."""
        if self.lm_head_info is None or self.lm_head_weights is None:
            raise RuntimeError("packed FPGA LM-head weights are not installed")
        groups = int(self.lm_head_info["input_groups"])
        blocks = int(self.lm_head_info["output_blocks"])
        tile_limit = self._prefill_tile_block_limit(groups, 1)
        matrix = self.lm_head_weights.reshape(groups, blocks, PREFILL_WEIGHT_BYTES)
        x = np.asarray(activation, dtype=np.float32).reshape(1, groups * 64)
        activation_started = time.perf_counter()
        if _native_quantize_activation_records is not None:
            records = _native_quantize_activation_records(x)
        else:
            records, _, _ = quantize_activation_records(x)
        self.profile["prefill_activation_quant_ms"] += (
            time.perf_counter() - activation_started
        ) * 1000.0
        outputs = []
        tiles = [
            (block_start, min(block_start + tile_limit, blocks))
            for block_start in range(0, blocks, tile_limit)
        ]
        first_start, first_stop = tiles[0]
        exposed_started = time.perf_counter()
        current_packet = self._prepare_lm_head_packet(
            0, records, matrix, groups, first_start, first_stop
        )
        exposed_ms = (time.perf_counter() - exposed_started) * 1000.0
        self.profile["lm_head_packet_exposed_ms"] += exposed_ms
        self.profile["prefill_packet_exposed_ms"] += exposed_ms
        self.profile["lm_head_packet_ms"] += current_packet[-1]
        self.profile["prefill_packet_prepare_ms"] += current_packet[-1]
        next_packet = None

        for tile_index, (block_start, block_stop) in enumerate(tiles):
            if tile_index > 0:
                if next_packet is None:
                    raise RuntimeError("LM-head packet pipeline lost the next tile")
                current_packet = next_packet
                next_packet = None
            buffer_index, tile_blocks, tx_bytes, prepared_start, packet_ms = (
                current_packet
            )
            if prepared_start != block_start:
                raise RuntimeError("LM-head packet pipeline returned the wrong tile")
            rx_values = tile_blocks * 8
            rx_bytes = rx_values * np.dtype(np.float32).itemsize
            tx = self.prefill_tx_buffers[buffer_index]

            started = time.perf_counter()
            tx.sync_to_device()
            self.profile["prefill_sync_to_device_ms"] += (
                time.perf_counter() - started
            ) * 1000.0
            started = time.perf_counter()
            self.prefill_kernel.write(0x10, 1)
            self.prefill_kernel.write(0x18, groups)
            self.prefill_kernel.write(0x20, tile_blocks)
            self.prefill_dma.recvchannel.transfer(self.prefill_rx, nbytes=rx_bytes)
            self.prefill_kernel.write(0x00, 1)
            self.prefill_dma.sendchannel.transfer(tx, nbytes=tx_bytes)
            self.profile["prefill_kernel_setup_ms"] += (
                time.perf_counter() - started
            ) * 1000.0

            if tile_index + 1 < len(tiles):
                next_start, next_stop = tiles[tile_index + 1]
                next_packet = self._prepare_lm_head_packet(
                    1 - buffer_index,
                    records,
                    matrix,
                    groups,
                    next_start,
                    next_stop,
                )
                self.profile["lm_head_packet_ms"] += next_packet[-1]
                self.profile["prefill_packet_prepare_ms"] += next_packet[-1]
                self.profile["lm_head_packet_overlap_tiles"] += 1
            started = time.perf_counter()
            self.prefill_dma.sendchannel.wait()
            self.prefill_dma.recvchannel.wait()
            self.profile["prefill_dma_wait_ms"] += (
                time.perf_counter() - started
            ) * 1000.0
            self.prefill_rx.sync_from_device()
            status = int(self.prefill_kernel.read(0x28))
            if status != 0:
                raise RuntimeError(f"Shared LM-head kernel status={status}")
            observed_build_id = int(self.prefill_kernel.read(0x38))
            if observed_build_id != PREFILL_BUILD_ID:
                raise RuntimeError(
                    f"Shared LM-head build ID mismatch: 0x{observed_build_id:08x}"
                )
            outputs.append(
                np.array(self.prefill_rx[:rx_values], dtype=np.float32, copy=True)
            )
            self.profile["lm_head_kernel_calls"] += 1
            self.profile["prefill_kernel_calls"] += 1
            self.profile["prefill_stream_input_bytes"] += tx_bytes
            self.profile["prefill_stream_output_bytes"] += rx_bytes
        return np.concatenate(outputs)[: int(self.lm_head_info["vocab_size"])]

    def _linear_tiled(
        self,
        name: str,
        activation: np.ndarray,
        next_names: str | tuple[str, ...] | None,
        linear_started: float,
    ) -> np.ndarray:
        """Run an oversized Linear as output-dimension tiles on the same PL kernel."""
        self.finish_prefetch()
        item = self.linears[name]
        groups = int(item["input_groups"])
        blocks = int(item["output_blocks"])
        tile_limit = self._tile_block_limit(groups)
        weight_start = int(item["offset"])
        weight_stop = weight_start + int(item["bytes"])
        matrix = self.weights[weight_start:weight_stop].reshape(
            groups, blocks, WEIGHT_BYTES
        )
        x = np.asarray(activation, dtype=np.float32).reshape(groups, 64)
        activation_started = time.perf_counter()
        x_bytes = np.ascontiguousarray(x.astype("<f2")).view(np.uint8).reshape(
            groups, ACTIVATION_BYTES
        )
        self.profile["activation_prepare_ms"] += (
            time.perf_counter() - activation_started
        ) * 1000.0
        outputs = []
        last_buffer_index = 0
        for tile_index, block_start in enumerate(range(0, blocks, tile_limit)):
            block_stop = min(block_start + tile_limit, blocks)
            tile_blocks = block_stop - block_start
            stride = ACTIVATION_BYTES + tile_blocks * WEIGHT_BYTES
            tx_bytes = groups * stride
            last_buffer_index = tile_index & 1
            tx = self.tx_buffers[last_buffer_index]
            packet_started = time.perf_counter()
            stream = tx[:tx_bytes].reshape(groups, stride)
            stream[:, :ACTIVATION_BYTES] = x_bytes
            stream[:, ACTIVATION_BYTES:] = matrix[
                :, block_start:block_stop, :
            ].reshape(groups, tile_blocks * WEIGHT_BYTES)
            packet_ms = (time.perf_counter() - packet_started) * 1000.0
            self.profile["packet_prepare_ms"] += packet_ms
            self.profile["weight_prefetch_copy_ms"] += packet_ms
            outputs.append(
                self._run_tx_buffer(tx, tx_bytes, groups, tile_blocks).reshape(-1)
            )
            self.profile["tiled_kernel_calls"] += 1
        self._launch_prefetch(next_names, last_buffer_index)
        self.profile["linear_calls"] += 1
        self.profile["tiled_linear_calls"] += 1
        self.profile["linear_total_ms"] += (
            time.perf_counter() - linear_started
        ) * 1000.0
        return np.concatenate(outputs)

    def linear(
        self,
        name: str,
        activation: np.ndarray,
        next_names: str | tuple[str, ...] | None = None,
    ) -> np.ndarray:
        shared = self.linear_prefill(
            name, np.asarray(activation, dtype=np.float32).reshape(1, -1)
        )
        return np.asarray(shared, dtype=np.float32).reshape(-1)

        # Legacy two-overlay Decode path retained below for provenance only.
        linear_started = time.perf_counter()
        prepare_started = time.perf_counter()
        item = self.linears[name]
        groups = int(item["input_groups"])
        blocks = int(item["output_blocks"])
        if blocks > self._tile_block_limit(groups):
            return self._linear_tiled(name, activation, next_names, linear_started)
        packet = self._acquire_weight_packet(name)
        _, buffer_index, packet_groups, packet_blocks, _, tx_bytes, _ = packet
        if packet_groups != groups or packet_blocks != blocks:
            raise RuntimeError("prepared packet shape does not match Linear")
        tx = self.tx_buffers[buffer_index]
        stride = ACTIVATION_BYTES + blocks * WEIGHT_BYTES
        stream = tx[:tx_bytes].reshape(groups, stride)
        x = np.asarray(activation, dtype=np.float32).reshape(groups, 64)
        activation_started = time.perf_counter()
        x_bytes = np.ascontiguousarray(x.astype("<f2")).view(np.uint8).reshape(groups, 128)
        stream[:, :ACTIVATION_BYTES] = x_bytes
        self.profile["activation_prepare_ms"] += (
            time.perf_counter() - activation_started
        ) * 1000.0
        self.profile["packet_prepare_ms"] += (time.perf_counter() - prepare_started) * 1000.0
        self._launch_prefetch(next_names, buffer_index)
        result = self._run_tx_buffer(tx, tx_bytes, groups, blocks).reshape(-1)
        self.profile["linear_calls"] += 1
        self.profile["linear_total_ms"] += (time.perf_counter() - linear_started) * 1000.0
        return result

    def linear_qkv(
        self,
        names: tuple[str, str, str],
        activation: np.ndarray,
        next_names: str | tuple[str, ...] | None = None,
    ) -> tuple[np.ndarray, ...]:
        """Submit Q, K, and V packets in one FPGA/DMA transaction."""
        shared = self.linear_prefill(
            names, np.asarray(activation, dtype=np.float32).reshape(1, -1)
        )
        return tuple(np.asarray(item, dtype=np.float32).reshape(-1) for item in shared)

        # Legacy two-overlay Decode path retained below for provenance only.
        linear_started = time.perf_counter()
        prepare_started = time.perf_counter()
        packet = self._acquire_weight_packet(names)
        _, buffer_index, groups, total_blocks, layouts, tx_bytes, _ = packet
        items = [self.linears[name] for name in names]
        groups = int(items[0]["input_groups"])
        if any(int(item["input_groups"]) != groups for item in items):
            raise ValueError("QKV linears must have identical input group counts")
        expected_blocks = sum(int(item["output_blocks"]) for item in items)
        if total_blocks != expected_blocks:
            raise RuntimeError("prepared packet shape does not match QKV batch")
        macro_count = groups * total_blocks
        if macro_count > self.max_macros:
            raise ValueError(f"QKV macro count {macro_count} exceeds allocated range")
        stride = ACTIVATION_BYTES + total_blocks * WEIGHT_BYTES
        tx = self.tx_buffers[buffer_index]
        stream = tx[:tx_bytes].reshape(groups, stride)
        x = np.asarray(activation, dtype=np.float32).reshape(groups, 64)
        activation_started = time.perf_counter()
        x_bytes = np.ascontiguousarray(x.astype("<f2")).view(np.uint8).reshape(groups, 128)
        stream[:, :ACTIVATION_BYTES] = x_bytes
        self.profile["activation_prepare_ms"] += (
            time.perf_counter() - activation_started
        ) * 1000.0
        self.profile["packet_prepare_ms"] += (time.perf_counter() - prepare_started) * 1000.0
        self._launch_prefetch(next_names, buffer_index)
        partials = self._run_tx_buffer(tx, tx_bytes, groups, total_blocks)
        results = tuple(
            partials[start:stop].reshape(-1)
            for start, stop in layouts
        )
        self.profile["linear_calls"] += len(names)
        self.profile["qkv_batch_calls"] += 1
        self.profile["linear_total_ms"] += (time.perf_counter() - linear_started) * 1000.0
        return results

    def _copy_prefill_weight_tile(
        self,
        key: tuple[str, ...],
        block_start: int,
        block_stop: int,
        destination: np.ndarray,
    ) -> tuple[tuple[int, int], ...]:
        """Copy one logical output tile, allowing fused linears to cross boundaries."""
        layouts = []
        logical_start = 0
        for name in key:
            item = self.linears[name]
            blocks = int(item["output_blocks"])
            logical_stop = logical_start + blocks
            overlap_start = max(block_start, logical_start)
            overlap_stop = min(block_stop, logical_stop)
            if overlap_start < overlap_stop:
                groups = int(item["input_groups"])
                weight_start = int(item["offset"])
                weight_stop = weight_start + int(item["bytes"])
                matrix = self.weights[weight_start:weight_stop].reshape(
                    groups, blocks, PREFILL_WEIGHT_BYTES
                )
                source_start = overlap_start - logical_start
                source_stop = overlap_stop - logical_start
                target_start = overlap_start - block_start
                target_stop = overlap_stop - block_start
                destination[:, target_start:target_stop, :] = matrix[
                    :, source_start:source_stop, :
                ]
            layouts.append((logical_start, logical_stop))
            logical_start = logical_stop
        return tuple(layouts)

    def _prepare_prefill_packet(
        self,
        buffer_index: int,
        key: tuple[str, ...],
        block_start: int,
        block_stop: int,
        records: np.ndarray,
        groups: int,
        activation_bytes: int,
    ) -> tuple[int, int, int, int, tuple[tuple[int, int], ...], float]:
        """Assemble one immutable-input tile in a selected CMA buffer."""
        started = time.perf_counter()
        blocks = block_stop - block_start
        stride = activation_bytes + blocks * PREFILL_WEIGHT_BYTES
        tx_bytes = groups * stride
        tx = self.prefill_tx_buffers[buffer_index]
        if tx_bytes > tx.size:
            raise ValueError("Prefill stream size exceeds CMA allocation")
        stream = tx[:tx_bytes].reshape(groups, stride)
        stream[:, :activation_bytes] = records.reshape(groups, activation_bytes)
        weight_destination = stream[:, activation_bytes:].reshape(
            groups, blocks, PREFILL_WEIGHT_BYTES
        )
        layouts = self._copy_prefill_weight_tile(
            key, block_start, block_stop, weight_destination
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return buffer_index, blocks, tx_bytes, block_start, layouts, elapsed_ms

    def linear_prefill(
        self,
        names: str | tuple[str, ...],
        activation: np.ndarray,
    ) -> np.ndarray | tuple[np.ndarray, ...]:
        """Run one or more sequence-batched Transformer projections on PL."""
        self.finish_prefetch()
        key = self._normalise_key(names)
        items = [self.linears[name] for name in key]
        groups = int(items[0]["input_groups"])
        if any(int(item["input_groups"]) != groups for item in items):
            raise ValueError("fused Prefill linears must have identical input groups")
        x = np.asarray(activation, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != groups * 64:
            raise ValueError(
                f"Prefill activation must have shape [tokens, {groups * 64}]"
            )
        tokens = int(x.shape[0])
        tile_limit = self._prefill_tile_block_limit(groups, tokens)
        total_blocks = sum(int(item["output_blocks"]) for item in items)

        started = time.perf_counter()
        if _native_quantize_activation_records is not None:
            records = _native_quantize_activation_records(x)
        else:
            records, _, _ = quantize_activation_records(x)
        self.profile["prefill_activation_quant_ms"] += (
            time.perf_counter() - started
        ) * 1000.0

        output_tiles = []
        layouts: tuple[tuple[int, int], ...] | None = None
        activation_bytes = tokens * PREFILL_ACTIVATION_BYTES
        tiles = [
            (block_start, min(block_start + tile_limit, total_blocks))
            for block_start in range(0, total_blocks, tile_limit)
        ]
        first_start, first_stop = tiles[0]
        exposed_started = time.perf_counter()
        current_packet = self._prepare_prefill_packet(
            0, key, first_start, first_stop, records, groups, activation_bytes
        )
        self.profile["prefill_packet_exposed_ms"] += (
            time.perf_counter() - exposed_started
        ) * 1000.0
        self.profile["prefill_packet_prepare_ms"] += current_packet[-1]
        next_packet = None

        for tile_index, (block_start, block_stop) in enumerate(tiles):
            if tile_index > 0:
                if next_packet is None:
                    raise RuntimeError("Prefill packet pipeline lost the next tile")
                current_packet = next_packet
                next_packet = None
            (
                buffer_index,
                blocks,
                tx_bytes,
                prepared_start,
                layouts,
                packet_ms,
            ) = current_packet
            if prepared_start != block_start:
                raise RuntimeError("Prefill packet pipeline returned the wrong tile")
            rx_values = tokens * blocks * 8
            rx_bytes = rx_values * np.dtype(np.float32).itemsize
            if rx_values > self.prefill_rx.size:
                raise ValueError(f"Prefill result size {rx_values} exceeds CMA allocation")

            tx = self.prefill_tx_buffers[buffer_index]

            sync_started = time.perf_counter()
            tx.sync_to_device()
            self.profile["prefill_sync_to_device_ms"] += (
                time.perf_counter() - sync_started
            ) * 1000.0

            setup_started = time.perf_counter()
            self.prefill_kernel.write(0x10, tokens)
            self.prefill_kernel.write(0x18, groups)
            self.prefill_kernel.write(0x20, blocks)
            self.prefill_dma.recvchannel.transfer(self.prefill_rx, nbytes=rx_bytes)
            self.prefill_kernel.write(0x00, 1)
            self.prefill_dma.sendchannel.transfer(tx, nbytes=tx_bytes)
            self.profile["prefill_kernel_setup_ms"] += (
                time.perf_counter() - setup_started
            ) * 1000.0

            if tile_index + 1 < len(tiles):
                next_start, next_stop = tiles[tile_index + 1]
                next_packet = self._prepare_prefill_packet(
                    1 - buffer_index,
                    key,
                    next_start,
                    next_stop,
                    records,
                    groups,
                    activation_bytes,
                )
                self.profile["prefill_packet_prepare_ms"] += next_packet[-1]
                self.profile["prefill_packet_overlap_launches"] += 1

            wait_started = time.perf_counter()
            self.prefill_dma.sendchannel.wait()
            self.prefill_dma.recvchannel.wait()
            self.profile["prefill_dma_wait_ms"] += (
                time.perf_counter() - wait_started
            ) * 1000.0

            sync_started = time.perf_counter()
            self.prefill_rx.sync_from_device()
            self.profile["prefill_sync_from_device_ms"] += (
                time.perf_counter() - sync_started
            ) * 1000.0
            status = int(self.prefill_kernel.read(0x28))
            if status != 0:
                raise RuntimeError(f"Prefill kernel status={status}")
            observed_build_id = int(self.prefill_kernel.read(0x38))
            if observed_build_id != PREFILL_BUILD_ID:
                raise RuntimeError(
                    f"Prefill PL build ID mismatch: 0x{observed_build_id:08x}"
                )

            copy_started = time.perf_counter()
            output_tiles.append(
                np.array(
                    self.prefill_rx[:rx_values], dtype=np.float32, copy=True
                ).reshape(tokens, blocks * 8)
            )
            self.profile["prefill_result_copy_ms"] += (
                time.perf_counter() - copy_started
            ) * 1000.0
            self.profile["prefill_kernel_calls"] += 1
            self.profile["prefill_stream_input_bytes"] += tx_bytes
            self.profile["prefill_stream_output_bytes"] += rx_bytes

        combined = np.concatenate(output_tiles, axis=1)
        if layouts is None:
            raise RuntimeError("Prefill produced no output tiles")
        results = tuple(
            combined[:, start * 8 : stop * 8] for start, stop in layouts
        )
        self.profile["prefill_linear_calls"] += len(key)
        return results[0] if isinstance(names, str) else results


class QwenRuntime:
    def __init__(self, root: Path, max_seq_len: int = 512):
        from tokenizers import Tokenizer

        self.root = Path(root)
        self.cfg = json.loads((self.root / "model/config.json").read_text())
        self.index = json.loads(_model_index_path(self.root).read_text())
        self.tokenizer = Tokenizer.from_file(str(self.root / "model/tokenizer.json"))
        self.engine = MixedGSEngine(self.root)
        self.aux_blob = self.root / "model" / Path(self.index["aux_file"]["path"]).name
        self.aux = {
            item["name"]: np.memmap(
                self.aux_blob,
                dtype="<f2",
                mode="r",
                offset=int(item["offset"]),
                shape=tuple(item["shape"]),
            )
            for item in self.index["aux_tensors"]
        }
        self.hidden = int(self.cfg["hidden_size"])
        self.heads = int(self.cfg["num_attention_heads"])
        self.kv_heads = int(self.cfg["num_key_value_heads"])
        self.head_dim = self.hidden // self.heads
        self.layers = int(self.cfg["num_hidden_layers"])
        self.eps = float(self.cfg["rms_norm_eps"])
        self.theta = float(self.cfg["rope_theta"])
        self.max_seq_len = int(max_seq_len)
        self.k_cache = [np.empty((max_seq_len, self.kv_heads, self.head_dim), np.float32) for _ in range(self.layers)]
        self.v_cache = [np.empty((max_seq_len, self.kv_heads, self.head_dim), np.float32) for _ in range(self.layers)]
        self.position = 0
        self.embedding = self.aux["model.embed_tokens.weight"]
        if self.engine.lm_head_info is not None:
            if int(self.engine.lm_head_info["hidden_size"]) != self.hidden:
                raise RuntimeError("FPGA LM-head hidden size does not match model")
            if int(self.engine.lm_head_info["vocab_size"]) != int(self.cfg["vocab_size"]):
                raise RuntimeError("FPGA LM-head vocabulary size does not match model")
        self.lm_head_mode = (
            "fpga-w4g64-fp16-rescore256"
            if self.engine.lm_head_info is not None
            else "arm-fp16"
        )
        self.lm_head_ms = 0.0
        self.lm_head_rescore_ms = 0.0
        self.lm_head_calls = 0
        self.prefill_stage_profile: dict[str, float] = {}
        self.prefill_overlay_load_ms = 0.0
        self.decode_overlay_load_ms = 0.0

    def _switch_engine(self, stage: str) -> float:
        # Prefill and Decode share one resident bitstream and one DMA/kernel.
        return 0.0

    def reset(self):
        self.prefill_overlay_load_ms = self._switch_engine("prefill")
        self.decode_overlay_load_ms = 0.0
        self.engine.finish_prefetch()
        self.position = 0
        self.lm_head_ms = 0.0
        self.lm_head_rescore_ms = 0.0
        self.lm_head_calls = 0
        self.prefill_stage_profile = {}
        self.engine.reset_profile()

    def _prefill_stage_add(self, name: str, started: float) -> None:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not hasattr(self, "prefill_stage_profile"):
            self.prefill_stage_profile = {}
        self.prefill_stage_profile[name] = (
            self.prefill_stage_profile.get(name, 0.0) + elapsed_ms
        )

    def _norm(self, x: np.ndarray, weight_name: str) -> np.ndarray:
        weight = np.asarray(self.aux[weight_name], dtype=np.float32)
        scale = 1.0 / math.sqrt(float(np.mean(x * x)) + self.eps)
        return x * scale * weight

    def _norm_batch(self, x: np.ndarray, weight_name: str) -> np.ndarray:
        weight = np.asarray(self.aux[weight_name], dtype=np.float32)
        scale = 1.0 / np.sqrt(
            np.mean(x * x, axis=-1, keepdims=True, dtype=np.float32) + self.eps
        )
        return x * scale * weight

    def _rope(self, x: np.ndarray, position: int) -> np.ndarray:
        half = self.head_dim // 2
        inv = 1.0 / (self.theta ** (np.arange(0, self.head_dim, 2, dtype=np.float32) / self.head_dim))
        phase = position * inv
        cos = np.concatenate((np.cos(phase), np.cos(phase))).astype(np.float32)
        sin = np.concatenate((np.sin(phase), np.sin(phase))).astype(np.float32)
        rotated = np.concatenate((-x[..., half:], x[..., :half]), axis=-1)
        return x * cos + rotated * sin

    def _rope_batch(self, x: np.ndarray, positions: np.ndarray) -> np.ndarray:
        half = self.head_dim // 2
        inv = 1.0 / (
            self.theta
            ** (np.arange(0, self.head_dim, 2, dtype=np.float32) / self.head_dim)
        )
        phase = np.asarray(positions, dtype=np.float32)[:, None] * inv[None, :]
        cos = np.concatenate((np.cos(phase), np.cos(phase)), axis=-1).astype(np.float32)
        sin = np.concatenate((np.sin(phase), np.sin(phase)), axis=-1).astype(np.float32)
        rotated = np.concatenate((-x[..., half:], x[..., :half]), axis=-1)
        return x * cos[:, None, :] + rotated * sin[:, None, :]

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        x = x - np.max(x, axis=-1, keepdims=True)
        y = np.exp(x, dtype=np.float32)
        return y / np.sum(y, axis=-1, keepdims=True)

    def _lm_head(self, x: np.ndarray) -> np.ndarray:
        started = time.perf_counter()
        self.lm_head_calls += 1
        vocab_size = int(self.cfg["vocab_size"])
        if self.engine.lm_head_info is not None:
            approximate = self.engine.linear_lm_head(x)
            shortlist_size = min(LM_HEAD_SHORTLIST, approximate.size)
            shortlist = np.argpartition(approximate, -shortlist_size)[-shortlist_size:]
            rescore_started = time.perf_counter()
            exact = np.asarray(self.embedding[shortlist], dtype=np.float32) @ x
            logits = np.full((vocab_size,), -np.inf, dtype=np.float32)
            logits[shortlist] = exact
            self.lm_head_rescore_ms += (
                time.perf_counter() - rescore_started
            ) * 1000.0
        else:
            # Blocked FP32 accumulation avoids NumPy's low-precision FP16
            # matmul without materializing the embedding matrix as FP32.
            logits = np.empty((vocab_size,), dtype=np.float32)
            for start in range(0, logits.size, 2048):
                stop = min(start + 2048, logits.size)
                block = np.asarray(self.embedding[start:stop], dtype=np.float32)
                logits[start:stop] = block @ x
        self.lm_head_ms += (time.perf_counter() - started) * 1000.0
        return logits

    def forward_token(self, token_id: int, compute_logits: bool = True) -> np.ndarray | None:
        if self.position >= self.max_seq_len:
            raise RuntimeError("KV cache capacity exceeded")
        x = np.asarray(self.embedding[int(token_id)], dtype=np.float32).copy()
        pos = self.position
        repeat = self.heads // self.kv_heads
        for layer in range(self.layers):
            prefix = f"model.layers.{layer}"
            next_prefix = f"model.layers.{layer + 1}" if layer + 1 < self.layers else "model.layers.0"
            qkv_names = (
                f"{prefix}.self_attn.q_proj.weight",
                f"{prefix}.self_attn.k_proj.weight",
                f"{prefix}.self_attn.v_proj.weight",
            )
            next_qkv_names = (
                f"{next_prefix}.self_attn.q_proj.weight",
                f"{next_prefix}.self_attn.k_proj.weight",
                f"{next_prefix}.self_attn.v_proj.weight",
            )
            o_name = f"{prefix}.self_attn.o_proj.weight"
            gate_name = f"{prefix}.mlp.gate_proj.weight"
            up_name = f"{prefix}.mlp.up_proj.weight"
            down_name = f"{prefix}.mlp.down_proj.weight"
            residual = x
            norm = self._norm(x, f"{prefix}.input_layernorm.weight")
            q, k, v = self.engine.linear_qkv(
                qkv_names,
                norm,
                next_names=o_name,
            )
            q += np.asarray(self.aux[f"{prefix}.self_attn.q_proj.bias"], dtype=np.float32)
            k += np.asarray(self.aux[f"{prefix}.self_attn.k_proj.bias"], dtype=np.float32)
            v += np.asarray(self.aux[f"{prefix}.self_attn.v_proj.bias"], dtype=np.float32)
            q = self._rope(q.reshape(self.heads, self.head_dim), pos)
            k = self._rope(k.reshape(self.kv_heads, self.head_dim), pos)
            v = v.reshape(self.kv_heads, self.head_dim)
            self.k_cache[layer][pos] = k
            self.v_cache[layer][pos] = v
            keys = np.repeat(self.k_cache[layer][: pos + 1], repeat, axis=1)
            values = np.repeat(self.v_cache[layer][: pos + 1], repeat, axis=1)
            scores = np.einsum("hd,thd->ht", q, keys, optimize=True) / math.sqrt(self.head_dim)
            probs = self._softmax(scores)
            context = np.einsum("ht,thd->hd", probs, values, optimize=True).reshape(-1)
            x = residual + self.engine.linear(o_name, context, next_names=gate_name)
            residual = x
            norm = self._norm(x, f"{prefix}.post_attention_layernorm.weight")
            gate = self.engine.linear(gate_name, norm, next_names=up_name)
            up = self.engine.linear(up_name, norm, next_names=down_name)
            silu = gate / (1.0 + np.exp(-np.clip(gate, -30.0, 30.0)))
            # The final generated token does not need a speculative layer-0 packet.
            prefetch_after_down = next_qkv_names if (layer + 1 < self.layers or compute_logits) else None
            x = residual + self.engine.linear(
                down_name, silu * up, next_names=prefetch_after_down
            )
        x = self._norm(x, "model.norm.weight")
        self.position += 1
        # Tied FP16 embedding matrix is the LM head; this remains on the A53.
        return self._lm_head(x) if compute_logits else None

    def prefill_tokens(self, token_ids: list[int]) -> np.ndarray:
        """Process a prompt in sequence tiles while preserving causal KV state."""
        if not token_ids:
            raise ValueError("prompt must contain at least one token")
        if self.position + len(token_ids) > self.max_seq_len:
            raise RuntimeError("KV cache capacity exceeded")
        repeat = self.heads // self.kv_heads
        final_hidden = None
        for token_start in range(0, len(token_ids), PREFILL_MAX_TOKENS):
            tile_ids = token_ids[token_start : token_start + PREFILL_MAX_TOKENS]
            tokens = len(tile_ids)
            pos_start = self.position
            pos_stop = pos_start + tokens
            positions = np.arange(pos_start, pos_stop, dtype=np.int32)
            causal = np.arange(pos_stop, dtype=np.int32)[None, :] <= positions[:, None]
            stage_started = time.perf_counter()
            x = np.asarray(self.embedding[tile_ids], dtype=np.float32).copy()
            self._prefill_stage_add("embedding_ms", stage_started)
            for layer in range(self.layers):
                prefix = f"model.layers.{layer}"
                qkv_names = (
                    f"{prefix}.self_attn.q_proj.weight",
                    f"{prefix}.self_attn.k_proj.weight",
                    f"{prefix}.self_attn.v_proj.weight",
                )
                o_name = f"{prefix}.self_attn.o_proj.weight"
                gate_name = f"{prefix}.mlp.gate_proj.weight"
                up_name = f"{prefix}.mlp.up_proj.weight"
                down_name = f"{prefix}.mlp.down_proj.weight"

                residual = x
                stage_started = time.perf_counter()
                norm = self._norm_batch(x, f"{prefix}.input_layernorm.weight")
                self._prefill_stage_add("input_norm_ms", stage_started)
                stage_started = time.perf_counter()
                q, k, v = self.engine.linear_prefill(qkv_names, norm)
                self._prefill_stage_add("qkv_linear_wall_ms", stage_started)
                stage_started = time.perf_counter()
                q += np.asarray(
                    self.aux[f"{prefix}.self_attn.q_proj.bias"], dtype=np.float32
                )
                k += np.asarray(
                    self.aux[f"{prefix}.self_attn.k_proj.bias"], dtype=np.float32
                )
                v += np.asarray(
                    self.aux[f"{prefix}.self_attn.v_proj.bias"], dtype=np.float32
                )
                q = self._rope_batch(
                    q.reshape(tokens, self.heads, self.head_dim), positions
                )
                k = self._rope_batch(
                    k.reshape(tokens, self.kv_heads, self.head_dim), positions
                )
                v = v.reshape(tokens, self.kv_heads, self.head_dim)
                self.k_cache[layer][pos_start:pos_stop] = k
                self.v_cache[layer][pos_start:pos_stop] = v
                # Keep grouped-query heads grouped instead of materialising
                # repeated K/V tensors.  np.matmul dispatches these contiguous
                # batched products to the platform's optimized native path.
                grouped_q = q.reshape(
                    tokens, self.kv_heads, repeat, self.head_dim
                ).transpose(1, 2, 0, 3)
                grouped_k = self.k_cache[layer][:pos_stop].transpose(1, 2, 0)
                scores = np.matmul(
                    grouped_q, grouped_k[:, None, :, :]
                ) / math.sqrt(self.head_dim)
                scores = np.where(causal[None, None, :, :], scores, -np.inf)
                probs = self._softmax(scores)
                grouped_v = self.v_cache[layer][:pos_stop].transpose(1, 0, 2)
                context = np.matmul(
                    probs, grouped_v[:, None, :, :]
                ).transpose(2, 0, 1, 3).reshape(tokens, self.hidden)
                self._prefill_stage_add("attention_cpu_ms", stage_started)
                stage_started = time.perf_counter()
                projected = self.engine.linear_prefill(o_name, context)
                self._prefill_stage_add("o_linear_wall_ms", stage_started)
                stage_started = time.perf_counter()
                x = residual + projected
                self._prefill_stage_add("attention_residual_ms", stage_started)

                residual = x
                stage_started = time.perf_counter()
                norm = self._norm_batch(
                    x, f"{prefix}.post_attention_layernorm.weight"
                )
                self._prefill_stage_add("post_norm_ms", stage_started)
                stage_started = time.perf_counter()
                gate, up = self.engine.linear_prefill(
                    (gate_name, up_name), norm
                )
                self._prefill_stage_add("gate_up_linear_wall_ms", stage_started)
                stage_started = time.perf_counter()
                if _native_silu_mul is not None:
                    down_input = _native_silu_mul(gate, up)
                else:
                    # One scratch tensor replaces the expression form's
                    # clip/negate/exp/denominator/multiply temporary chain.
                    silu = np.clip(gate, -30.0, 30.0)
                    np.negative(silu, out=silu)
                    np.exp(silu, out=silu)
                    silu += 1.0
                    np.divide(gate, silu, out=silu)
                    np.multiply(silu, up, out=silu)
                    down_input = silu
                self._prefill_stage_add("mlp_activation_ms", stage_started)
                stage_started = time.perf_counter()
                down = self.engine.linear_prefill(down_name, down_input)
                self._prefill_stage_add("down_linear_wall_ms", stage_started)
                stage_started = time.perf_counter()
                x = residual + down
                self._prefill_stage_add("mlp_residual_ms", stage_started)
            stage_started = time.perf_counter()
            final_hidden = self._norm_batch(x, "model.norm.weight")
            self._prefill_stage_add("final_norm_ms", stage_started)
            self.position = pos_stop
        if final_hidden is None:
            raise RuntimeError("Prefill produced no hidden state")
        return np.asarray(final_hidden[-1], dtype=np.float32).copy()

    def encode_chat(self, user_text: str) -> list[int]:
        prompt = (
            "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant."
            "<|im_end|>\n<|im_start|>user\n" + user_text + "<|im_end|>\n<|im_start|>assistant\n"
        )
        return self.tokenizer.encode(prompt, add_special_tokens=False).ids

    def generate(self, user_text: str, max_new_tokens: int = 16, sampling: str = "argmax", seed: int = 42):
        request_started = time.perf_counter()
        ids = self.encode_chat(user_text)
        tokenization_ms = (time.perf_counter() - request_started) * 1000.0
        if len(ids) + max_new_tokens > self.max_seq_len:
            raise ValueError("prompt plus generation exceeds KV cache")
        self.reset()
        before_prefill_calls, before_prefill_macros = self.engine.prefill_counters()
        started = time.perf_counter()
        final_hidden = self.prefill_tokens(ids)
        prefill_compute_completed = time.perf_counter()
        prefill_batch_calls, prefill_batch_macros = self.engine.prefill_counters()
        prefill_profile = self.engine.profile_snapshot()
        self.decode_overlay_load_ms = self._switch_engine("decode")
        before_calls, before_macros = self.engine.counters()
        logits = self._lm_head(final_hidden)
        prefill_completed = time.perf_counter()
        prefill_ms = (prefill_completed - started) * 1000.0
        prefill_calls, prefill_macros = self.engine.counters()
        prefill_lm_head_ms = float(self.lm_head_ms)
        prefill_accounted_ms = sum(
            float(prefill_profile[name])
            for name in (
                "prefill_activation_quant_ms",
                "prefill_packet_exposed_ms",
                "prefill_sync_to_device_ms",
                "prefill_kernel_setup_ms",
                "prefill_dma_wait_ms",
                "prefill_sync_from_device_ms",
                "prefill_result_copy_ms",
            )
        )
        prefill_cpu_other_ms = max(
            0.0,
            prefill_ms
            - prefill_accounted_ms
            - prefill_lm_head_ms
            - self.decode_overlay_load_ms,
        )
        generated = []
        rng = np.random.default_rng(seed)
        ttft_ms = None
        ttft_inference_ms = None
        for step in range(max_new_tokens):
            if sampling == "argmax":
                next_id = int(np.argmax(logits))
            elif sampling == "topk":
                top = np.argpartition(logits, -20)[-20:]
                values = logits[top] - np.max(logits[top])
                probability = np.exp(values / 0.7)
                probability /= probability.sum()
                next_id = int(rng.choice(top, p=probability))
            else:
                raise ValueError("sampling must be argmax or topk")
            if step == 0:
                first_token_ready = time.perf_counter()
                ttft_ms = (first_token_ready - request_started) * 1000.0
                ttft_inference_ms = (first_token_ready - started) * 1000.0
            if next_id == int(self.cfg["eos_token_id"]):
                break
            generated.append(next_id)
            logits = self.forward_token(next_id, compute_logits=step + 1 < max_new_tokens)
        after_calls, after_macros = self.engine.counters()
        wall_ms = (time.perf_counter() - started) * 1000.0
        request_wall_ms = (time.perf_counter() - request_started) * 1000.0
        decode_after_first_ms = max(
            0.0, wall_ms - float(ttft_inference_ms or wall_ms)
        )
        profile = self.engine.profile_snapshot()
        batch_prefill_profile_ms = sum(
            float(profile[name])
            for name in (
                "prefill_activation_quant_ms",
                "prefill_packet_exposed_ms",
                "prefill_sync_to_device_ms",
                "prefill_kernel_setup_ms",
                "prefill_dma_wait_ms",
                "prefill_sync_from_device_ms",
                "prefill_result_copy_ms",
            )
        )
        cpu_other_ms = max(
            0.0,
            wall_ms
            - float(profile["linear_total_ms"])
            - prefill_accounted_ms
            - self.lm_head_ms
            - self.decode_overlay_load_ms,
        )
        decode_call_delta = after_calls - before_calls
        decode_macro_delta = after_macros - before_macros
        batch_call_delta = prefill_batch_calls - before_prefill_calls
        batch_macro_delta = prefill_batch_macros - before_prefill_macros
        proof = {
            "result": "PASS" if (
                decode_call_delta > 0
                and decode_macro_delta > 0
                and batch_call_delta > 0
                and batch_macro_delta > 0
            ) else "FAIL",
            "build_id": f"0x{BUILD_ID:08x}",
            "prefill_build_id": f"0x{PREFILL_BUILD_ID:08x}",
            "runtime_optimization": RUNTIME_OPTIMIZATION,
            "pl_kernel_calls": decode_call_delta + batch_call_delta,
            "pl_macros": decode_macro_delta + batch_macro_delta,
            "prompt_tokens": len(ids),
            "generated_tokens": len(generated),
            "wall_ms": wall_ms,
            "request_wall_ms": request_wall_ms,
            "tokenization_ms": tokenization_ms,
            "prefill_ms": prefill_ms,
            "prefill_compute_ms": (
                prefill_compute_completed - started
            ) * 1000.0,
            "prefill_overlay_load_ms": self.prefill_overlay_load_ms,
            "decode_overlay_load_ms": self.decode_overlay_load_ms,
            "ttft_ms": float(ttft_ms or request_wall_ms),
            "ttft_inference_ms": float(ttft_inference_ms or wall_ms),
            "decode_after_first_ms": decode_after_first_ms,
            "sampling": sampling,
            "prefill_pl_kernel_calls": prefill_batch_calls - before_prefill_calls,
            "prefill_pl_macros": prefill_batch_macros - before_prefill_macros,
            "prefill_decode_kernel_calls": prefill_calls - before_calls,
            "prefill_decode_kernel_macros": prefill_macros - before_macros,
            "prefill_linear_calls": int(prefill_profile["prefill_linear_calls"]),
            "prefill_batch_kernel_calls": int(prefill_profile["prefill_kernel_calls"]),
            "prefill_qkv_batch_calls": (
                (len(ids) + PREFILL_MAX_TOKENS - 1) // PREFILL_MAX_TOKENS
            ) * self.layers,
            "prefill_activation_quant_ms": float(
                prefill_profile["prefill_activation_quant_ms"]
            ),
            "prefill_packet_prepare_ms": float(
                prefill_profile["prefill_packet_prepare_ms"]
            ),
            "prefill_packet_exposed_ms": float(
                prefill_profile["prefill_packet_exposed_ms"]
            ),
            "prefill_packet_overlap_launches": int(
                prefill_profile["prefill_packet_overlap_launches"]
            ),
            "prefill_weight_prefetch_copy_ms": float(
                prefill_profile["weight_prefetch_copy_ms"]
            ),
            "prefill_weight_prefetch_wait_ms": float(
                prefill_profile["weight_prefetch_wait_ms"]
            ),
            "prefill_dma_wait_ms": float(prefill_profile["prefill_dma_wait_ms"]),
            "prefill_stream_input_bytes": int(
                prefill_profile["prefill_stream_input_bytes"]
            ),
            "prefill_stream_output_bytes": int(
                prefill_profile["prefill_stream_output_bytes"]
            ),
            "prefill_lm_head_ms": prefill_lm_head_ms,
            "prefill_cpu_other_ms": prefill_cpu_other_ms,
            "prefill_stage_profile": dict(self.prefill_stage_profile),
            "prefill_elementwise_mode": PREFILL_ELEMENTWISE_MODE,
            "prefill_activation_mode": PREFILL_ACTIVATION_MODE,
            "profile_linear_calls": int(profile["linear_calls"]),
            "profile_qkv_batch_calls": int(profile["qkv_batch_calls"]),
            "profile_packet_prepare_ms": float(profile["packet_prepare_ms"]),
            "profile_activation_prepare_ms": float(profile["activation_prepare_ms"]),
            "profile_weight_prefetch_copy_ms": float(profile["weight_prefetch_copy_ms"]),
            "profile_weight_prefetch_wait_ms": float(profile["weight_prefetch_wait_ms"]),
            "profile_weight_prefetch_launches": int(profile["weight_prefetch_launches"]),
            "profile_weight_prefetch_hits": int(profile["weight_prefetch_hits"]),
            "profile_weight_prefetch_misses": int(profile["weight_prefetch_misses"]),
            "profile_tx_copy_ms": float(profile["tx_copy_ms"]),
            "profile_sync_ms": float(profile["sync_to_device_ms"] + profile["sync_from_device_ms"]),
            "profile_kernel_setup_ms": float(profile["kernel_setup_ms"]),
            "profile_dma_wait_ms": float(profile["dma_wait_ms"]),
            "profile_result_ms": float(profile["result_copy_ms"] + profile["reduce_ms"]),
            "profile_stream_input_bytes": int(profile["stream_input_bytes"]),
            "profile_stream_output_bytes": int(profile["stream_output_bytes"]),
            "profile_lm_head_ms": float(self.lm_head_ms),
            "profile_lm_head_calls": int(self.lm_head_calls),
            "profile_lm_head_mode": self.lm_head_mode,
            "profile_lm_head_rescore_ms": float(self.lm_head_rescore_ms),
            "profile_lm_head_kernel_calls": int(profile["lm_head_kernel_calls"]),
            "profile_lm_head_packet_ms": float(profile["lm_head_packet_ms"]),
            "profile_lm_head_packet_exposed_ms": float(
                profile["lm_head_packet_exposed_ms"]
            ),
            "profile_lm_head_packet_overlap_tiles": int(
                profile["lm_head_packet_overlap_tiles"]
            ),
            "profile_cpu_other_ms": cpu_other_ms,
        }
        if proof["result"] != "PASS":
            raise RuntimeError("FPGA proof counters did not advance")
        return self.tokenizer.decode(generated, skip_special_tokens=True), proof
