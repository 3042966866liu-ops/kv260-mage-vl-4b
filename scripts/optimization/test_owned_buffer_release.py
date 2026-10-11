"""Explicit fake backend tests of destructor idempotence and unsafe retention."""
import unittest
from owned_buffer_release import OwnedBufferRelease


class ReleaseTests(unittest.TestCase):
    def test_close_then_destructor_after_device_teardown(self):
        events = []
        def safe():
            events.append('proof')
            return True
        hook = OwnedBufferRelease(lambda: events.append('free'), safe,
                                  lambda: events.append('record'))
        class FakeBuffer:
            def freebuffer(self): hook()
            def __del__(self): self.freebuffer()
        buffer = FakeBuffer()
        buffer.freebuffer()
        hook._safe = lambda: self.fail('Destructor read device after teardown')
        buffer.__del__()
        buffer.freebuffer()
        self.assertEqual(events, ['proof', 'free', 'record'])
        del buffer

    def test_busy_or_missing_proof_never_frees(self):
        for proof in (False, None, 1):
            hook = OwnedBufferRelease(lambda: self.fail('Unsafe free'), lambda: proof,
                                      lambda: self.fail('Unsafe ledger'))
            with self.assertRaisesRegex(RuntimeError, 'safety'): hook()
            self.assertEqual(hook.state, 'owned')

    def test_failed_backend_not_retried(self):
        calls = []
        def failed():
            calls.append('attempt')
            raise OSError('Backend result ambiguous')
        hook = OwnedBufferRelease(failed, lambda: True, lambda: self.fail('Wrong ledger'))
        with self.assertRaises(OSError): hook()
        with self.assertRaisesRegex(RuntimeError, 'unresolved'): hook()
        self.assertEqual(calls, ['attempt'])
        self.assertEqual(hook.state, 'unresolved')

    def test_safety_reader_exception_retains(self):
        def failed(): raise OSError('Device unreadable')
        hook = OwnedBufferRelease(lambda: self.fail('Unsafe free'), failed, lambda: None)
        with self.assertRaises(OSError): hook()
        self.assertEqual(hook.state, 'owned')

    def test_reentrant_backend_call_refused(self):
        def backend():
            with self.assertRaisesRegex(RuntimeError, 'unresolved'): hook()
        hook = OwnedBufferRelease(backend, lambda: True, lambda: None)
        hook()
        self.assertEqual(hook.state, 'released')

    def test_ledger_failure_cannot_repeat_backend(self):
        calls = []
        def failed(): raise OSError('Ledger unavailable')
        hook = OwnedBufferRelease(lambda: calls.append('free'), lambda: True, failed)
        with self.assertRaises(OSError): hook()
        hook()
        self.assertEqual(calls, ['free'])
        self.assertEqual(hook.state, 'released')


if __name__ == '__main__': unittest.main()
