from types import SimpleNamespace
import unittest
from op01_support import guarded_close_board,compact_summary


class CleanupTests(unittest.TestCase):
    def board(self):
        self.calls=[]
        return SimpleNamespace(kernel=object(),dma=object(),close=lambda:self.calls.append('close'))
    def test_unlaunched_partial_constructor(self):
        b=self.board();del b.kernel;del b.dma
        r=guarded_close_board(b,lambda *a:self.fail('Unlaunched has no DMA ownership'),False)
        self.assertTrue(r['buffers_released']);self.assertEqual(self.calls,['close'])
    def test_active_or_unknown_dma_retained(self):
        for state in ({},dict(ap_ctrl=0,mm2s_dmasr=2,s2mm_dmasr=2),dict(ap_ctrl=4,mm2s_dmasr=2,s2mm_dmasr=0)):
            b=self.board();r=guarded_close_board(b,lambda *a:state,True)
            self.assertTrue(r['recovery_required']);self.assertEqual(self.calls,[])
    def test_snapshot_exception_retained(self):
        b=self.board()
        def fail(*a):raise OSError('MMIO unavailable')
        r=guarded_close_board(b,fail,True)
        self.assertTrue(r['recovery_required']);self.assertEqual(self.calls,[])
    def test_idle_closed(self):
        b=self.board();r=guarded_close_board(b,lambda *a:dict(ap_ctrl=4,mm2s_dmasr=4098,s2mm_dmasr=4098),True)
        self.assertTrue(r['buffers_released']);self.assertFalse(r['errors'])
    def test_cleanup_error_is_evidence(self):
        def fail():raise RuntimeError('free failed')
        r=guarded_close_board(SimpleNamespace(close=fail),None,False)
        self.assertIn('free failed',r['errors'][0]);self.assertFalse(r['buffers_released'])
    def test_uart_excludes_duplicate_large_arrays(self):
        r=compact_summary(dict(transactions=[1],board_evidence={'scale_attempts':[1]},
            request=dict(status='PASS',board_after={'scale_attempts':[1]},board_before={},input_token_ids=[1])))
        self.assertEqual(r,dict(request=dict(status='PASS')))
