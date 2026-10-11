"""Structural controller tests with fake model; not numerical/board proof."""
from types import SimpleNamespace
import unittest
import numpy as np
from causal_generation import generate, GenerationFailure
from measurement import TokenTrace


class TestClock:
    def __init__(self):
        self.ns = 0
    def __call__(self):
        self.ns += 100_000
        return self.ns


class Model:
    def __init__(self, eos_at=None, corrupt=False):
        self.eos_at, self.corrupt = eos_at, corrupt
        self.prefills = 0
        self.decodes = 0
        self.calls = 0
        self.cache_objects = []
    def output(self, step):
        token = 7 if step == self.eos_at else 1
        logits = np.zeros(8, np.float32)
        logits[token] = 1
        return token, logits
    def prefill(self, hidden):
        self.prefills += 1
        self.calls += int(np.ceil(len(hidden) / 32)) * 154 + 8
        self.step = 0
        cache = SimpleNamespace(keys=[np.zeros((len(hidden), 1, 2), np.float32) for _ in range(2)],
                                values=[np.zeros((len(hidden), 1, 2), np.float32) for _ in range(2)])
        self.cache_objects.append(cache)
        return (*self.output(0), cache)
    def decode(self, token, cache):
        self.decodes += 1
        self.calls += 162
        self.step += 1
        for index in range(2):
            cache.keys[index] = np.concatenate([cache.keys[index], np.zeros((1, 1, 2), np.float32)])
            cache.values[index] = np.concatenate([cache.values[index], np.zeros((1, 1, 2), np.float32)])
        if self.corrupt:
            cache.values[1] = cache.values[1][:-1]
        return self.output(self.step)


def run(model, count=8, **kwargs):
    kwargs.setdefault('cpu_linear_fallback', False)  # Fake backend contract only, no PL proof.
    return generate(model, np.ones((4, 3), np.float32), max_new_tokens=count,
                    trace=TokenTrace([7], clock=TestClock()),
                    layers=2, kv_heads=1, head_dim=2, vocab=8, eos_ids=(7,),
                    logical_calls_before=lambda: model.calls,
                    logical_calls_after=lambda: model.calls, **kwargs)


class CausalTests(unittest.TestCase):
    def test_missing_fallback_evidence_rejected(self):
        with self.assertRaisesRegex(GenerationFailure, 'missing proof'):
            run(Model(), cpu_linear_fallback=None)

    def test_actual_cpu_fallback_rejected(self):
        with self.assertRaisesRegex(GenerationFailure, 'CPU Linear fallback'):
            run(Model(), cpu_linear_fallback=True)

    def test_one_prefill_and_no_unused_final_forward(self):
        for count in (2, 8, 32, 128):
            model = Model()
            result = run(model, count)
            self.assertEqual(model.prefills, 1)
            self.assertEqual(model.decodes, count - 1)
            self.assertEqual(result['kv_lengths'], list(range(4, 4 + count)))
            self.assertEqual(result['output_tokens'], count)
            self.assertFalse(result['hardware_proof_verified'])

    def test_eos_forward_is_counted(self):
        model = Model(eos_at=2)
        result = run(model)
        self.assertEqual(result['output_tokens'], 2)
        self.assertEqual(result['raw_output_tokens'], 3)
        self.assertEqual(model.calls, 162 * 3)
        self.assertEqual(result['logical_calls_expected'], model.calls)
        self.assertFalse(result['valid_128_tokens'])

    def test_empty_eos_is_failure(self):
        with self.assertRaises(GenerationFailure) as error:
            run(Model(eos_at=0))
        self.assertEqual(error.exception.result['output_tokens'], 0)

    def test_corrupt_cache_fails_without_restart(self):
        model = Model(corrupt=True)
        with self.assertRaises(GenerationFailure) as error:
            run(model)
        self.assertEqual(model.prefills, 1)
        self.assertEqual(model.decodes, 1)
        self.assertIn('KV length/geometry', str(error.exception))

    def test_request_cache_isolation(self):
        model = Model()
        first = run(model)
        second = run(model)
        self.assertEqual(first['kv_lengths'], second['kv_lengths'])
        self.assertIsNot(model.cache_objects[0], model.cache_objects[1])

    def test_context_limit_fails_without_reprefill(self):
        model = Model()
        with self.assertRaises(GenerationFailure):
            run(model, max_context=5)
        self.assertEqual(model.prefills, 1)
        self.assertEqual(model.decodes, 1)

    def test_counter_failure_not_hidden(self):
        model = Model()
        original = model.decode
        def bad_decode(*args):
            result = original(*args)
            model.calls += 1
            return result
        model.decode = bad_decode
        with self.assertRaisesRegex(GenerationFailure, 'logical PL call'):
            run(model)

    def test_watchdog_does_not_change_threshold(self):
        with self.assertRaises(GenerationFailure) as error:
            run(Model(), request_timeout_s=1e-12)
        self.assertEqual(error.exception.result['finish_reason'], 'timeout')


if __name__ == '__main__':
    unittest.main()
