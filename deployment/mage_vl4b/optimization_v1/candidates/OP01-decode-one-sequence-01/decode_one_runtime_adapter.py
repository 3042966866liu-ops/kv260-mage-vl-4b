"""Decode-only adapter retaining M238 packing/parsing/retries and wire sizes.

The caller must load an isolated candidate board_runtime module (Build-ID and
kernel name derived from the pinned stable source). Never mutate stable files.
"""
from contextlib import contextmanager
from decode_one_policy import CANDIDATE_BUILD_ID, execution_config


def runtime_class(parent, base):
    if base.BUILD_ID != CANDIDATE_BUILD_ID:
        raise ValueError('Candidate runtime identity required')

    class DecodeOneRuntime(parent):
        _decode_scope = False

        @contextmanager
        def _one_token(self, values):
            if len(values.shape) != 2 or values.shape[0] != 1:
                raise ValueError('Decode-only runtime requires exactly one token')
            if self._decode_scope:
                raise RuntimeError('Concurrent/nested decode dispatch rejected')
            self._decode_scope = True
            try:
                yield
            finally:
                self._decode_scope = False

        def language_family_many(self, layer, family, values):
            with self._one_token(values):
                return super().language_family_many(layer, family, values)

        def _execute(self, chain, values, buffers, descriptor_offset_base_words=0):
            # LM Head uses the parent's _execute; language retries remain inside
            # language_family_many and pass through _program_static_registers.
            with self._one_token(values):
                return super()._execute(chain, values, buffers, descriptor_offset_base_words)

        def _program_static_registers(self, chain, buffers):
            if not self._decode_scope:
                raise RuntimeError('No validated single-token scope')
            modified = dict(chain)
            config = execution_config(int(chain['config_u32'], 16),
                build_id=base.BUILD_ID, phase='decode', valid_tokens=1)
            modified['config_u32'] = hex(config)
            return super()._program_static_registers(modified, buffers)

        def evidence(self):
            result = super().evidence()
            result.update(decode_one_enabled=True, build_id='0x4F503131',
                          capacity_status='STOPPED_BY_USER_NOT_PASS', formal_promotion_allowed=False,
                          expected_macros_scope='Inherited T32 accounting, not executed MAC count')
            return result

    return DecodeOneRuntime
