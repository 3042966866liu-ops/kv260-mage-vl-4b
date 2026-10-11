"""Actual frozen video wrapper/stream; explicitly fake PL, attention and memory."""
import ast
import contextlib
import json
import sys
import time
import textwrap
import unittest
import weakref
from types import SimpleNamespace
import numpy as np
from m351_workflow import ROOT,BASE
from m393_silu_scope import SiluLayerScope,RetainedSiluOwnerError
from m368_video_contract import tensor
import test_m393_silu_scope as model_fixture

PKG=BASE/'candidates/M394-silu-video-01'
VIDEO=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'

class Tests(unittest.TestCase):
    def wrapper(self):
        f=model_fixture.Tests();f.setup_model(159)
        source=(PKG/'m394_silu_video_gate.py').read_text(encoding='utf-8')
        tree=ast.parse(source);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        node=next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name=='observed_prefill')
        factory='def factory():\n    silu_scope=None\n'+textwrap.indent(ast.unparse(node),'    ')+'\n    def retained():return silu_scope\n    return observed_prefill,retained\n'
        result={};captured={}
        ns=dict(tensor=tensor,expected={'baseline':{'input':tensor(f.hidden)}},policy=f.policy,model=f.model,
                resident=lambda:True,SiluLayerScope=SiluLayerScope,RetainedSiluOwnerError=RetainedSiluOwnerError,
                sys=SimpleNamespace(modules={'m241_video_language_runtime':f.module}),weakref=weakref,
                result=result,captured=captured,allocations=[None]*7)
        exec(factory,ns);call,retained=ns['factory']()
        return f,call,retained,result,captured

    def test_actual_wrapper_once_closed_owner_and_real159_geometry(self):
        f,call,retained,r,c=self.wrapper();output=call(f.hidden)
        self.assertEqual(output[0],17);self.assertEqual(len(output[2].keys),36)
        self.assertEqual(r['silu_scope']['calls'],36);self.assertEqual(r['silu_scope']['workspace_bytes'],6187008)
        self.assertTrue(r['scope_weakref_dead']);self.assertTrue(r['silu_scope']['workspace_buffer_released']);self.assertIsNone(retained())
        with self.assertRaises(RuntimeError):call(f.hidden)
        self.assertEqual(f.head_calls,1)

    def test_late_consumer_failure_retains_owner_in_actual_wrapper(self):
        f,call,retained,r,c=self.wrapper();original=f.model._family
        def failure(layer,name,value):
            if layer==35 and name=='mlp_down':raise RuntimeError('EXPLICIT_FAKE_PL_ERROR')
            return original(layer,name,value)
        f.model._family=failure
        with self.assertRaises(RetainedSiluOwnerError):call(f.hidden)
        self.assertIsNotNone(retained());self.assertTrue(retained().retained)
        self.assertIsNotNone(retained().workspace._buffer);self.assertEqual(f.head_calls,0)

    def test_input_identity_rejected_before_scope_or_family(self):
        f,call,retained,r,c=self.wrapper()
        with self.assertRaises(RuntimeError):call(f.hidden[:30])
        self.assertIsNone(retained());self.assertEqual(f.layers,[])

    def test_original_stream_runs_wrapper_and_releases_inference_lock(self):
        f,call,retained,r,c=self.wrapper();f.model.prefill=call
        tree=ast.parse(VIDEO.read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M276ShortPromptBinaryRuntime');node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='stream')
        ns=dict(time=time,np=np,M276_KNIFE_PROMPT='fixture',select_last_frame=lambda frames:frames[-1:],
                preprocess=lambda frame:{'pixel_values':frame,'image_grid_thw':None,'patch_positions':None},
                tokenize=lambda *a:list(range(159)),latest_input_embeddings=lambda *a:f.hidden,
                constrained_knife_decision=lambda logits:dict(text='0',token_id=15,verdict='ABSENT',knife_score=.4,score_kind='fake'),
                _server=SimpleNamespace(BUILD_ID='0x4D333537',KERNEL='fake',expected_physical_calls=lambda *a:778))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_stream','exec'),ns)
        count=[0]
        def evidence():
            count[0]+=1;return dict(build_id='0x4D333537',logical_calls=0 if count[0]==1 else 778,logical_expected_macros=0 if count[0]==1 else 1)
        import threading
        lock=threading.Lock()
        engine=SimpleNamespace(load=lambda:None,_inference_lock=lock,tokenizer=object(),config={'tokenizer':'fake'},language=f.model,
                               vision=lambda *a:None,board=SimpleNamespace(evidence=evidence))
        events=list(ns['stream'](engine,SimpleNamespace(prompt='fixture',max_new_tokens=1,frames_rgb_u8=np.zeros((4,448,448,3),np.uint8))))
        self.assertEqual([p['name'] for n,p in events if n=='stage'],['preprocess','vision','prefill'])
        self.assertEqual([n for n,p in events].count('complete'),1);self.assertEqual(f.head_calls,1);self.assertIsNone(retained())
        self.assertTrue(lock.acquire(blocking=False));lock.release()

if __name__=='__main__':unittest.main()
