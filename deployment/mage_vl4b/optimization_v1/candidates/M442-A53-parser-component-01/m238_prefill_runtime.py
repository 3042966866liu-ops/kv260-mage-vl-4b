#!/usr/bin/env python3
"""M238: overlap T32 input quantization/packing with FPGA execution.

This candidate is deliberately independent of T64.  It preserves the accepted
M236 T32 packet, adaptive-scale retry, dual output buffers and fused parser.
Only the host schedule changes: while block N executes in PL, one CPU worker
prepares the immutable packet bytes for block N+1.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

import board_runtime as base
from m231_prefill_runtime import _output_widths
from m236_prefill_runtime import M236PrefillRuntime, _PendingBlock


@dataclass(frozen=True)
class _PreparedBlock:
    values: np.ndarray
    token_start: int
    token_count: int
    initial_shift: int
    packet: bytes
    pack_ms: float


class M238PrefillRuntime(M236PrefillRuntime):
    """M236 plus one-block-ahead host packing, without changing PL work."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack_prefetch_submissions = 0
        self.pack_prefetch_wait_ms = 0.0
        self.pack_prefetch_compute_ms = 0.0
        self.prepacked_launches = 0

    @staticmethod
    def _prepare_block(
        chain: dict,
        values: np.ndarray,
        token_start: int,
        descriptor_offset_base_words: int,
        initial_shift: int,
    ) -> _PreparedBlock:
        started = time.perf_counter()
        packet = base.pack_chain_input(
            chain,
            values,
            descriptor_offset_base_words,
            activation_scale_shift=initial_shift,
        )
        return _PreparedBlock(
            values=values,
            token_start=token_start,
            token_count=int(values.shape[0]),
            initial_shift=initial_shift,
            packet=packet,
            pack_ms=(time.perf_counter() - started) * 1000.0,
        )

    def _launch_prepacked(
        self,
        chain: dict,
        prepared: _PreparedBlock,
        buffers: list,
        output_buffer,
    ) -> None:
        input_bytes = len(prepared.packet)
        if input_bytes != int(chain["input_bytes"]):
            raise RuntimeError("M238 prepacked input packet size mismatch")

        started = time.perf_counter()
        self.input_buffer[:input_bytes] = np.frombuffer(prepared.packet, dtype=np.uint8)
        self._record_phase(chain, "input_copy", started)
        started = time.perf_counter()
        self.input_buffer.sync_to_device()
        self._record_phase(chain, "input_sync", started)
        started = time.perf_counter()
        self._program_static_registers(chain, buffers)
        self._record_phase(chain, "register_setup", started)

        started = time.perf_counter()
        self.dma.recvchannel.transfer(output_buffer, nbytes=int(chain["output_bytes"]))
        self.kernel.write(base.REG_AP_CTRL, 1)
        self.dma.sendchannel.transfer(self.input_buffer, nbytes=input_bytes)
        snapshot = base.wait_transaction(self.kernel, self.dma, 10.0)
        self._record_phase(chain, "launch_wait", started)
        returned = int(snapshot["ap_return"])
        if returned != base.BUILD_ID:
            raise RuntimeError(f"M120/M89X2 build/status mismatch: 0x{returned:08x}")

        started = time.perf_counter()
        output_buffer.sync_from_device()
        self._record_phase(chain, "output_sync", started)
        self.host_calls += 1
        self.expected_macros += int(chain["expected_macros"])
        self.prepacked_launches += 1

    def language_family_many(
        self, layer: int, family: str, values: np.ndarray
    ) -> dict[str, np.ndarray]:
        array = np.asarray(values, dtype=np.float32)
        if array.ndim != 2 or array.shape[0] < 1:
            raise ValueError("language_family_many expects a non-empty rank-2 activation")
        chain = self._language_chain(layer, family)
        expected_width = int(chain["groups"]) * 64
        if array.shape[1] != expected_width:
            raise ValueError(
                f"language_family_many width mismatch: {array.shape[1]} != {expected_width}"
            )
        if self.output_buffer_alt is None:
            raise RuntimeError("M238 alternate output buffer is unavailable")

        if self.weight_mode == "staged-low-cma":
            buffers, base_words = self._stage(self.language_layout, chain)
            self.family_stage_count[self._family_key(chain)] += 1
        else:
            buffers, base_words = self.language_buffers, 0
        targets = {
            name: np.full((array.shape[0], width), np.nan, dtype=np.float32)
            for name, width in _output_widths(chain).items()
        }
        self.family_output_allocations[self._family_key(chain)] += len(targets)

        blocks = list(range(0, array.shape[0], 32))
        output_buffers = (self.output_buffer, self.output_buffer_alt)
        pending_by_buffer: dict[int, _PendingBlock] = {}

        def submit_pack(executor, token_start: int):
            token_count = min(32, array.shape[0] - token_start)
            block_values = array[token_start:token_start + token_count]
            initial_shift = self._initial_scale_shift(block_values)
            self.pack_prefetch_submissions += 1
            return executor.submit(
                self._prepare_block,
                chain,
                block_values,
                token_start,
                base_words,
                initial_shift,
            )

        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="m238-pack") as pack_executor, \
             ThreadPoolExecutor(max_workers=1, thread_name_prefix="m238-parse") as parse_executor:
            pack_future = submit_pack(pack_executor, blocks[0])
            for block_index, token_start in enumerate(blocks):
                wait_started = time.perf_counter()
                prepared = pack_future.result()
                self.pack_prefetch_wait_ms += (time.perf_counter() - wait_started) * 1000.0
                self.pack_prefetch_compute_ms += prepared.pack_ms
                # Preserve M230 phase accounting while keeping the work itself
                # on the prefetch worker.
                self.phase_ms["pack"] += prepared.pack_ms
                self.phase_calls["pack"] += 1
                self.family_phase_ms[self._family_key(chain)]["pack"] += prepared.pack_ms
                if block_index + 1 < len(blocks):
                    pack_future = submit_pack(pack_executor, blocks[block_index + 1])

                buffer_index = block_index & 1
                previous = pending_by_buffer.pop(buffer_index, None)
                if previous is not None:
                    self.pipeline_reuse_waits += 1
                    self._resolve_pending(chain, buffers, targets, base_words, previous)

                output_buffer = output_buffers[buffer_index]
                self._launch_prepacked(chain, prepared, buffers, output_buffer)
                future = parse_executor.submit(
                    self._parse_buffer,
                    chain,
                    output_buffer,
                    targets,
                    prepared.token_start,
                    prepared.token_count,
                    prepared.initial_shift,
                )
                pending_by_buffer[buffer_index] = _PendingBlock(
                    future=future,
                    values=prepared.values,
                    output_buffer=output_buffer,
                    token_start=prepared.token_start,
                    token_count=prepared.token_count,
                    initial_shift=prepared.initial_shift,
                    attempted_shifts=[prepared.initial_shift],
                )
                self.pipeline_submissions += 1
                self.family_t32_blocks[self._family_key(chain)] += 1

            for buffer_index in sorted(pending_by_buffer):
                self._resolve_pending(
                    chain, buffers, targets, base_words, pending_by_buffer[buffer_index]
                )

        if not all(np.isfinite(value).all() for value in targets.values()):
            raise RuntimeError("M238 family output contains unfilled or non-finite rows")
        return targets

    def evidence(self) -> dict:
        result = super().evidence()
        result.update({
            "prefill_scheduler": "m238-t32-input-pack-prefetch-plus-m236-fused-parse-overlap",
            "input_pack_prefetch": True,
            "pack_prefetch_depth": 1,
            "pack_prefetch_submissions": self.pack_prefetch_submissions,
            "pack_prefetch_wait_ms": self.pack_prefetch_wait_ms,
            "pack_prefetch_compute_ms": self.pack_prefetch_compute_ms,
            "prepacked_launches": self.prepacked_launches,
            "input_packet_contract_changed": False,
            "fpga_transaction_contract_changed": False,
            "model_math_changed": False,
        })
        return result
