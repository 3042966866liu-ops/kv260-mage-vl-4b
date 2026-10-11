"""Original full36-layer Prefill control, real-size synthetic activation math.

Attention, norm, weights, PL output, MMIO/memory are explicit substitutes.
"""
import ast
import json
from types import SimpleNamespace
import sys
import time
import textwrap
import weakref
import unittest
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT,BASE
from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError
SOURCE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'

class Tests(unittest.TestCase):
    def setup_model(self,tokens):
        self.tokens=tokens;self.safe=True;self.owner=None;self.inputs=[];self.outputs=[];self.layers=[];self.head_calls=0
        self.gate=np.random.default_rng(3).standard_normal((tokens,9728),dtype=np.float32);self.up=np.random.default_rng(4).standard_normal((tokens,9728),dtype=np.float32)
        self.policy=SimpleNamespace(capture=lambda *a:None,safe=lambda:self.safe)
        def family(layer,name,value):
            prefix=f'model.language_model.layers.{layer}'
            if name=='attention_out':return {prefix+'.self_attn.o_proj':np.zeros((tokens,2560),np.float32)}
            if name=='gate_up':return {prefix+'.mlp.gate_proj':self.gate,prefix+'.mlp.up_proj':self.up}
            if name=='mlp_down':
                self.layers.append(layer)
                if self.owner is not None:self.inputs.append(id(value));self.outputs.append(self.owner.workspace._active)
                return {prefix+'.mlp.down_proj':value[:,:2560].copy()}
            raise AssertionError('Unexpected family')
        def head(v):
            self.head_calls+=1;r=np.zeros((1,151936),np.float32);r[0,17]=2;return r
        self.model=SimpleNamespace(weight=lambda *a:None,_family=family,_attention_inputs=lambda *a:(np.zeros((tokens,1),np.float32),)*3,
                                   grouped_attention_calls=0,grouped_attention_wall_ms=0,runtime=SimpleNamespace(lm_head=head))
        self.module=SimpleNamespace(__file__=str(SOURCE),np=np,time=time,HIDDEN=2560,MAX_CONTEXT=4096,HEADS=1,HEAD_DIM=1,KV_HEADS=1,LAYERS=36,
                                    rms_norm=lambda a,w:a,apply_rope=lambda q,k,p:(q,k),causal_attention_grouped=lambda *a:np.zeros((tokens,1),np.float32),
                                    silu=lambda x:(x/(1.0+np.exp(-x))).astype(np.float32),KVCache=lambda k,v:SimpleNamespace(keys=k,values=v))
        self.hidden=np.zeros((tokens,2560),np.float32)
    def compare(self,tokens):
        self.setup_model(tokens)
        tree=ast.parse(SOURCE.read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M241VideoLanguageModel');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prefill')
        namespace=dict(vars(self.module));exec(compile(ast.Module(body=[fn],type_ignores=[]),'original','exec'),namespace)
        expected=namespace['prefill'](self.model,self.hidden)
        self.layers=[];self.head_calls=0;self.owner=SiluLayerScope(self.model,self.policy,lambda:True,enabled=True);candidate=self.owner.bind(self.module)
        actual=candidate(self.model,self.hidden)
        self.assertEqual(expected[0],actual[0]);self.assertEqual(expected[1].tobytes(),actual[1].tobytes())
        self.assertEqual([a.tobytes() for a in expected[2].keys],[a.tobytes() for a in actual[2].keys]);self.assertEqual([a.tobytes() for a in expected[2].values],[a.tobytes() for a in actual[2].values])
        self.assertEqual(self.layers,list(range(36)));self.assertEqual(self.head_calls,1);self.assertEqual(len(set(self.inputs)),1);self.assertTrue(all(self.outputs));self.assertEqual(self.owner.calls,36)
        self.owner.close();self.assertEqual(self.owner.report()['workspace_bytes'],tokens*9728*4);self.assertTrue(self.owner.report()['workspace_buffer_released'])
        count=len(self.layers)
        with self.assertRaises(RetainedSiluOwnerError):candidate(self.model,self.hidden)
        self.assertEqual(len(self.layers),count)
    def test_original_fixed30_full_prefill_control(self):self.compare(30)
    def test_original_fixed159_full_prefill_control(self):self.compare(159)
    def test_late_layer_consumer_failure_does_not_reuse_or_head(self):
        self.setup_model(159);self.owner=SiluLayerScope(self.model,self.policy,lambda:True,enabled=True);fn=self.owner.bind(self.module);family=self.model._family
        def fault(layer,name,value):
            if layer==12 and name=='mlp_down':raise RuntimeError('FAKE_RETRY_CONSUMER_ERROR')
            return family(layer,name,value)
        self.model._family=fault
        with self.assertRaises(RetainedSiluOwnerError):fn(self.model,self.hidden)
        self.assertEqual(self.owner.calls,12);self.assertEqual(self.head_calls,0);self.assertTrue(self.owner.retained)
        with self.assertRaises(RetainedSiluOwnerError):self.owner.close()
    def test_head_completion_checked_before_release(self):
        self.setup_model(30);owner=SiluLayerScope(self.model,self.policy,lambda:True,enabled=True);fn=owner.bind(self.module);head=self.model.runtime.lm_head
        def fault(v):self.safe=False;return head(v)
        self.model.runtime.lm_head=fault;fn(self.model,self.hidden)
        with self.assertRaises(RetainedSiluOwnerError):owner.close()
        self.assertIsNotNone(owner.workspace._buffer)
    def test_wrong_source_before_call(self):
        self.setup_model(30);owner=SiluLayerScope(self.model,self.policy,lambda:True,enabled=True)
        self.module.__file__=__file__
        with self.assertRaises(RuntimeError):owner.bind(self.module)
        self.assertEqual(self.layers,[]);owner.close()
    def test_actual_frozen_text_gate_call_and_owner_release(self):
        self.setup_model(30);pkg=BASE/'candidates/M393-silu-text-01';s=(pkg/'m393_silu_text_gate.py').read_text(encoding='utf-8')
        a=s.index('        silu_scope=SiluLayerScope(');z=s.index("        policy.capture('after-fixed-text'",a)
        result={};namespace=dict(model=self.model,policy=self.policy,resident=lambda:True,SiluLayerScope=SiluLayerScope,
             sys=SimpleNamespace(modules={'m241_video_language_runtime':self.module}),hidden=self.hidden,weakref=weakref,result=result,
             allocations=[None]*7,RetainedSiluOwnerError=RetainedSiluOwnerError)
        exec(textwrap.dedent(s[a:z]),namespace)
        self.assertTrue(result['scope_weakref_dead']);self.assertEqual(result['silu_scope']['calls'],36)
        self.assertEqual(namespace['token'],17);self.assertEqual(len(namespace['kv'].keys),36)
        self.assertTrue(result['silu_scope']['workspace_buffer_released']);self.assertFalse(result['ps_prefetch_enabled'])

if __name__=='__main__':unittest.main()
