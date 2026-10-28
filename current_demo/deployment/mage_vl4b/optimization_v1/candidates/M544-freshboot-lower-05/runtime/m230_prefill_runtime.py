#!/usr/bin/env python3
"""M230 profiled T32 runtime with family-scoped weight staging.

This is an isolated candidate layered on the accepted M120/M89-X2 runtime.
It deliberately preserves the T32 packet, quantization, FPGA arithmetic and
output parsing contracts.  The only scheduling change is that one staged
weight window serves every T32 block belonging to the same language family.
"""

from __future__ import annotations

import time
from collections import defaultdict

import numpy as np

import board_runtime as base


PHASES = (
    "pack",
    "input_copy",
    "input_sync",
    "register_setup",
    "launch_wait",
    "output_sync",
    "parse",
)


class M230PrefillRuntime(base.M120BoardRuntime):
    """Accepted M120 runtime plus transparent profiling and stage-once batching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase_ms = {name: 0.0 for name in PHASES}
        self.phase_calls = {name: 0 for name in PHASES}
        self.family_phase_ms = defaultdict(lambda: {name: 0.0 for name in PHASES})
        self.family_t32_blocks = defaultdict(int)
        self.family_stage_count = defaultdict(int)
        self._programmed_weight_addresses = None
        self._programmed_config = None

    @staticmethod
    def _family_key(chain: dict) -> str:
        layer = chain.get("layer")
        return f"{layer if layer is not None else 'head'}:{chain.get('family', 'lm_head')}"

    def _record_phase(self, chain: dict, phase: str, started: float) -> None:
        elapsed = (time.perf_counter() - started) * 1000.0
        self.phase_ms[phase] += elapsed
        self.phase_calls[phase] += 1
        self.family_phase_ms[self._family_key(chain)][phase] += elapsed

    def _program_static_registers(self, chain: dict, buffers: list) -> None:
        addresses = tuple(base.physical_address(buffer) for buffer in buffers)
        config = int(chain["config_u32"], 16)
        if addresses != self._programmed_weight_addresses:
            for register, address in zip(base.REG_POINTERS, addresses):
                base.write_u64(self.kernel, register, address)
            self._programmed_weight_addresses = addresses
        if config != self._programmed_config:
            self.kernel.write(base.REG_CONFIG, config)
            self._programmed_config = config

    def _execute(self, chain: dict, values: np.ndarray, buffers: list,
                 descriptor_offset_base_words: int = 0) -> dict[str, np.ndarray]:
        """Execute the unchanged M120 transaction while measuring every host phase."""
        output_bytes = int(chain["output_bytes"])
        initial_shift = self._initial_scale_shift(values)
        attempted = []
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
            outputs = base.parse_chain_output(
                chain,
                memoryview(self.output_buffer)[:output_bytes],
                output_scale_shift=shift,
            )
            self._record_phase(chain, "parse", started)
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

    def _language_chain(self, layer: int, family: str) -> dict:
        matches = [
            chain
            for chain in self.language_contract.chains
            if int(chain["layer"]) == int(layer) and chain["family"] == family
        ]
        if len(matches) != 1:
            raise RuntimeError(f"language chain lookup failed: layer={layer} family={family}")
        return matches[0]

    def language_family(self, layer: int, family: str,
                        values: np.ndarray) -> dict[str, np.ndarray]:
        """Transparent drop-in entry: every caller receives stage-once scheduling."""
        return self.language_family_many(layer, family, values)

    def language_family_many(self, layer: int, family: str,
                             values: np.ndarray) -> dict[str, np.ndarray]:
        """Run all T32 blocks for one family after staging its weights once."""
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

        assembled: dict[str, list[np.ndarray]] = {}
        for start in range(0, array.shape[0], 32):
            count = min(32, array.shape[0] - start)
            update = self._execute(
                chain,
                array[start:start + count],
                buffers,
                base_words,
            )
            self.family_t32_blocks[self._family_key(chain)] += 1
            for name, value in update.items():
                assembled.setdefault(name, []).append(np.asarray(value[:count], dtype=np.float32))
        return {name: np.concatenate(chunks, axis=0) for name, chunks in assembled.items()}

    def evidence(self) -> dict:
        result = super().evidence()
        result.update({
            "prefill_scheduler": "m230-family-stage-once-t32",
            "fpga_transaction_contract_changed": False,
            "model_math_changed": False,
            "phase_ms": dict(self.phase_ms),
            "phase_calls": dict(self.phase_calls),
            "family_phase_ms": {key: dict(value) for key, value in self.family_phase_ms.items()},
            "family_t32_blocks": dict(self.family_t32_blocks),
            "family_stage_count": dict(self.family_stage_count),
            "static_weight_pointer_register_cache": True,
            "static_config_register_cache": True,
        })
        return result
