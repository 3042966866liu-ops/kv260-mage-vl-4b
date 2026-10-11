"""Actual frozen schedulers and real Futures; explicit fake PL/parser/model."""
import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M373-future-wait-component-01'))
from m373_test_future_wait import Harness
from m375_video_wait import VideoWaitDiagnostic
from m375_wait_validation import validate

CONTRACT=json.loads((ROOT/'deployment/mage_vl4b/optimization_v1/runs/M375-video-wait-plan-01/RESULT.json').read_text(encoding='utf-8'))['family_contract']

class Probe(Harness):
    def _language_chain(self,layer,family):
        row=next(r for r in CONTRACT if (r['layer'],r['family'])==(layer,family))
        return dict(layer=layer,family=family,chain_index=row['chain_index'],groups=1)
    def _parse_buffer(self,chain,output,targets,start,count,shift):
        if self.retry and chain['chain_index'] in (0,1,2) and start==0 and shift==1:
            return False
        retry=self.retry; self.retry=False
        try:return super()._parse_buffer(chain,output,targets,start,count,shift)
        finally:self.retry=retry

class Model:
    def __init__(self,runtime):self.runtime=runtime
    def _family(self,layer,name,values):return self.runtime.language_family_many(layer,name,values)
    def prefill(self,hidden):
        answers=[];x=np.ascontiguousarray(hidden[:,:64])
        for row in CONTRACT:answers.append(self._family(row['layer'],row['family'],x)['probe'])
        self.answer=answers
        return answers

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime=Probe(retry=True);model=Model(runtime)
        scope=VideoWaitDiagnostic(model,runtime,CONTRACT,enabled=True)
        answer=scope.prefill(np.ones((159,2560),np.float32))
        assert answer is model.answer
        reference_runtime=Probe(retry=True)
        reference=Model(reference_runtime).prefill(np.ones((159,2560),np.float32))
        for a,b in zip(answer,reference):np.testing.assert_array_equal(a,b)
        assert runtime.accepted==reference_runtime.accepted
        assert runtime.pipeline_retry_launches==reference_runtime.pipeline_retry_launches==3
        assert runtime.stages==154
        assert all(n not in vars(obj) for obj,n in ((model,'_family'),(runtime,'language_family_many'),(runtime,'_resolve_pending')))
        cls.report=scope.report();cls.scope=scope
    def test_complete_original_sequence_retry_output_and_summary(self):
        result=validate(self.report,CONTRACT)
        self.assertEqual(result['summary']['parse']['calls'],770)
        self.assertEqual(result['summary']['pack']['calls'],770)
        self.assertEqual(result['main_thread_closure_error_ns'],0)
        self.assertEqual(set(result['by_family']),{'q','kv','qkv','attention_out','gate_up','mlp_down'})
    def test_default_disabled_and_single_use(self):
        r=Probe();m=Model(r)
        with self.assertRaises(ValueError):VideoWaitDiagnostic(m,r,CONTRACT)
        with self.assertRaises(RuntimeError):self.scope.prefill(np.ones((159,2560),np.float32))
    def test_failure_restores_owned_bindings_and_original_exception(self):
        r=Probe(fail_parse=True);m=Model(r)
        m._family=m._family;r.language_family_many=r.language_family_many;r._resolve_pending=r._resolve_pending
        prior=(m._family,r.language_family_many,r._resolve_pending)
        scope=VideoWaitDiagnostic(m,r,CONTRACT,enabled=True)
        with self.assertRaisesRegex(ValueError,'fake parser'):scope.prefill(np.ones((159,2560),np.float32))
        self.assertEqual((m._family,r.language_family_many,r._resolve_pending),prior)
        self.assertTrue(scope.restored)
        with self.assertRaises(ValueError):validate(scope.report(),CONTRACT)
    def test_outer_prefill_timer_does_not_recurse(self):
        r=Probe(fail_parse=True);m=Model(r);scope=VideoWaitDiagnostic(m,r,CONTRACT,enabled=True)
        m.prefill=lambda hidden:scope.prefill(hidden)
        with self.assertRaisesRegex(ValueError,'fake parser'):m.prefill(np.ones((159,2560),np.float32))
        self.assertTrue(scope.restored)
    def test_reject_corruption_and_uncovered_scope(self):
        for name in ('sum','exclusive','parent','ready','order','family','unknown','missing','wait_duration','restoration','scope','sha'):
            r=copy.deepcopy(self.report)
            if name=='sum':r['summary']['parse']['condition_wait_s']+=1
            elif name=='exclusive':r['trace']['events'][0]['exclusive_ns']+=1
            elif name=='parent':r['trace']['events'][1]['parent']=99999
            elif name=='ready':r['records'][0]['ready_before']=1
            elif name=='order':r['records'][0]['token_start']=128
            elif name=='family':r['families'][0]['chain_index']+=1
            elif name=='unknown':r['trace']['events'][1]['name']='unknown'
            elif name=='missing':r['records'].pop()
            elif name=='wait_duration':r['records'][0]['condition_wait_ns']=r['records'][0]['result_wall_ns']+1
            elif name=='restoration':r['bindings_restored']=False
            elif name=='scope':r['extra_cma_allocations']=1
            else:r['future_result_source_sha256']='0'*64
            with self.assertRaises(ValueError,msg=name):validate(r,CONTRACT)

if __name__=='__main__':unittest.main()
