import unittest
from contextlib import nullcontext
from types import SimpleNamespace
import numpy as np
from decode_diagnostic import DecodeDiagnostic


class DiagnosticTests(unittest.TestCase):
    def setup_case(self, fail=False):
        base=SimpleNamespace(__name__='test_backend',chain_window=lambda:None,copy_window_to_buffer=lambda:None,
                             wait_transaction=lambda:None)
        class Runtime:
            host_calls=logical_calls=stage_bytes=stage_ms=scale_retry_count=0
            def _stage(self):
                base.chain_window();base.copy_window_to_buffer();self.stage_bytes+=16
            def lm_head(self):return np.ones(4,np.float32)
        runtime=Runtime()
        class Model:
            def _family(self,layer,family,values):
                runtime._stage();base.wait_transaction()
                runtime.host_calls+=1;runtime.logical_calls+=1
                if fail:raise RuntimeError('hardware timeout')
                return values
            def decode(self,token,cache):
                self._family(0,'gate_up',np.ones((1,3),np.float32))
                cache.keys[0]=np.concatenate((cache.keys[0],cache.keys[0][-1:]))
                cache.values[0]=np.concatenate((cache.values[0],cache.values[0][-1:]))
                self.returned=(1,runtime.lm_head())
                return self.returned
        model=Model()
        cache=SimpleNamespace(keys=[np.zeros((4,1,2))],values=[np.zeros((4,1,2))])
        return model,runtime,base,cache

    def test_delegation_and_restore(self):
        model,runtime,base,cache=self.setup_case()
        diagnostic=DecodeDiagnostic(model,runtime,base,transfer_instrumenter=lambda *args:nullcontext(),detailed_runtime=False)
        returned=diagnostic.decode(2,cache)
        self.assertIs(returned,model.returned)
        self.assertNotIn('trace',diagnostic.records[0])
        diagnostic.finalize()
        record=diagnostic.records[0]
        self.assertEqual(record['counter_delta']['host_calls'],1)
        self.assertEqual(record['cache_after']['layers'][0]['key_shape'],[5,1,2])
        self.assertNotIn('_family',vars(model));self.assertNotIn('_stage',vars(runtime))
        names={e['name'] for e in record['trace']['events']}
        self.assertIn('device_completion_wait',names)
        self.assertIn('weight_window_lookup',names)
        with self.assertRaises(RuntimeError):diagnostic.decode(1,cache)

    def test_failure_preserves_exception_and_restores(self):
        model,runtime,base,cache=self.setup_case(fail=True)
        diagnostic=DecodeDiagnostic(model,runtime,base,transfer_instrumenter=lambda *args:nullcontext(),detailed_runtime=False)
        with self.assertRaisesRegex(RuntimeError,'hardware timeout'):diagnostic.decode(2,cache)
        self.assertEqual(diagnostic.records[0]['status'],'FAIL')
        self.assertNotIn('_family',vars(model));self.assertNotIn('_stage',vars(runtime))


if __name__=='__main__':unittest.main()
