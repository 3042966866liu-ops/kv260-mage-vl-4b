"""Exercise actual pair entry with frozen parser/Futures and fake DMA/policy."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from m377_gate_up_pair import run_pair
from test_m376_gate_up_workers import FakeDMA,CHAIN

class Policy:
    def __init__(self):self.labels=[];self.started=False;self.stopped=False
    def capture(self,name,check):self.labels.append(name)
    def begin_sampling(self):self.started=True
    def stop_sampling(self):self.stopped=True

class Runtime(FakeDMA):
    def __init__(self):
        super().__init__(dict(CHAIN,groups=40),retry=True);self.stage_bytes=0
    def _stage(self,*args):self.stage_bytes+=4;return super()._stage(*args)

class Tests(unittest.TestCase):
    def test_original_dispatch_pair_outputs_retries_stats_and_restore(self):
        runtime=Runtime();policy=Policy();x=np.zeros((159,2560),np.float32);x[:,0]=np.arange(159)
        result=run_pair(runtime,policy,x)
        self.assertEqual(result['pairs'][0]['outputs'],result['pairs'][1]['outputs'])
        self.assertEqual(result['pairs'][0]['counts']['pipeline_retry_launches'],2)
        self.assertEqual(result['pairs'][0]['scope']['original_single_worker_dispatch'],True)
        self.assertEqual(result['pairs'][1]['scope']['gate_up_calls'],1)
        self.assertEqual(len(policy.labels),4);self.assertTrue(policy.started and policy.stopped)
        self.assertNotIn('language_family_many',vars(runtime));self.assertNotIn('_record_phase',vars(runtime))
    def test_scope_shape_rejected_before_sampling(self):
        p=Policy()
        with self.assertRaises(ValueError):run_pair(Runtime(),p,np.zeros((30,2560),np.float32))
        self.assertFalse(p.started)
    def test_count_mismatch_stops_sampling(self):
        class Broken(Runtime):
            def _emit(self,*args):
                super()._emit(*args);self.host_calls+=1
        p=Policy()
        with self.assertRaises(RuntimeError):run_pair(Broken(),p,np.zeros((159,2560),np.float32))
        self.assertTrue(p.stopped)

if __name__=='__main__':unittest.main()
