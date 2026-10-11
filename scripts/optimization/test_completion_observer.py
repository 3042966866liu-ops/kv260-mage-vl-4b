import unittest
from completion_observer import BUILD_ID, ObservationFailure, wait_observed


def snap(ap=0,m=False,s=False,**changes):
    value=dict(ap_ctrl=ap,ap_return=BUILD_ID,mm2s_dmasr=2 if m else 0,s2mm_dmasr=2 if s else 0,
        mm2s_idle=m,s2mm_idle=s,mm2s_error=False,s2mm_error=False,
        kernel_read_error='',return_read_error='',dma_read_error='')
    value.update(changes)
    return value


class ObserverTests(unittest.TestCase):
    def run_case(self,rows,**kw):
        t=[1000];calls=[];rows=iter(rows)
        def now(): t[0]+=1000;return t[0]
        def read():
            calls.append(1)
            return next(rows)
        result=wait_observed(read,1000,clock=now,sleeper=lambda _:None,**kw)
        self.assertEqual(result[1]['polls'],len(calls))
        return result

    def test_clear_on_read_latched_until_output_done(self):
        _,r=self.run_case([snap(),snap(2,True,False),snap(4,True,True)])
        self.assertTrue(r['events']['ap_done']['clear_on_read_latched'])
        self.assertEqual(r['polls'],3)
        self.assertEqual(r['dma_timing_unresolved'],[])

    def test_first_poll_complete_initial_idle_unresolved(self):
        _,r=self.run_case([snap(6,True,True)])
        self.assertEqual(r['dma_timing_unresolved'],['mm2s','s2mm'])
        self.assertTrue(r['completion_proven'])

    def test_initial_idle_without_done_not_completion(self):
        _,r=self.run_case([snap(4,True,True),snap(),snap(6,True,True)])
        self.assertEqual(r['polls'],3)

    def test_output_before_input(self):
        _,r=self.run_case([snap(),snap(0,False,True),snap(6,True,True)])
        self.assertLess(r['events']['s2mm']['observed_ns'],r['events']['mm2s']['observed_ns'])

    def test_submit_dma_busy_read_proves_fast_transfer(self):
        _,r=self.run_case([snap(6,True,True)],initial_busy={'mm2s':dict(before_ns=1100,after_ns=1200),'s2mm':dict(before_ns=1300,after_ns=1400)})
        self.assertEqual(r['dma_timing_unresolved'],[])

    def test_input_before_kernel(self):
        _,r=self.run_case([snap(),snap(0,True,False),snap(6,True,True)])
        self.assertLess(r['events']['mm2s']['observed_ns'],r['events']['ap_done']['observed_ns'])

    def test_return_mismatch(self):
        with self.assertRaisesRegex(ObservationFailure,'Build'):
            self.run_case([snap(6,True,True,ap_return=0)])

    def test_read_errors(self):
        for field in ('kernel_read_error','return_read_error','dma_read_error'):
            with self.assertRaises(ObservationFailure):self.run_case([snap(**{field:'read failed'})])

    def test_unknown_state(self):
        for field,value in (('ap_ctrl',-1),('ap_ctrl',True),('mm2s_idle',None),('s2mm_error',None)):
            with self.assertRaises(ObservationFailure):self.run_case([snap(**{field:value})])

    def test_dma_error_bit(self):
        with self.assertRaisesRegex(ObservationFailure,'DMA error'):
            self.run_case([snap(mm2s_dmasr=0x10)])

    def test_active_timeout_retains_snapshot(self):
        with self.assertRaises(ObservationFailure) as caught:self.run_case([snap()],timeout_s=0)
        self.assertEqual(caught.exception.evidence['last_snapshot']['ap_ctrl'],0)
        self.assertFalse(caught.exception.evidence.get('completion_proven',False))

    def test_intervals_contain_observation_and_gap(self):
        _,r=self.run_case([snap(),snap(6,True,True)])
        self.assertGreater(r['max_poll_gap_ns'],0)
        for event in r['events'].values():self.assertLessEqual(event['lower_ns'],event['upper_ns'])

    def test_done_interval_starts_before_prior_snapshot_not_after(self):
        _,r=self.run_case([snap(),snap(6,True,True)])
        self.assertEqual(r['events']['ap_done']['lower_ns'],3000)


if __name__=='__main__':unittest.main()
