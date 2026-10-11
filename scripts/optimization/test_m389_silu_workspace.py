"""Synthetic Windows algorithm/lifetime checks, not real-video or A53 proof."""
import ast
import pathlib
import threading
import unittest
import numpy as np
from m389_silu_workspace import SiluWorkspace

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py'
node = next(n for n in ast.parse(SOURCE.read_text(encoding='utf-8')).body
            if isinstance(n, ast.FunctionDef) and n.name == 'silu')
env = {'np': np}
exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCE), 'exec'), env)
reference_silu = env['silu']
SHAPE = (159, 9728)


class Checks(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(389)
        self.gate = rng.uniform(-120, 120, SHAPE).astype(np.float32)
        self.up = rng.normal(size=SHAPE).astype(np.float32)
        self.work = SiluWorkspace(SHAPE, enabled=True)

    def equivalent(self, gate, up):
        before = (gate.tobytes(), up.tobytes())
        with np.errstate(all='ignore'):
            reference = reference_silu(gate) * up
            with self.work.lease(gate, up) as actual:
                self.assertEqual(reference.tobytes(), actual.tobytes())
                self.assertIs(actual, self.work._buffer)
        self.assertEqual(before, (gate.tobytes(), up.tobytes()))

    def test_real_size_synthetic_bits_and_input_immutability(self):
        self.equivalent(self.gate, self.up)

    def test_edges_signed_zero_subnormal_overflow(self):
        edge = np.array([0., -0., 1e-45, -1e-45, 88., -88., 1000., -1000.,
                         1e30, -1e30, np.inf, -np.inf, np.nan], dtype=np.float32)
        self.gate.flat[:edge.size] = edge
        self.up.flat[:edge.size] = edge[::-1]
        self.equivalent(self.gate, self.up)

    def test_noncontiguous_readonly_inputs(self):
        self.gate.flags.writeable = self.up.flags.writeable = False
        self.equivalent(self.gate[:, ::-1], self.up[:, ::-1])

    def test_repeated_same_buffer(self):
        identity = id(self.work._buffer)
        for _ in range(3):
            self.equivalent(self.gate, self.up)
            self.assertEqual(identity, id(self.work._buffer))
        self.work.close()
        self.assertIsNone(self.work._buffer)

    def test_nested_and_cross_thread_consumer_rejected(self):
        errors = []
        def other():
            try:
                with self.work.lease(self.gate, self.up):
                    pass
            except RuntimeError:
                errors.append(True)
        with self.work.lease(self.gate, self.up):
            self.assertRaises(RuntimeError, self.work.close)
            t = threading.Thread(target=other)
            t.start(); t.join()
            self.assertEqual(errors, [True])

    def test_consumer_exception_retains_and_refuses_reuse_free(self):
        identity = id(self.work._buffer)
        with self.assertRaisesRegex(RuntimeError, 'consumer'):
            with self.work.lease(self.gate, self.up):
                raise RuntimeError('consumer')
        self.assertEqual(identity, id(self.work._buffer))
        self.assertTrue(self.work._retained)
        self.assertRaises(RuntimeError, self.work.close)
        with self.assertRaises(RuntimeError):
            with self.work.lease(self.gate, self.up):
                pass

    def test_dtype_shape_and_alias_fail_before_arithmetic(self):
        for bad in (self.gate.astype(np.float64), self.gate[:30], self.work._buffer):
            with self.assertRaises(ValueError):
                with self.work.lease(bad, self.up):
                    pass
            self.assertFalse(self.work._active)

    def test_default_disabled_and_closed(self):
        self.assertRaises(RuntimeError, SiluWorkspace, SHAPE)
        self.assertRaises(ValueError, SiluWorkspace, (30, 9728), enabled=True)
        self.work.close()
        with self.assertRaises(RuntimeError):
            with self.work.lease(self.gate, self.up):
                pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
