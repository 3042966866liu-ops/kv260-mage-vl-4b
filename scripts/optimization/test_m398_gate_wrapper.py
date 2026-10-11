"""Exercise the real generated wrapper/stream, with explicit fake Linear/Attention."""
import ast
import contextlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import textwrap
import threading
import time
import unittest
import weakref
import numpy as np
import test_m397_last_layer_tail as fixture
from m351_workflow import ROOT
from m398_reference_capture import LastLayerReferenceCapture,RetainedReferenceOwnerError
from m368_video_contract import tensor

GATE=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M398-tail-reference-01/m398_tail_reference_gate.py'
TEMP=ROOT/'tmp/m398/wrapper-tests'

class Tests(unittest.TestCase):
    def wrapper(self,d):
        f=fixture.Tests();m,module,original=f.model_case(159);family=m._family
        m._family=lambda l,n,v:{k:np.ascontiguousarray(x) for k,x in family(l,n,v).items()}
        tree=ast.parse(GATE.read_text(encoding='utf-8'));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        nodes=[next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name==name) for name in ('observed_family','observed_prefill')]
        source='def factory():\n    capture_scope=None\n'+'\n'.join(textwrap.indent(ast.unparse(n),'    ') for n in nodes)+'\n    def retained():return capture_scope\n    return observed_family,observed_prefill,retained\n'
        hidden=np.ones((159,2560),np.float32)*np.float32(.1);r={};captured={};families=[]
        ns=dict(model=m,tensor=tensor,FAMILIES=[(l,n) for l in range(36) for n in ('attention_out','gate_up','mlp_down')],
                expected={'baseline':{'input':tensor(hidden)}},policy=SimpleNamespace(safe=lambda:f.safe,capture=lambda *a:None),
                resident=lambda:True,result=r,captured=captured,families=families,original_family=m._family,
                LastLayerReferenceCapture=LastLayerReferenceCapture,RetainedReferenceOwnerError=RetainedReferenceOwnerError,
                EVIDENCE=Path(d),sys=SimpleNamespace(modules={'m241_video_language_runtime':module}),weakref=weakref,allocations=[None]*7)
        exec(source,ns);observe,call,retained=ns['factory']();m._family=observe
        return f,m,hidden,call,retained,r
    def test_real_wrapper_captures_once_owner_released(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,h,call,retained,r=self.wrapper(d);answer=call(h)
            self.assertEqual(len(answer[2].keys),36);self.assertEqual(r['reference_capture']['file_count'],12)
            self.assertTrue(r['scope_weakref_dead']);self.assertIsNone(retained());self.assertFalse(r['tail_candidate_executed'])
            self.assertFalse(r['silu_workspace_enabled']);self.assertFalse(r['ps_prefetch_enabled'])
            with self.assertRaises(RuntimeError):call(h)
            self.assertEqual(f.head_calls,1)
    def test_actual_wrapper_fault_retains_scope_and_blocks_head(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,h,call,retained,r=self.wrapper(d);family=m._family
            def fault(l,n,v):
                if l==35 and n=='mlp_down':raise RuntimeError('FAKE_PL_ERROR')
                return family(l,n,v)
            m._family=fault
            with self.assertRaises(RetainedReferenceOwnerError):call(h)
            self.assertTrue(retained().retained);self.assertEqual(f.head_calls,0)
    def test_wrong_input_before_capture(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            f,m,h,call,retained,r=self.wrapper(d)
            with self.assertRaises(RuntimeError):call(h[:30])
            self.assertIsNone(retained());self.assertEqual(f.calls,[])
    def test_finally_retention_and_count_policy_are_present(self):
        source=GATE.read_text(encoding='utf-8')
        self.assertIn('unsafe=unsafe or capture_scope is not None',source)
        self.assertIn("row['logical_calls']!=778",source)
        self.assertIn("capture_scope.family(layer,name,values,output)",source)
        self.assertNotIn('LastLayerTailScope',source)
        self.assertNotIn('SiluLayerScope',source)
        self.assertIn("result['candidate_numerical_pass']=False",source)

if __name__=='__main__':
    TEMP.mkdir(parents=True,exist_ok=True)
    unittest.main()
