#!/usr/bin/env python3
"""M235 T32 output-parse/next-launch overlap candidate.

The accepted M231 parser and FPGA transaction are preserved.  A second 2.5 MiB
maximum-sized output DMA buffer allows the CPU to parse block N while the same
single FPGA kernel executes block N+1.  Before a result enters the pipeline, a
cheap view-only FP16 finiteness check preserves M231's adaptive retry rule.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor

import numpy as np

import board_runtime as base
from m231_prefill_runtime import M231PrefillRuntime, _output_widths


class M235PrefillRuntime(M231PrefillRuntime):
    """M231 with two output buffers and one ordered host parser worker."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_buffer_alt = self.allocate(self.output_buffer.shape, dtype=np.uint8)
        if (
            base.physical_address(self.output_buffer_alt) + self.output_buffer_alt.nbytes
            > base.LOW_END
        ):
            self.output_buffer_alt.freebuffer()
            self.output_buffer_alt = None
            raise RuntimeError("M235 alternate output DMA buffer outside low DDR")
        self.phase_ms["finite_check"] = 0.0
        self.phase_calls["finite_check"] = 0
        for phases in self.family_phase_ms.values():
            phases["finite_check"] = 0.0
        self.pipeline_submissions = 0
        self.pipeline_reuse_waits = 0

    def _record_extra_phase(self, chain: dict, phase: str, started: float) -> None:
        elapsed = (time.perf_counter() - started) * 1000.0
        self.phase_ms[phase] += elapsed
        self.phase_calls[phase] += 1
        family = self.family_phase_ms[self._family_key(chain)]
        if phase not in family:
            family[phase] = 0.0
        family[phase] += elapsed

    @staticmethod
    def _raw_written_slice_finite(
        chain: dict,
        payload: bytes | bytearray | memoryview,
        token_count: int,
    ) -> bool:
        if token_count < 1 or token_count > 32:
            raise ValueError("token_count must be in [1, 32]")
        raw = memoryview(payload)
        if len(raw) != int(chain["output_bytes"]):
            raise RuntimeError("M235 raw output packet size mismatch")
        cursor = 0
        checked = 0
        for descriptor in chain.get("descriptors", []):
            size = int(descriptor["output_bytes"])
            rows = int(descriptor["rows_per_shard"])
            if rows <= 0 or rows % 8:
                raise RuntimeError("M235 rows_per_shard contract mismatch")
            blocks = rows // 8
            words = size // 8
            if words != blocks * 32 * 4 * 4:
                raise RuntimeError("M235 descriptor output word count/layout mismatch")
            octets = np.frombuffer(raw[cursor:cursor + size], dtype=np.uint8)
            cursor += size
            lanes = np.ndarray(
                shape=(words, 2),
                dtype="<f2",
                buffer=octets,
                strides=(8, 4),
            )
            source = lanes.reshape(blocks, 32, 4, 4, 2).transpose(1, 2, 0, 3, 4)
            if not np.isfinite(source[:token_count]).all():
                return False
            checked += token_count * int(descriptor["valid_rows"])
        if cursor != len(raw):
            raise RuntimeError("M235 raw output cursor mismatch")
        return checked > 0

    def _run_block_to_buffer(
        self,
        chain: dict,
        values: np.ndarray,
        buffers: list,
        output_buffer,
        token_count: int,
        descriptor_offset_base_words: int,
    ) -> int:
        output_bytes = int(chain["output_bytes"])
        initial_shift = self._initial_scale_shift(values)
        attempted: list[int] = []
        for shift in range(initial_shift, base.MIN_ACTIVATION_SCALE_SHIFT - 1, -1):
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
            self.dma.recvchannel.transfer(output_buffer, nbytes=output_bytes)
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
            attempted.append(shift)

            started = time.perf_counter()
            finite = self._raw_written_slice_finite(
                chain,
                memoryview(output_buffer)[:output_bytes],
                token_count,
            )
            self._record_extra_phase(chain, "finite_check", started)
            if finite:
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
                return shift

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

    def _parse_buffer(
        self,
        chain: dict,
        output_buffer,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
        shift: int,
    ) -> None:
        started = time.perf_counter()
        self._parse_into(
            chain,
            memoryview(output_buffer)[:int(chain["output_bytes"])],
            targets,
            token_start,
            token_count,
            shift,
        )
        self._record_phase(chain, "parse", started)

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
            raise RuntimeError("M235 alternate output buffer is unavailable")

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
        pending: dict[int, Future] = {}
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="m235-parse") as executor:
            for block_index, token_start in enumerate(range(0, array.shape[0], 32)):
                buffer_index = block_index & 1
                previous = pending.pop(buffer_index, None)
                if previous is not None:
                    self.pipeline_reuse_waits += 1
                    previous.result()
                token_count = min(32, array.shape[0] - token_start)
                output_buffer = output_buffers[buffer_index]
                shift = self._run_block_to_buffer(
                    chain,
                    array[token_start:token_start + token_count],
                    buffers,
                    output_buffer,
                    token_count,
                    base_words,
                )
                pending[buffer_index] = executor.submit(
                    self._parse_buffer,
                    chain,
                    output_buffer,
                    targets,
                    token_start,
                    token_count,
                    shift,
                )
                self.pipeline_submissions += 1
                self.family_t32_blocks[self._family_key(chain)] += 1
            for future in pending.values():
                future.result()

        if not all(np.isfinite(value).all() for value in targets.values()):
            raise RuntimeError("M235 family output contains unfilled rows")
        return targets

    def evidence(self) -> dict:
        result = super().evidence()
        result.update({
            "prefill_scheduler": "m235-family-stage-once-dual-output-parse-overlap-t32",
            "output_parser": "m231-strided-fp16-direct-final-buffer-v1",
            "dual_output_dma_buffers": True,
            "alternate_output_buffer_bytes": int(self.output_buffer_alt.nbytes),
            "pipeline_submissions": self.pipeline_submissions,
            "pipeline_reuse_waits": self.pipeline_reuse_waits,
            "raw_finite_precheck": "fp16-useful-lanes-token-slice-v1",
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

