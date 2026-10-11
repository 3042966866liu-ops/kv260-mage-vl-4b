"""Actual packaged wrapper, explicit fake Linear/Attention; no board evidence."""
import ast
import importlib.util
import sys
import textwrap
from types import SimpleNamespace
import unittest
import weakref
import numpy as np
import test_m397_last_layer_tail as fixture
from m351_workflow import ROOT,BASE
from m368_video_contract import tensor
PKG=BASE/'candidates/M402-tail-video-01'
spec=importlib.util.spec_from_file_location('m401_prefill_tail_scope',PKG/'m401_prefill_tail_scope.py')
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)
sys.path.insert(0,str(PKG))

class Tests(unittest.TestCase):
    def wrapper(self):
        f=fixture.Tests();m,module,original=f.model_case(159)
        tree=ast.parse((PKG/'m402_tail_video_gate.py').read_bytes())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        nodes=[next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name==name) for name in ('observed_family','observed_prefill')]
        source='def factory():\n    layer_scope=None\n'+'\n'.join(textwrap.indent(ast.unparse(n),'    ') for n in nodes)+'\n    def retained():return layer_scope\n    return observed_family,observed_prefill,retained\n'
        hidden=np.full((159,2560),np.float32(.1));r={};captured={};families=[]
        ns=dict(model=m,tensor=tensor,FAMILIES=[(l,n) for l in range(36) for n in ('attention_out','gate_up','mlp_down')],expected={'baseline':{'input':tensor(hidden)}},policy=SimpleNamespace(safe=lambda:f.safe,capture=lambda *a:None),resident=lambda:True,result=r,captured=captured,families=families,original_family=m._family,LastLayerTailScope=scope.LastLayerTailScope,RetainedTailOwnerError=scope.RetainedTailOwnerError,sys=SimpleNamespace(modules={'m241_video_language_runtime':module}),weakref=weakref,allocations=[None]*7)
        exec(source,ns);observe,call,retained=ns['factory']();m._family=observe
        return f,m,hidden,call,retained,r,families
    def test_actual_wrapper_selects_only_last31_and_closes(self):
        f,m,h,call,retained,r,families=self.wrapper();answer=call(h)
        self.assertEqual(len(answer[2].keys),36);self.assertTrue(r['scope_weakref_dead']);self.assertIsNone(retained())
        self.assertEqual([x[2] for x in f.calls if x[0]==35],[31]*3)
        self.assertTrue(r['tail_candidate_executed']);self.assertFalse(r['silu_workspace_enabled']);self.assertFalse(r['ps_prefetch_enabled'])
        self.assertEqual(families[-3]['input']['shape'],[31,4096])
        with self.assertRaises(RuntimeError):call(h)
        self.assertEqual(f.head_calls,1)
    def test_actual_late_failure_retains_scope(self):
        f,m,h,call,retained,r,_=self.wrapper();family=m._family
        def fault(l,n,v):
            if l==35 and n=='mlp_down':raise RuntimeError('EXPLICIT_FAKE_PL_ERROR')
            return family(l,n,v)
        m._family=fault
        with self.assertRaises(scope.RetainedTailOwnerError):call(h)
        self.assertTrue(retained().retained);self.assertEqual(f.head_calls,0)
    def test_wrong_input_precedes_scope_and_resources(self):
        f,m,h,call,retained,r,_=self.wrapper()
        with self.assertRaises(RuntimeError):call(h[:30])
        self.assertIsNone(retained());self.assertEqual(f.calls,[])
    def test_cleanup_and_count_guard_paths(self):
        s=(PKG/'m402_tail_video_gate.py').read_text(encoding='utf-8')
        self.assertIn('unsafe=unsafe or layer_scope is not None or count_scope is not None',s)
        self.assertLess(s.index('validate_count(video_server.expected_physical_calls)'),s.index('engine.load()'))
        self.assertLess(s.index('count_scope.close()'),s.index('engine.close()'))
        self.assertIn("row['logical_calls']!=766",s);self.assertIn("expected['transactions']",s)
        self.assertIn('m276_video_runtime._server is not video_server',s)

if __name__=='__main__':unittest.main()
