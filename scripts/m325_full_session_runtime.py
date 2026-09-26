"""Explicit T32 Prefill and single-token Decode policy for OP01.

The calling process imports M238 only after binding ``board_runtime`` to the
hash-checked OP01 candidate base.  No stable runtime file is modified.
"""

from contextlib import contextmanager


def candidate_runtime_class(parent, base, execution_config):
    if base.BUILD_ID != 0x4F503131:
        raise ValueError("OP01 candidate Build-ID required")

    class FullSessionRuntime(parent):
        _m325_phase = None

        @contextmanager
        def phase(self, name):
            if name not in ("prefill", "decode") or self._m325_phase is not None:
                raise ValueError("one explicit model phase required")
            self._m325_phase = name
            try:
                yield
            finally:
                self._m325_phase = None

        def language_family_many(self, layer, family, values):
            if self._m325_phase not in ("prefill", "decode"):
                raise RuntimeError("language call outside model phase")
            if self._m325_phase == "decode" and values.shape[0] != 1:
                raise ValueError("Decode-one requires exactly one token")
            return super().language_family_many(layer, family, values)

        def _execute(self, chain, values, buffers, descriptor_offset_base_words=0):
            if self._m325_phase not in ("prefill", "decode"):
                raise RuntimeError("LM Head call outside model phase")
            if self._m325_phase == "decode" and values.shape[0] != 1:
                raise ValueError("Decode-one LM Head requires one token")
            return super()._execute(chain, values, buffers, descriptor_offset_base_words)

        def _program_static_registers(self, chain, buffers):
            if self._m325_phase not in ("prefill", "decode"):
                raise RuntimeError("register setup outside model phase")
            modified = dict(chain)
            # The active-token count is only a guard in execution_config.  T32
            # Prefill retains the legacy config, including its final short tile.
            count = 1 if self._m325_phase == "decode" else 32
            modified["config_u32"] = hex(execution_config(
                int(chain["config_u32"], 16), build_id=base.BUILD_ID,
                phase=self._m325_phase, valid_tokens=count))
            return super()._program_static_registers(modified, buffers)

        def evidence(self):
            value = super().evidence()
            value.update(decode_one_enabled=True,
                         capacity_status="STOPPED_BY_USER_NOT_PASS",
                         formal_promotion_allowed=False)
            return value

    return FullSessionRuntime
