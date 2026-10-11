#!/usr/bin/env python3
"""M231 bit-exact T32 parser and family output-buffer reuse candidate.

The accepted M230 scheduler already stages one family weight window once.  M231
keeps the same xclbin, packet format, quantization, scale retry policy and FPGA
transactions, but removes two host-side allocation patterns measured as the
largest remaining software cost:

* reconstructing FP16 lanes through two temporary byte copies;
* growing sparse 32-token output arrays for every descriptor and concatenating
  27 independently allocated T32 results.

One final family output is allocated once and each DMA result is decoded
directly into its non-overlapping token slice.
"""

from __future__ import annotations

import time
from collections import defaultdict

import numpy as np

import board_runtime as base
from m230_prefill_runtime import M230PrefillRuntime


def _half_values_strided(raw: memoryview) -> np.ndarray:
    """Return the two FP16 payload lanes in every 64-bit output word as FP32.

    Each word stores useful half values at byte offsets 0 and 4.  A strided
    view avoids the accepted parser's two byte copies and temporary packed
    array.  ``astype`` is the only required materialization.
    """
    if len(raw) % 8:
        raise RuntimeError("FPGA output payload is not an integral number of 64-bit words")
    octets = np.frombuffer(raw, dtype=np.uint8)
    lanes = np.ndarray(
        shape=(len(raw) // 8, 2),
        dtype="<f2",
        buffer=octets,
        strides=(8, 4),
    )
    return lanes.astype(np.float32)


def _output_widths(chain: dict) -> dict[str, int]:
    widths: dict[str, int] = {}
    for descriptor in chain["descriptors"]:
        name = descriptor.get("module", "lm_head")
        stop = int(descriptor["row_start"]) + int(descriptor["valid_rows"])
        widths[name] = max(widths.get(name, 0), stop)
    if not widths:
        raise RuntimeError("chain has no output descriptors")
    return widths


class M231PrefillRuntime(M230PrefillRuntime):
    """M230 plus direct-to-final-buffer parsing for multi-T32 families."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.family_output_allocations = defaultdict(int)
        self.parse_temporary_result_dicts = 0

    @staticmethod
    def _parse_into(
        chain: dict,
        payload: bytes | bytearray | memoryview,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
        output_scale_shift: int,
    ) -> None:
        if not isinstance(output_scale_shift, int) or not 0 <= output_scale_shift <= 10:
            raise ValueError("output_scale_shift must be an integer in [0, 10]")
        if token_count < 1 or token_count > 32:
            raise ValueError("token_count must be in [1, 32]")
        raw = memoryview(payload)
        if len(raw) != int(chain["output_bytes"]):
            raise RuntimeError(
                f"output packet size mismatch: {len(raw)} != {chain['output_bytes']}"
            )

        cursor = 0
        for descriptor in chain["descriptors"]:
            size = int(descriptor["output_bytes"])
            values = _half_values_strided(raw[cursor:cursor + size])
            cursor += size
            rows = int(descriptor["rows_per_shard"])
            blocks = rows // 8
            values = values.reshape(blocks, 32, 4, 4, 2)
            assembled = values.transpose(1, 2, 0, 3, 4).reshape(32, 4 * rows)
            if output_scale_shift:
                assembled = np.ldexp(assembled, -output_scale_shift).astype(np.float32)
            valid = int(descriptor["valid_rows"])
            name = descriptor.get("module", "lm_head")
            row_start = int(descriptor["row_start"])
            row_stop = row_start + valid
            if name not in targets or targets[name].shape[1] < row_stop:
                raise RuntimeError(f"preallocated target is incomplete for {name}")
            targets[name][token_start:token_start + token_count, row_start:row_stop] = (
                assembled[:token_count, :valid]
            )
        if cursor != len(raw):
            raise RuntimeError("output cursor mismatch")

    @staticmethod
    def _written_slice_finite(
        chain: dict,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
    ) -> bool:
        checked = 0
        for descriptor in chain.get("descriptors", []):
            name = descriptor.get("module", "lm_head")
            if name not in targets:
                return False
            row_start = int(descriptor["row_start"])
            valid = int(descriptor["valid_rows"])
            row_stop = row_start + valid
            values = targets[name]
            if values.ndim != 2 or valid <= 0 or values.shape[1] < row_stop:
                return False
            if not np.isfinite(
                values[token_start:token_start + token_count, row_start:row_stop]
            ).all():
                return False
            checked += token_count * valid
        return checked > 0

    def _execute_into(
        self,
        chain: dict,
        values: np.ndarray,
        buffers: list,
        targets: dict[str, np.ndarray],
        token_start: int,
        token_count: int,
        descriptor_offset_base_words: int = 0,
    ) -> None:
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
            self.dma.recvchannel.transfer(self.output_buffer, nbytes=output_bytes)
            self.kernel.write(base.REG_AP_CTRL, 1)
            self.dma.sendchannel.transfer(self.input_buffer, nbytes=input_bytes)
            snapshot = base.wait_transaction(self.kernel, self.dma, 10.0)
            self._record_phase(chain, "launch_wait", started)

            returned = int(snapshot["ap_return"])
            if returned != base.BUILD_ID:
                raise RuntimeError(f"M120/M89X2 build/status mismatch: 0x{returned:08x}")

            started = time.perf_counter()
            self.output_buffer.sync_from_device()
            self._record_phase(chain, "output_sync", started)
            self.host_calls += 1
            self.expected_macros += int(chain["expected_macros"])
            attempted.append(shift)

            started = time.perf_counter()
            self._parse_into(
                chain,
                memoryview(self.output_buffer)[:output_bytes],
                targets,
                token_start,
                token_count,
                shift,
            )
            self._record_phase(chain, "parse", started)
            if self._written_slice_finite(
                chain, targets, token_start, token_count
            ):
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
                    "input_max_abs": float(
                        np.max(np.abs(np.asarray(values, dtype=np.float32)))
                    ),
                })
                return

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
        for token_start in range(0, array.shape[0], 32):
            token_count = min(32, array.shape[0] - token_start)
            self._execute_into(
                chain,
                array[token_start:token_start + token_count],
                buffers,
                targets,
                token_start,
                token_count,
                base_words,
            )
            self.family_t32_blocks[self._family_key(chain)] += 1
        if not all(np.isfinite(value).all() for value in targets.values()):
            raise RuntimeError("M231 family output contains unfilled rows")
        return targets

    def evidence(self) -> dict:
        result = super().evidence()
        result.update({
            "prefill_scheduler": "m231-family-stage-once-direct-final-buffer-t32",
            "fpga_transaction_contract_changed": False,
            "model_math_changed": False,
            "output_parser": "strided-fp16-view-direct-final-buffer-v1",
            "family_output_allocations": dict(self.family_output_allocations),
            "parse_temporary_result_dicts": self.parse_temporary_result_dicts,
        })
        return result
