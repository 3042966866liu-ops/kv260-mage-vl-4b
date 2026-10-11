import unittest
import numpy as np
from lifecycle_trial import run_trial

class Tests(unittest.TestCase):
    def arguments(self):
        self.calls=[]
        def restore():self.calls.append('restore');return 1291,object()
        def prepare():self.calls.append('prepare');return {'passes':2}
        def decode(token,cache):self.calls.append('decode');return 311,np.array([1,2],np.float32),{}
        return dict(vision_holder=[object()],restore=restore,prepare_reads=prepare,decode=decode,
            snapshot=lambda:{},release=lambda *a,**k:{'object_released':True},
            trim=lambda:{'called':True})
    def test_restore_and_preparation_every_state(self):
        args=self.arguments();result=run_trial(**args)
        self.assertEqual(self.calls,['restore','prepare','decode']*3)
        self.assertEqual(len(result['records']),3)
        self.assertFalse(result['performance_pass'])
    def test_mismatch_persisted_then_stop(self):
        args=self.arguments();count=[0];records=[]
        def decode(*a):count[0]+=1;return 311,np.array([count[0]],np.float32),{}
        args.update(decode=decode,on_record=records.append)
        with self.assertRaisesRegex(RuntimeError,'Full logits differ'):run_trial(**args)
        self.assertEqual(len(records),2)
        self.assertFalse(records[-1]['logits_bit_exact_vs_A'])
    def test_external_reference_stops_before_B(self):
        args=self.arguments();args['release']=lambda *a,**k:{'object_released':False}
        with self.assertRaisesRegex(RuntimeError,'external reference'):run_trial(**args)
        self.assertEqual(self.calls.count('decode'),1)

if __name__=='__main__':unittest.main()
