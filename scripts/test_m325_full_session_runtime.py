"""Small host-only checks for OP01 phase gating before board execution."""

import unittest

from m325_full_session_runtime import candidate_runtime_class


class FakeBase:
    BUILD_ID = 0x4F503131


class FakeParent:
    def language_family_many(self, layer, family, values):
        return (layer, family, values.shape)

    def _execute(self, chain, values, buffers, descriptor_offset_base_words=0):
        return (chain, values.shape)

    def _program_static_registers(self, chain, buffers):
        return chain

    def evidence(self):
        return {"build_id": "0x4f503131"}


class Values:
    def __init__(self, rows):
        self.shape = (rows, 2560)


def checked_config(config, *, build_id, phase, valid_tokens):
    assert build_id == FakeBase.BUILD_ID
    assert phase in ("prefill", "decode")
    assert valid_tokens == (1 if phase == "decode" else 32)
    return config | ((1 << 24) if phase == "decode" else 0)


class PhaseTests(unittest.TestCase):
    def setUp(self):
        runtime = candidate_runtime_class(FakeParent, FakeBase, checked_config)
        self.board = runtime()
        self.chain = {"config_u32": "0x10401"}

    def test_prefill_keeps_t32_protocol(self):
        with self.board.phase("prefill"):
            self.board.language_family_many(0, "qkv", Values(32))
            result = self.board._program_static_registers(self.chain, [])
        self.assertEqual(result["config_u32"], self.chain["config_u32"])

    def test_decode_sets_op01_bit_only_for_one_token(self):
        with self.board.phase("decode"):
            self.board.language_family_many(0, "qkv", Values(1))
            result = self.board._program_static_registers(self.chain, [])
            with self.assertRaises(ValueError):
                self.board.language_family_many(0, "qkv", Values(2))
        self.assertEqual(int(result["config_u32"], 16), int(self.chain["config_u32"], 16) | (1 << 24))

    def test_calls_without_phase_are_rejected(self):
        with self.assertRaises(RuntimeError):
            self.board._program_static_registers(self.chain, [])


if __name__ == "__main__":
    unittest.main()
