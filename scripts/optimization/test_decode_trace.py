import threading
import unittest
from decode_trace import DecodeTrace


class TraceTests(unittest.TestCase):
    def test_exclusive_closure(self):
        times=iter([0,10,30,40,70,100])
        trace=DecodeTrace(clock=lambda:next(times))
        with trace.span('decode'):
            with trace.span('prepare'):pass
            with trace.span('wait'):pass
        rows=trace.report()['events']
        self.assertEqual([r['exclusive_ns'] for r in rows],[50,20,30])
        self.assertEqual(sum(r['exclusive_ns'] for r in rows),100)

    def test_restore_and_identity(self):
        class Model:
            def decode(self, value):return value
        model=Model();trace=DecodeTrace();value=object()
        with trace.wrap(model,'decode'):
            self.assertIs(model.decode(value),value)
        self.assertNotIn('decode',vars(model))
        self.assertEqual(len(trace.report()['events']),1)

    def test_failure_preserved(self):
        trace=DecodeTrace()
        with self.assertRaisesRegex(ValueError,'original'):
            with trace.span('wait'):raise ValueError('original')
        self.assertTrue(trace.report()['events'][0]['failed'])

    def test_worker_separate_root(self):
        trace=DecodeTrace()
        def worker():
            with trace.span('pack'):pass
        with trace.span('decode'):
            thread=threading.Thread(target=worker);thread.start();thread.join()
        rows=trace.report()['events']
        self.assertIsNone(rows[1]['parent'])
        self.assertNotEqual(rows[0]['thread'],rows[1]['thread'])
        self.assertFalse(trace.report()['cross_thread_addition_allowed'])

    def test_bound_and_live(self):
        trace=DecodeTrace(max_events=1)
        with trace.span('one'):
            with self.assertRaises(RuntimeError):trace.report()
            with self.assertRaises(RuntimeError):
                with trace.span('two'):pass
        self.assertEqual(len(trace.report()['events']),1)


if __name__=='__main__':unittest.main()
