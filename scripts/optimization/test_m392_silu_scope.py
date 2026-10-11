"""Actual frozen layer loop and borrowed-result lifecycle, explicit fake DMA/math."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys
import time
import textwrap
import weakref
import numpy as np
from m351_workflow import ROOT,BASE
OLD=BASE/'candidates/M385-ps-layer-02';sys.path.insert(0,str(OLD))
from m343_layer_scope import bind
from m392_silu_scope import SiluLayerScope,RetainedSiluOwnerError

SOURCE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
GENERATED=(OLD/'frozen_one_layer.py').read_text(encoding='utf-8')

class Tests(unittest.TestCase):
    def setUp(self):
        self.safe=True;self.resident=True;self.calls=[];self.active=[];self.scope=None;self.identities=[]
        self.policy=SimpleNamespace(capture=lambda *a:None,safe=lambda:self.safe)
        self.gate=np.random.default_rng(1).standard_normal((159,9728),dtype=np.float32)
        self.up=np.random.default_rng(2).standard_normal((159,9728),dtype=np.float32)
        def family(layer,name,value):
            self.calls.append(name)
            if name=='attention_out':return {'model.language_model.layers.0.self_attn.o_proj':np.zeros((159,2560),np.float32)}
            if name=='gate_up':return {'model.language_model.layers.0.mlp.gate_proj':self.gate,'model.language_model.layers.0.mlp.up_proj':self.up}
            if name=='mlp_down':
                if self.scope is not None:self.active.append(self.scope.workspace._active);self.identities.append(id(value))
                return {'model.language_model.layers.0.mlp.down_proj':value[:,:2560].copy()}
            raise AssertionError('Unexpected family')
        self.model=SimpleNamespace(_family=family,weight=lambda *a:None,_attention_inputs=lambda *a:(np.zeros((159,1),np.float32),)*3,
                                  grouped_attention_calls=0,grouped_attention_wall_ms=0)
        self.module=SimpleNamespace(__file__=str(SOURCE),np=np,time=time,HIDDEN=2560,MAX_CONTEXT=4096,HEADS=1,HEAD_DIM=1,KV_HEADS=1,LAYERS=36,
                                    rms_norm=lambda a,w:a,apply_rope=lambda q,k,p:(q,k),causal_attention_grouped=lambda *a:np.zeros((159,1),np.float32),
                                    silu=lambda x:(x/(1.0+np.exp(-x))).astype(np.float32),KVCache=lambda k,v:SimpleNamespace(keys=k,values=v))
        self.hidden=np.zeros((159,2560),np.float32)
    def make(self):
        self.scope=SiluLayerScope(self.model,self.policy,lambda:self.resident,enabled=True)
        return self.scope,self.scope.bind(self.module,GENERATED)
    def test_actual_layer_math_reuse_retry_consumer_and_close(self):
        namespace=dict(vars(self.module));namespace['LAYERS']=1;exec(GENERATED,namespace)
        reference,kv=namespace['one_layer'](self.model,self.hidden)
        owner,fn=self.make()
        for _ in range(2):
            actual,k=fn(self.model,self.hidden)
            self.assertEqual(actual.tobytes(),reference.tobytes());self.assertEqual(k.keys[0].tobytes(),kv.keys[0].tobytes());self.assertEqual(k.values[0].tobytes(),kv.values[0].tobytes())
        self.assertEqual(self.active,[True,True]);self.assertEqual(self.identities[0],self.identities[1]);self.assertEqual(owner.calls,2)
        owner.close();self.assertTrue(owner.report()['workspace_buffer_released']);self.assertTrue(owner.report()['binding_callback_removed'])
    def test_busy_after_consumer_retains_buffer(self):
        owner,fn=self.make();original=self.model._family
        def late_busy(*a):
            output=original(*a)
            if a[1]=='mlp_down':self.safe=False
            return output
        self.model._family=late_busy
        with self.assertRaises(RetainedSiluOwnerError):fn(self.model,self.hidden)
        self.assertTrue(owner.retained);self.assertTrue(owner.workspace._retained)
        with self.assertRaises(RetainedSiluOwnerError):owner.close()
        self.assertIsNotNone(owner.workspace._buffer)
    def test_live_parser_after_consumer_refused(self):
        owner,fn=self.make();original=self.model._family
        def future(*a):
            output=original(*a)
            if a[1]=='mlp_down':self.active.append('parser')
            return output
        self.model._family=future
        with patch('m392_silu_scope.threading.enumerate',side_effect=lambda:[SimpleNamespace(name='m238-parse_0')] if 'parser' in self.active else []):
            with self.assertRaises(RetainedSiluOwnerError):fn(self.model,self.hidden)
        with self.assertRaises(RetainedSiluOwnerError):owner.close()
    def test_consumer_failure_retains_binding_and_workspace(self):
        owner,fn=self.make();original=self.model._family
        def failure(*a):
            if a[1]=='mlp_down':raise RuntimeError('FAKE_ACTIVE_OR_RETRY_FAILURE')
            return original(*a)
        self.model._family=failure
        with self.assertRaises(RetainedSiluOwnerError):fn(self.model,self.hidden)
        self.assertTrue(owner.bindings);self.assertIsNotNone(owner.workspace)
        with self.assertRaises(RetainedSiluOwnerError):owner.close()
    def test_wrong_model_or_closed_scope(self):
        owner,fn=self.make()
        with self.assertRaises(RetainedSiluOwnerError):
            with owner.lease(object(),self.gate,self.up):pass
        owner.close()
        with self.assertRaises(RetainedSiluOwnerError):fn(self.model,self.hidden)
    def test_changed_frozen_statement_rejected(self):
        owner,fn=self.make()
        with self.assertRaises(RuntimeError):owner.bind(self.module,GENERATED.replace('down_input)', 'down_input.copy())'))
        owner.close()
    def test_default_off_and_prior_busy(self):
        with self.assertRaises(RuntimeError):SiluLayerScope(self.model,self.policy,lambda:True)
        self.safe=False
        with self.assertRaises(RuntimeError):SiluLayerScope(self.model,self.policy,lambda:True,enabled=True)
    def test_unreleased_borrow_rejected_on_close(self):
        owner,fn=self.make();fn(self.model,self.hidden);borrow=owner.workspace._buffer
        with self.assertRaises(RetainedSiluOwnerError):owner.close()
        self.assertIsNotNone(borrow)
    def test_actual_frozen_gate_invocation_and_owner_weakref(self):
        pkg=BASE/'candidates/M392-silu-layer-02'
        source=(pkg/'m392_silu_layer_gate.py').read_text(encoding='utf-8')
        a=source.index('        silu_scope=SiluLayerScope(');z=source.index("        policy.capture('after-layer0'",a)
        result={}
        namespace=dict(model=self.model,policy=self.policy,resident=lambda:True,SiluLayerScope=SiluLayerScope,
                       sys=SimpleNamespace(modules={'m241_video_language_runtime':self.module}),frozen_layer=GENERATED,
                       hidden=self.hidden,weakref=weakref,result=result,allocations=[None]*7,RetainedSiluOwnerError=RetainedSiluOwnerError)
        exec(textwrap.dedent(source[a:z]),namespace)
        self.assertTrue(result['scope_weakref_dead']);self.assertEqual(result['silu_scope']['calls'],1)
        self.assertTrue(result['silu_scope']['workspace_buffer_released']);self.assertFalse(result['ps_prefetch_enabled'])

if __name__=='__main__':unittest.main()
