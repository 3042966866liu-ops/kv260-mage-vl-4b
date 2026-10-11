"""Synthetic contract tests ONLY; no model/board performance is measured."""
import tempfile
from pathlib import Path
import unittest
from measurement import TokenTrace, exclusive_lock, summarize_requests, write_json


class Clock:
    def __init__(self):
        self.ns = 0
    def __call__(self):
        return self.ns
    def at(self, seconds):
        self.ns = int(seconds * 1e9)


class MeasurementTests(unittest.TestCase):
    def run_trace(self, ids, reason='length', **kwargs):
        clock = Clock()
        trace = TokenTrace([99], [0], clock)
        for index, token in enumerate(ids):
            clock.at(index + 2)
            trace.token_ready(token, synchronized=True)
        clock.at(len(ids) + 2)
        trace.stage('request', 0, clock.ns)
        return trace.finish(reason, **kwargs)

    def test_known_events(self):
        r = self.run_trace([1, 2, 3])
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual((r['ttft_s'], r['decode_tps'], r['answer_latency_s']), (2, 1, 4))

    def test_zero_and_one(self):
        self.assertIsNone(self.run_trace([])['decode_tps'])
        self.assertEqual(self.run_trace([])['status'], 'FAIL')
        self.assertIsNone(self.run_trace([1])['decode_tps'])

    def test_eos_pad_not_throughput(self):
        r = self.run_trace([0, 1, 2, 99], 'eos')
        self.assertEqual(r['output_tokens'], 2)
        self.assertEqual(r['decode_tps'], 1)
        self.assertEqual(r['raw_output_tokens'], 4)
        self.assertEqual(self.run_trace([99], 'eos')['status'], 'FAIL')

    def test_failures_retained(self):
        for kwargs in ({'finite': False}, {'cpu_linear_fallback': True}, {'cpu_linear_fallback': None}, {'error': 'device error'}):
            self.assertEqual(self.run_trace([1, 2], **kwargs)['status'], 'FAIL')
        self.assertEqual(self.run_trace([1], 'timeout')['status'], 'FAIL')

    def test_no_128_claim_for_early_eos(self):
        self.assertFalse(self.run_trace([1, 2, 99], 'eos')['valid_128_tokens'])
        self.assertTrue(self.run_trace([1] * 128)['valid_128_tokens'])

    def test_unsynchronized_rejected(self):
        with self.assertRaises(ValueError):
            TokenTrace([99]).token_ready(1, synchronized=False)

    def test_after_eos_rejected(self):
        trace = TokenTrace([99])
        trace.token_ready(99, synchronized=True)
        with self.assertRaises(ValueError):
            trace.token_ready(1, synchronized=True)

    def test_overlap_and_gap_rejected(self):
        for intervals in ([(0, 2), (1, 3)], [(0, 1)]):
            clock = Clock()
            trace = TokenTrace([99], clock=clock)
            clock.at(2)
            trace.token_ready(1, synchronized=True)
            for a, b in intervals:
                trace.stage('phase', int(a * 1e9), int(b * 1e9))
            clock.at(3)
            self.assertEqual(trace.finish('length')['status'], 'FAIL')

    def test_non_monotonic_rejected(self):
        clock = Clock()
        trace = TokenTrace([99], clock=clock)
        clock.at(-1)
        with self.assertRaises(ValueError):
            trace.token_ready(1, synchronized=True)

    def test_nearest_rank_and_request_median(self):
        rows = [dict(status='PASS', ttft_s=i, decode_tps=i) for i in range(1, 11)]
        rows.append(dict(status='FAIL', ttft_s=None, decode_tps=None))
        r = summarize_requests(rows)
        self.assertEqual(r['ttft_s']['median'], 5.5)
        self.assertEqual(r['ttft_s']['p90'], 9)
        self.assertEqual(r['failed_requests'], 1)
        self.assertIsNone(r['formal_level'])

    def test_nonfinite_json_preserves_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.json'
            write_json(path, {'a': 1})
            old = path.read_bytes()
            with self.assertRaises(ValueError):
                write_json(path, {'a': float('nan')})
            self.assertEqual(path.read_bytes(), old)

    def test_lock_excludes_and_releases_on_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'board.lock'
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                with exclusive_lock(path):
                    with self.assertRaises(FileExistsError):
                        with exclusive_lock(path):
                            self.fail('second writer admitted')
                    raise RuntimeError('injected')
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
