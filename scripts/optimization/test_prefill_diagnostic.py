import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
import numpy as np

from prefill_diagnostic import PrefillDiagnostic


def rms_norm(x): return x
def apply_rope(x): return x
def causal_attention_grouped(x): return x
def silu(x): return x


class Runtime:
    def __init__(self, base, fail=False):
        self.base, self.fail = base, fail
        self.host_calls = self.logical_calls = self.stage_bytes = self.stage_ms = 0
        self.scale_retry_count = 0
        self.phase_ms = {'pack': 0.0}
    def _stage(self):
        self.base.chain_window()
        self.base.copy_window_to_buffer()
        self.stage_bytes += 16
    def _prepare_block(self, x): return x
    def _parse_buffer(self, x): return x.copy()
    def _parse_into_and_check(self, x): return x
    def _launch_once(self): pass
    def _launch_prepacked(self):
        self.base.wait_transaction()
        if self.fail: raise RuntimeError('device timeout')
        self.host_calls += 1
        self.logical_calls += 1
    def lm_head(self, x): return x[-1].copy()


class Model:
    def __init__(self, runtime): self.runtime = runtime
    def _family(self, layer, family, x):
        self.runtime._stage()
        with ThreadPoolExecutor(max_workers=1) as worker:
            prepared = worker.submit(self.runtime._prepare_block, x).result()
            self.runtime._launch_prepacked()
            return worker.submit(self.runtime._parse_buffer, prepared).result()
    def prefill(self, hidden):
        value = self._family(0, 'gate_up', rms_norm(hidden))
        value = silu(causal_attention_grouped(apply_rope(value)))
        cache = SimpleNamespace(keys=[value[:, None, :].copy()],
                                values=[value[:, None, :].copy()])
        self.returned = (3, self.runtime.lm_head(value), cache)
        return self.returned


class PrefillTests(unittest.TestCase):
    def case(self, fail=False, **kwargs):
        base = SimpleNamespace(chain_window=lambda: None,
                               copy_window_to_buffer=lambda: None,
                               wait_transaction=lambda: None)
        runtime = Runtime(base, fail)
        model = Model(runtime)
        diagnostic = PrefillDiagnostic(model, runtime, base,
            transfer_instrumenter=lambda *args: nullcontext(), **kwargs)
        return diagnostic, model, runtime, base

    def test_delegation_workers_and_restore(self):
        diagnostic, model, runtime, base = self.case()
        hidden = np.arange(12, dtype=np.float32).reshape(3, 4)
        result = diagnostic.prefill(hidden)
        self.assertIs(result, model.returned)
        np.testing.assert_array_equal(result[1], hidden[-1])
        self.assertNotIn('trace', diagnostic.record)
        report = diagnostic.finalize()
        events = report['trace']['events']
        self.assertEqual(report['counter_delta']['logical_calls'], 1)
        self.assertEqual(report['counter_delta']['stage_bytes'], 16)
        self.assertGreater(len({e['thread'] for e in events}), 1)
        self.assertFalse(report['cross_thread_addition_allowed'])
        for name in ('_stage', '_prepare_block', '_parse_buffer', '_launch_prepacked'):
            self.assertNotIn(name, vars(runtime))
        self.assertNotIn('_family', vars(model))
        self.assertEqual(base.wait_transaction.__name__, '<lambda>')
        with self.assertRaisesRegex(RuntimeError, 'one Prefill'):
            diagnostic.prefill(hidden)

    def test_failure_retained_and_global_restored(self):
        diagnostic, model, runtime, _ = self.case(fail=True)
        original = rms_norm
        with self.assertRaisesRegex(RuntimeError, 'device timeout'):
            diagnostic.prefill(np.ones((3, 4), np.float32))
        report = diagnostic.finalize()
        self.assertEqual(report['status'], 'FAIL')
        self.assertIs(rms_norm, original)
        self.assertNotIn('_family', vars(model))
        self.assertNotIn('_stage', vars(runtime))

    def test_event_overflow_fails_and_restores(self):
        from decode_trace import DecodeTrace
        diagnostic, model, runtime, _ = self.case(trace_factory=lambda: DecodeTrace(max_events=1))
        with self.assertRaisesRegex(RuntimeError, 'event bound'):
            diagnostic.prefill(np.ones((3, 4), np.float32))
        self.assertEqual(diagnostic.finalize()['status'], 'FAIL')
        self.assertNotIn('_family', vars(model))
        self.assertNotIn('_stage', vars(runtime))


if __name__ == '__main__': unittest.main()
