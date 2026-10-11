#!/usr/bin/env python3
"""M236 T32 dual-buffer pipeline with finiteness fused into parsing.

M235 proved that parsing block N can overlap FPGA execution of block N+1, but
its separate raw-output finite scan added about 404 ms to the frozen 849-token
q-family workload.  M236 preserves the adaptive scale retry contract while
checking the already materialized FP32 values inside the parser.  The common
finite path therefore performs no second raw-buffer scan.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

import board_runtime as base
from m231_prefill_runtime import M231PrefillRuntime, _half_values_strided, _output_widths


@dataclass
class _PendingBlock:
    future: Future
    values: np.ndarray
    output_buffer: object
    token_start: int
    token_count: int
    initial_shift: int
    attempted_shifts: list[int]


class M236PrefillRuntime(M231PrefillRuntime):
    """M231 with two DMA outputs and fused parse/finiteness validation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_buffer_alt = self.allocate(self.output_buffer.shape, dtype=np.uint8)
        if (
            base.physical_address(self.output_buffer_alt) + self.output_buffer_alt.nbytes
            > base.LOW_END
        ):
            self.output_buffer_alt.freebuffer()
            self.output_buffer_alt = None
            raise RuntimeError("M236 alternate output DMA buffer outside low DDR")
        self.pipeline_submissions = 0
        self.pipeline_reuse_waits = 0
        self.pipeline_retry_launches = 0
        self.fused_nonfinite_detections = 0

    @staticmethod
    def _parse_into_and_check(
        chain: dict,
        payload: bytes | bytearray | memoryview,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
        output_scale_shift: int,
    ) -> bool:
        if not isinstance(output_scale_shift, int) or not 0 <= output_scale_shift <= 10:
            raise ValueError("output_scale_shift must be an integer in [0, 10]")
        if token_count < 1 or token_count > 32:
            raise ValueError("token_count must be in [1, 32]")
        raw = memoryview(payload)
        if len(raw) != int(chain["output_bytes"]):
            raise RuntimeError("M236 output packet size mismatch")

        cursor = 0
        checked = 0
        finite = True
        for descriptor in chain["descriptors"]:
            size = int(descriptor["output_bytes"])
            values = _half_values_strided(raw[cursor:cursor + size])
            cursor += size
            rows = int(descriptor["rows_per_shard"])
            if rows <= 0 or rows % 8:
                raise RuntimeError("M236 rows_per_shard contract mismatch")
            blocks = rows // 8
            assembled = values.reshape(blocks, 32, 4, 4, 2)
            assembled = assembled.transpose(1, 2, 0, 3, 4).reshape(32, 4 * rows)
            if output_scale_shift:
                assembled = np.ldexp(assembled, -output_scale_shift).astype(np.float32)
            valid = int(descriptor["valid_rows"])
            name = descriptor.get("module", "lm_head")
            row_start = int(descriptor["row_start"])
            row_stop = row_start + valid
            if name not in targets or targets[name].shape[1] < row_stop:
                raise RuntimeError(f"M236 preallocated target is incomplete for {name}")
            written = assembled[:token_count, :valid]
            # The check consumes the same cache-hot FP32 view immediately before
            # assignment; no second traversal of the raw DMA packet is performed.
            finite = bool(np.isfinite(written).all()) and finite
            targets[name][token_start:token_start + token_count, row_start:row_stop] = written
            checked += token_count * valid
        if cursor != len(raw):
            raise RuntimeError("M236 output cursor mismatch")
        return finite and checked > 0

    def _launch_once(
        self,
        chain: dict,
        values: np.ndarray,
        buffers: list,
        output_buffer,
        descriptor_offset_base_words: int,
        shift: int,
    ) -> None:
        started = time.perf_counter()
        packet = base.pack_chain_input(
            chain,
            values,
            descriptor_offset_base_words,
            activation_scale_shift=shift,
        )
        self._record_phase(chain, "pack", started)
        input_bytes = len(packet)

        started = time.perf_counter()
        self.input_buffer[:input_bytes] = np.frombuffer(packet, dtype=np.uint8)
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

    def _parse_buffer(
        self,
        chain: dict,
        output_buffer,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
        shift: int,
    ) -> bool:
        started = time.perf_counter()
        finite = self._parse_into_and_check(
            chain,
            memoryview(output_buffer)[:int(chain["output_bytes"])],
            targets,
            token_start,
            token_count,
            shift,
        )
        self._record_phase(chain, "parse", started)
        return finite

    def _accept_shift(
        self,
        chain: dict,
        values: np.ndarray,
        initial_shift: int,
        attempted: list[int],
        selected_shift: int,
    ) -> None:
        self.logical_calls += 1
        self.logical_expected_macros += int(chain["expected_macros"])
        self.scale_retry_count += len(attempted) - 1
        self.scale_shift_counts[str(selected_shift)] += 1
        self.scale_attempts.append({
            "chain_index": int(chain["chain_index"]),
            "layer": int(chain["layer"]) if chain.get("layer") is not None else None,
            "family": chain.get("family", "lm_head"),
            "initial_shift": initial_shift,
            "attempted_shifts": attempted,
            "selected_shift": selected_shift,
            "input_max_abs": float(np.max(np.abs(np.asarray(values, dtype=np.float32)))),
        })

    def _resolve_pending(
        self,
        chain: dict,
        buffers: list,
        targets: dict[str, np.ndarray],
        descriptor_offset_base_words: int,
        pending: _PendingBlock,
    ) -> None:
        finite = bool(pending.future.result())
        if finite:
            self._accept_shift(
                chain,
                pending.values,
                pending.initial_shift,
                pending.attempted_shifts,
                pending.attempted_shifts[-1],
            )
            return

        self.fused_nonfinite_detections += 1
        for shift in range(
            pending.attempted_shifts[-1] - 1,
            base.MIN_ACTIVATION_SCALE_SHIFT - 1,
            -1,
        ):
            pending.attempted_shifts.append(shift)
            self.pipeline_retry_launches += 1
            self._launch_once(
                chain,
                pending.values,
                buffers,
                pending.output_buffer,
                descriptor_offset_base_words,
                shift,
            )
            if self._parse_buffer(
                chain,
                pending.output_buffer,
                targets,
                pending.token_start,
                pending.token_count,
                shift,
            ):
                self._accept_shift(
                    chain,
                    pending.values,
                    pending.initial_shift,
                    pending.attempted_shifts,
                    shift,
                )
                return
            self.fused_nonfinite_detections += 1

        self.scale_retry_count += max(0, len(pending.attempted_shifts) - 1)
        self.scale_attempts.append({
            "chain_index": int(chain["chain_index"]),
            "layer": int(chain["layer"]) if chain.get("layer") is not None else None,
            "family": chain.get("family", "lm_head"),
            "initial_shift": pending.initial_shift,
            "attempted_shifts": pending.attempted_shifts,
            "selected_shift": None,
            "input_max_abs": float(np.max(np.abs(np.asarray(pending.values, dtype=np.float32)))),
        })
        raise FloatingPointError(
            f"non-finite FPGA output after adaptive shifts {pending.attempted_shifts}; "
            f"layer={chain.get('layer')} family={chain.get('family', 'lm_head')}"
        )

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
            raise RuntimeError("M236 alternate output buffer is unavailable")

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

        output_buffers = (self.output_buffer, self.output_buffer_alt)
        pending_by_buffer: dict[int, _PendingBlock] = {}
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="m236-parse") as executor:
            for block_index, token_start in enumerate(range(0, array.shape[0], 32)):
                buffer_index = block_index & 1
                previous = pending_by_buffer.pop(buffer_index, None)
                if previous is not None:
                    self.pipeline_reuse_waits += 1
                    self._resolve_pending(chain, buffers, targets, base_words, previous)

                token_count = min(32, array.shape[0] - token_start)
                block_values = array[token_start:token_start + token_count]
                initial_shift = self._initial_scale_shift(block_values)
                output_buffer = output_buffers[buffer_index]
                self._launch_once(
                    chain,
                    block_values,
                    buffers,
                    output_buffer,
                    base_words,
                    initial_shift,
                )
                future = executor.submit(
                    self._parse_buffer,
                    chain,
                    output_buffer,
                    targets,
                    token_start,
                    token_count,
                    initial_shift,
                )
                pending_by_buffer[buffer_index] = _PendingBlock(
                    future=future,
                    values=block_values,
                    output_buffer=output_buffer,
                    token_start=token_start,
                    token_count=token_count,
                    initial_shift=initial_shift,
                    attempted_shifts=[initial_shift],
                )
                self.pipeline_submissions += 1
                self.family_t32_blocks[self._family_key(chain)] += 1

            for buffer_index in sorted(pending_by_buffer):
                self._resolve_pending(
                    chain,
                    buffers,
                    targets,
                    base_words,
                    pending_by_buffer[buffer_index],
                )

        if not all(np.isfinite(value).all() for value in targets.values()):
            raise RuntimeError("M236 family output contains unfilled or non-finite rows")
        return targets

    def evidence(self) -> dict:
        result = super().evidence()
        result.update({
            "prefill_scheduler": "m236-family-stage-once-dual-output-fused-parse-overlap-t32",
            "output_parser": "m231-strided-fp16-direct-final-buffer-fused-finite-v1",
            "dual_output_dma_buffers": True,
            "alternate_output_buffer_bytes": int(self.output_buffer_alt.nbytes),
            "pipeline_submissions": self.pipeline_submissions,
            "pipeline_reuse_waits": self.pipeline_reuse_waits,
            "pipeline_retry_launches": self.pipeline_retry_launches,
            "fused_nonfinite_detections": self.fused_nonfinite_detections,
            "standalone_raw_finite_scan": False,
            "adaptive_scale_retry_preserved": True,
            "fpga_transaction_contract_changed": False,
            "model_math_changed": False,
        })
        return result

    def close(self) -> None:
        alternate = getattr(self, "output_buffer_alt", None)
        if alternate is not None:
            alternate.freebuffer()
            self.output_buffer_alt = None
        super().close()
