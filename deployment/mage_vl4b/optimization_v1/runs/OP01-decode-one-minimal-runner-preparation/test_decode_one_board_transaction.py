"""Fake-device lifecycle tests, not FPGA execution or measured speed."""
import unittest
from types import SimpleNamespace
import numpy as np
from decode_one_board_transaction import BoardTransaction
from decode_one_board_protocol import zero_transaction, CANDIDATE_BUILD


class Buffer(np.ndarray):
    def sync_to_device(self): pass
    def sync_from_device(self): pass
    def freebuffer(self): self.freed = True


class TransactionTests(unittest.TestCase):
    def make(self, *, mismatch=False, unsafe=False, allocation_fail=False):
        buffers = []
        def allocate(shape, dtype):
            if allocation_fail and len(buffers) == 2:
                raise RuntimeError('allocation failed')
            b = np.zeros(shape, dtype=dtype).view(Buffer)
            b.freed, b.device_address = False, 0x100000 + len(buffers)*0x10000
            buffers.append(b)
            return b
        def receive(buf, nbytes):
            if not mismatch:
                buf[:] = 0
        channel = SimpleNamespace(transfer=lambda *a, **kw: None)
        dma = SimpleNamespace(recvchannel=SimpleNamespace(transfer=receive), sendchannel=channel)
        state = dict(ap_ctrl=0 if unsafe else 4, mm2s_dmasr=0 if unsafe else 2, s2mm_dmasr=2,
                     ap_return=CANDIDATE_BUILD)
        def waiter(*a, **kw):
            if unsafe:
                raise TimeoutError('fake timeout')
            return {'ap_done_seen': True, 'observed_return': CANDIDATE_BUILD}
        tx = BoardTransaction(SimpleNamespace(write=lambda *a: None), dma, allocate,
                              lambda: state, waiter=waiter)
        return tx, buffers

    def test_complete_output_and_release(self):
        tx, buffers = self.make()
        result = tx.run(zero_transaction(build_id=CANDIDATE_BUILD), 'fake')
        self.assertEqual(result['status'], 'PASS_MINIMAL_TRANSACTION_ONLY')
        self.assertTrue(all(x.freed for x in buffers))
        self.assertFalse(tx.started)

    def test_wrong_output_fails_without_unsafe_free(self):
        tx, buffers = self.make(mismatch=True)
        with self.assertRaisesRegex(RuntimeError, 'output differs'):
            tx.run(zero_transaction(build_id=CANDIDATE_BUILD), 'fake')
        self.assertTrue(all(x.freed for x in buffers))
        self.assertEqual(tx.evidence['status'], 'FAIL')

    def test_timeout_retains_buffers_and_rejects_retry(self):
        tx, buffers = self.make(unsafe=True)
        fixture = zero_transaction(build_id=CANDIDATE_BUILD)
        with self.assertRaises(TimeoutError): tx.run(fixture, 'fake')
        self.assertTrue(tx.recovery_required)
        self.assertTrue(all(not x.freed for x in buffers))
        with self.assertRaisesRegex(RuntimeError, 'no retry'): tx.run(fixture, 'fake')

    def test_allocation_failure_before_dma_releases(self):
        tx, buffers = self.make(allocation_fail=True)
        with self.assertRaisesRegex(RuntimeError, 'allocation failed'):
            tx.run(zero_transaction(build_id=CANDIDATE_BUILD), 'fake')
        self.assertEqual(len(buffers), 2)
        self.assertTrue(all(x.freed for x in buffers))
        self.assertFalse(tx.recovery_required)


if __name__ == '__main__': unittest.main()
