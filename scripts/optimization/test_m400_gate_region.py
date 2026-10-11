"""Execute actual generated gate region with explicit fake scope/DMA counters."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import weakref
from m351_workflow import ROOT
from m399_tail_chain_scope import RetainedChainOwnerError
GATE=ROOT/'tmp/m400/layer-draft/m400_tail_layer_gate.py'


class Tests(unittest.TestCase):
    def namespace(self,fault=None):
        result=dict(transactions=[],model_forward_calls=0);calls=[];refs=[]
        pin=dict(raw_sha256='ca4a8d45e5e73190ee476958886cc97eafb42f6476d1c440fcbae9d99b2400ef',expected_stage_bytes=53624832,expected_macros=81920000,expected_scale_attempts=[])
        engine=SimpleNamespace(language=SimpleNamespace(grouped_attention_calls=0),stream=lambda:None)
        class Scope:
            def __init__(self,*a,**kw):
                assert kw=={'enabled':True};self.retained=False;self.closed=False;refs.append(weakref.ref(self))
            def run(self,module,generated):
                assert 'one_layer' in generated
                for family,n in (('qkv',5),('attention_out',1),('gate_up',1),('mlp_down',1)):
                    if fault=='consumer' and family=='gate_up':self.retained=True;raise RetainedChainOwnerError('EXPECTED_FAKE_CONSUMER')
                    calls.extend([family]*n);result['transactions'].extend([dict(explicit_fake_DMA=True)]*n)
                engine.language.grouped_attention_calls=1
                return dict(explicit_fake_layer=True)
            def close(self):self.closed=True
            def report(self):return dict(closed=self.closed,retained=self.retained)
        def evidence():
            return dict(logical_calls=len(calls),host_calls=len(calls)+(1 if fault=='counter' and calls else 0),
                        stage_bytes=(0 if fault=='stage' else 53624832) if calls else 0,scale_retry_count=0,pipeline_retry_launches=0,
                        logical_expected_macros=(100 if fault=='macro' else 81920000) if calls else 0,
                        expected_macros=(100 if fault=='macro' else 81920000) if calls else 0,
                        scale_attempts=[dict(explicit_fake_wrong_scale=True)] if fault=='scale' and calls else [])
        def path(p):
            if p=='/proc/cmdline':return SimpleNamespace(read_text=lambda **k:'FAKE_UNCHANGED_CMDLINE')
            return Path(p)
        return dict(engine=engine,runtime=SimpleNamespace(evidence=evidence),policy=SimpleNamespace(capture=lambda *a:None,begin_sampling=lambda:None,stop_sampling=lambda:None),
                    resident=lambda:True,result=result,blocked=[],patch=lambda obj,name,value:setattr(obj,name,value),forbid=lambda *a:lambda *x:None,
                    Path=path,HERE=GATE.parent,sys=SimpleNamespace(modules={'m241_video_language_runtime':None}),
                    reference_pin=pin,TailLayerScope=Scope,RetainedChainOwnerError=RetainedChainOwnerError,weakref=weakref,allocations=[None]*7,
                    sha256=lambda p:'FAKE_BOOT_SHA',boot=None,before_boot='FAKE_BOOT_SHA',before_cmd='FAKE_UNCHANGED_CMDLINE'),refs,calls

    def region(self):
        tree=ast.parse(GATE.read_text(encoding='utf-8'));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        body=next(n for n in main.body if isinstance(n,ast.Try)).body
        i=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and ast.unparse(n)=='model = engine.language')
        return compile(ast.fix_missing_locations(ast.Module(body=body[i:],type_ignores=[])),'<actual-m400-layer-region>','exec')

    def test_actual_region_one_layer_and_owner_release(self):
        ns,refs,calls=self.namespace();exec(self.region(),ns)
        self.assertEqual(calls,['qkv']*5+['attention_out','gate_up','mlp_down']);self.assertIsNone(refs[0]());self.assertIsNone(ns['layer_scope'])
        self.assertEqual(ns['result']['status'],'PASS_M400_TAIL_LAYER_NUMERICAL');self.assertTrue(ns['result']['scope_weakref_dead'])
        self.assertFalse(ns['result']['candidate_full_model_executed']);self.assertEqual(ns['result']['isolated_layer_calls'],1)

    def test_consumer_failure_preserves_owner_and_stops(self):
        ns,refs,calls=self.namespace('consumer')
        with self.assertRaises(RetainedChainOwnerError):exec(self.region(),ns)
        self.assertEqual(calls,['qkv']*5+['attention_out']);self.assertTrue(ns['layer_scope'].retained);self.assertIsNotNone(refs[0]())
        self.assertNotIn('layer_numerical_pass',ns['result'])

    def test_actual_counter_stage_macro_and_scale_rejections(self):
        for fault in ('counter','stage','macro','scale'):
            with self.subTest(fault=fault):
                ns,refs,calls=self.namespace(fault)
                with self.assertRaises(RuntimeError):exec(self.region(),ns)
                self.assertNotIn('layer_numerical_pass',ns['result'])

    def test_finally_retention_and_default_off_scope(self):
        s=GATE.read_text(encoding='utf-8')
        self.assertIn('unsafe=unsafe or layer_scope is not None',s);self.assertIn('except RetainedChainOwnerError',s)
        self.assertIn("result['gate_return_code']=0 if result['status']=='PASS_M400_TAIL_LAYER_NUMERICAL'",s)
        self.assertIn('M400 disabled by default',s);self.assertNotIn('engine.stream(request)',s);self.assertNotIn('bind_head(',s)


if __name__=='__main__':unittest.main()
