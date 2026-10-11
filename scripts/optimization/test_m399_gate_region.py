"""Actual generated chain-region counters/owner guards, explicit fake consumers."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import weakref
from m351_workflow import ROOT
from m399_tail_chain_scope import RetainedChainOwnerError
GATE=ROOT/'tmp/m399/chain-draft/m399_tail_chain_gate.py'

class Tests(unittest.TestCase):
    def namespace(self,fault=None):
        r=dict(transactions=[],model_forward_calls=0);calls=[];refs=[]
        class Scope:
            def __init__(self,*a,**kw):
                assert kw=={'enabled':True};self.retained=False;self.closed=False;refs.append(weakref.ref(self))
            def run(self):
                for n in ('attention_out','gate_up','mlp_down'):
                    if fault=='consumer' and n=='gate_up':self.retained=True;raise RetainedChainOwnerError('EXPECTED_FAKE_CONSUMER')
                    calls.append(n);r['transactions'].append(dict(fake_DMA=True))
                return [dict(family=n,tokens=31) for n in calls]
            def close(self):self.closed=True
            def report(self):return dict(closed=self.closed,retained=self.retained)
        def evidence():
            return dict(logical_calls=len(calls),host_calls=len(calls)+(1 if fault=='counter' and calls else 0),
                        stage_bytes=(0 if fault=='stage' else 45268992)*len(calls)//3,scale_retry_count=0,pipeline_retry_launches=0,
                        logical_expected_macros=100*len(calls),expected_macros=100*len(calls))
        policy=SimpleNamespace(capture=lambda *a:None,begin_sampling=lambda:None,stop_sampling=lambda:None)
        engine=SimpleNamespace(language=SimpleNamespace(),stream=lambda:None)
        def patch(obj,name,value):setattr(obj,name,value)
        def path(p):
            if p=='/proc/cmdline':return SimpleNamespace(read_text=lambda **k:'FAKE_UNCHANGED_CMDLINE')
            return Path(p)
        return dict(engine=engine,runtime=SimpleNamespace(evidence=evidence),policy=policy,resident=lambda:True,
                    result=r,blocked=[],patch=patch,forbid=lambda *a:lambda *x:None,Path=path,
                    reference_pin={'raw_sha256':'ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef'},
                    TailChainScope=Scope,RetainedChainOwnerError=RetainedChainOwnerError,weakref=weakref,allocations=[None]*7,
                    sha256=lambda p:'FAKE_BOOT_SHA',boot=None,before_boot='FAKE_BOOT_SHA',before_cmd='FAKE_UNCHANGED_CMDLINE'),refs,calls
    def region(self):
        tree=ast.parse(GATE.read_text(encoding='utf-8'));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        body=next(n for n in main.body if isinstance(n,ast.Try)).body
        i=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and ast.unparse(n)=='model = engine.language')
        return compile(ast.fix_missing_locations(ast.Module(body=body[i:],type_ignores=[])),'<actual-m399-chain-region>','exec')
    def test_actual_region_completes_only_three_chains_and_releases_owner(self):
        ns,refs,calls=self.namespace();exec(self.region(),ns)
        self.assertEqual(calls,['attention_out','gate_up','mlp_down']);self.assertIsNone(refs[0]());self.assertIsNone(ns['chain_scope'])
        r=ns['result'];self.assertEqual(r['status'],'PASS_M399_LAST31_CHAIN_NUMERICAL');self.assertTrue(r['scope_weakref_dead']);self.assertTrue(r['chain_numerical_pass'])
        self.assertFalse(r['candidate_full_model_executed']);self.assertFalse(r['ps_prefetch_enabled']);self.assertEqual(r['chain_call_delta']['stage_bytes'],45268992)
    def test_consumer_fault_stops_before_down_and_retains_original_owner(self):
        ns,refs,calls=self.namespace('consumer')
        with self.assertRaises(RetainedChainOwnerError):exec(self.region(),ns)
        self.assertEqual(calls,['attention_out']);self.assertTrue(ns['chain_scope'].retained);self.assertIsNotNone(refs[0]());self.assertNotIn('chain_numerical_pass',ns['result'])
    def test_wrong_counter_and_stage_are_rejected(self):
        for fault in ('counter','stage'):
            with self.subTest(fault=fault):
                ns,refs,calls=self.namespace(fault)
                with self.assertRaises(RuntimeError):exec(self.region(),ns)
                self.assertNotIn('chain_numerical_pass',ns['result'])
    def test_finally_and_source_scope(self):
        s=GATE.read_text(encoding='utf-8');self.assertIn('unsafe=unsafe or chain_scope is not None',s)
        self.assertIn('except RetainedChainOwnerError',s);self.assertNotIn('engine.stream(request)',s)
        self.assertNotIn('prefill_function(',s);self.assertNotIn('bind_head(',s)
        self.assertIn("result['gate_return_code']=0 if result['status']=='PASS_M399_LAST31_CHAIN_NUMERICAL'",s)

if __name__=='__main__':unittest.main()
