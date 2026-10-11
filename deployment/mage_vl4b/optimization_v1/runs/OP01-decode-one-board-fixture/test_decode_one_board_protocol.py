import unittest
from decode_one_board_protocol import (STABLE_BUILD, CANDIDATE_BUILD, DECODE_ONE_BIT, referenced_descriptor,
                                       zero_transaction, wait_transaction, TransactionFailure)


def state(build=CANDIDATE_BUILD, ctrl=6, idle=True):
    return dict(ap_ctrl=ctrl, ap_return=build, mm2s_dmasr=2, s2mm_dmasr=2,
                mm2s_idle=idle, s2mm_idle=idle, mm2s_error=False, s2mm_error=False)


class ProtocolTests(unittest.TestCase):
    def test_referenced_descriptor_modes(self):
        for mode in (False,True):
            fixture=referenced_descriptor(decode_one=mode)
            self.assertEqual(len(fixture['packet']),2576)
            self.assertEqual(len(fixture['weights']),64*17*16)
            self.assertEqual(len(fixture['expected_output']),32768*8)
            words=[int.from_bytes(fixture['expected_output'][i:i+8],'little')
                   for i in range(0,len(fixture['expected_output']),8)]
            self.assertEqual(sum(w!=0 for w in words),1024 if mode else 32768)
            self.assertEqual(set(words),{0,0x440000004400} if mode else {0x440000004400})

    def run_wait(self, frames, expected=CANDIDATE_BUILD):
        values=iter(frames)
        ticks=iter([0.0, 0.1, 0.2, 5.1, 5.2])
        last=frames[-1]
        return wait_transaction(lambda: next(values,last), expected_build=expected,
            identity='offline-fake-not-board', input_bytes=2576, output_bytes=4096,
            clock=lambda: next(ticks), sleep=lambda _: None)

    def test_packet_identity(self):
        a=zero_transaction(build_id=STABLE_BUILD)
        b=zero_transaction(build_id=CANDIDATE_BUILD,decode_one=True)
        self.assertEqual(a['packet'],b['packet'])
        self.assertEqual(len(a['packet']),2576)
        self.assertEqual(b['config']^a['config'],DECODE_ONE_BIT)
        self.assertEqual(b['weight_bytes_per_shard'],144)
        with self.assertRaises(ValueError): zero_transaction(build_id=STABLE_BUILD,decode_one=True)

    def test_candidate_and_stable(self):
        for build in (STABLE_BUILD,CANDIDATE_BUILD):
            self.assertEqual(self.run_wait([state(build)],build)['observed_return'],build)

    def test_wrong_identity_rejected(self):
        with self.assertRaises(TransactionFailure): self.run_wait([state(STABLE_BUILD)])

    def test_done_latched_until_dma_idle(self):
        result=self.run_wait([state(ctrl=2,idle=False),state(ctrl=4)])
        self.assertTrue(result['ap_done_seen'])
        self.assertEqual(result['observed_return'],CANDIDATE_BUILD)

    def test_timeout_and_diagnostics(self):
        with self.assertRaises(TransactionFailure) as caught:
            self.run_wait([state(ctrl=0,idle=False)])
        self.assertIn('timeout',str(caught.exception))
        self.assertEqual(caught.exception.evidence['input_bytes'],2576)

    def test_dma_raw_error_rejected(self):
        frame=state(); frame['s2mm_dmasr']=0x12
        with self.assertRaises(TransactionFailure): self.run_wait([frame])

    def test_unreadable_register_rejected(self):
        frame=state(); frame['ap_ctrl']=-1
        with self.assertRaises(TransactionFailure): self.run_wait([frame])

if __name__=='__main__': unittest.main()
