"""Actual frozen stream/prefill control with explicit math/MMIO substitutes."""
import ast
import copy
import hashlib
import pathlib
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import sys
import numpy as np
from m351_workflow import ROOT,BASE
PKG=BASE/'candidates/M390-gate-up-capture-01'
sys.path.insert(0,str(PKG))
from m390_capture_boundary import GateUpCapture,CaptureBoundary
from m368_video_contract import tensor

RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'


def frozen_method(path,cls,name,env):
    tree=ast.parse((RELEASE/path).read_text(encoding='utf-8'))
    node=next(x for c in tree.body if isinstance(c,ast.ClassDef) and c.name==cls
              for x in c.body if isinstance(x,ast.FunctionDef) and x.name==name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env)
    return env[name]


class CaptureChecks(unittest.TestCase):
    def setUp(self):
        fixture_root=(ROOT/'tmp/m390/fixtures').resolve()
        fixture_root.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=fixture_root)
        assert pathlib.Path(self.temp.name).resolve().parent==fixture_root
        self.addCleanup(self.temp.cleanup)
        self.folder=pathlib.Path(self.temp.name)
        self.safe=True;self.observed=[]
        self.policy=SimpleNamespace(capture=lambda *a:None,safe=lambda:self.safe)
        self.values=np.zeros((159,2560),np.float32)
        self.outputs={n:{'model.language_model.layers.0.mlp.'+s+'_proj':np.full((159,9728),i+1,np.float32)
                         for i,s in enumerate(('gate','up'))} for n in ('gate_up',)}
        for name in ('q','kv','attention_out'):
            self.outputs[name]={'fake_control_only':np.zeros((159,2560),np.float32)}
        self.expected=[dict(layer=0,family=n,input=tensor(self.values),output={k:tensor(v) for k,v in sorted(self.outputs[n].items())}) for n in ('q','kv','attention_out','gate_up')]
        def original(layer,name,values):
            self.observed.append((layer,name));return self.outputs[name]
        self.cap=GateUpCapture(original,self.expected,self.policy,self.folder)

    def prefix(self):
        for name in ('q','kv','attention_out','gate_up'):self.cap(0,name,self.values)

    def test_real_serialization_geometry_and_expected_boundary(self):
        with self.assertRaises(CaptureBoundary):self.prefix()
        self.assertTrue(self.cap.done);self.assertEqual(len(self.observed),4)
        for n,item in self.cap.fixtures.items():
            p=pathlib.Path(item['path']);a=np.load(p,allow_pickle=False)
            self.assertEqual(a.tobytes(),self.outputs['gate_up']['model.language_model.layers.0.mlp.'+n+'_proj'].tobytes())
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),item['file_sha256'])
        with self.assertRaises(RuntimeError):self.cap(0,'mlp_down',self.values)
        self.assertEqual(len(self.observed),4)

    def test_hash_mismatch_rejects_without_fixture(self):
        self.outputs['q']['fake_control_only'][0,0]=1
        with self.assertRaises(RuntimeError):self.prefix()
        self.assertFalse(list(self.folder.iterdir()))

    def test_bad_shape_rejects(self):
        self.outputs['gate_up']['model.language_model.layers.0.mlp.gate_proj']=np.ones((30,9728),np.float32)
        # Match its hash so geometry check is independently exercised.
        self.expected[3]['output']={k:tensor(v) for k,v in sorted(self.outputs['gate_up'].items())}
        with self.assertRaises(RuntimeError):self.prefix()
        self.assertFalse(self.cap.done)

    def test_busy_DMA_rejects_without_fixture(self):
        self.safe=False
        with self.assertRaises(RuntimeError):self.prefix()
        self.assertFalse(list(self.folder.iterdir()))

    def test_live_pack_worker_rejects(self):
        with patch('m390_capture_boundary.threading.enumerate',return_value=[SimpleNamespace(name='m238-pack_0')]):
            with self.assertRaises(RuntimeError):self.prefix()
        self.assertFalse(list(self.folder.iterdir()))

    def test_existing_fixture_rejected(self):
        (self.folder/'gate.npy').write_bytes(b'original')
        with self.assertRaises(RuntimeError):self.prefix()
        self.assertEqual((self.folder/'gate.npy').read_bytes(),b'original')

    def test_mid_save_error_not_expected_boundary(self):
        with patch('m390_capture_boundary.np.save',side_effect=OSError('saved fixture fault')):
            with self.assertRaises(OSError):self.prefix()
        self.assertFalse(self.cap.done)

    def test_original_frozen_prefill_and_stream_stop_before_silu_down_head(self):
        # Original math functions and model outputs are explicit substitutes;
        # the actual frozen function bodies and unwind/lock order execute.
        calls=[];out={}
        def family(layer,name,values):
            calls.append((layer,name))
            if name in ('q','kv'):return {}
            if name=='attention_out':return {'model.language_model.layers.0.self_attn.o_proj':self.values.copy()}
            if name=='gate_up':return self.outputs['gate_up']
            raise AssertionError('down/later family reached')
        expected=[]
        for name in ('q','kv','attention_out','gate_up'):
            value=family(0,name,self.values);out[name]=value
            expected.append(dict(layer=0,family=name,input=tensor(self.values),output={k:tensor(v) for k,v in sorted(value.items())}))
        calls.clear()
        def original(layer,name,values):
            calls.append((layer,name));return out[name]
        cap=GateUpCapture(original,expected,self.policy,self.folder)
        def fail(*a,**kw):raise AssertionError('SiLU/down/head reached')
        def qkv(layer,values):
            cap(layer,'q',values);cap(layer,'kv',values)
            return (np.zeros((159,4096),np.float32),np.zeros((159,1024),np.float32),np.zeros((159,1024),np.float32))
        env=dict(np=np,time=time,HIDDEN=2560,MAX_CONTEXT=4096,HEADS=32,KV_HEADS=8,HEAD_DIM=128,LAYERS=36,
                 rms_norm=lambda x,w:x,apply_rope=lambda q,k,p:(q,k),
                 causal_attention_grouped=lambda *a:np.zeros((159,4096),np.float32),silu=fail,KVCache=fail)
        prefill=frozen_method('deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py','M241VideoLanguageModel','prefill',env)
        # attention_out input in the true body has4096 columns.
        expected[2]['input']=tensor(np.zeros((159,4096),np.float32))
        model=SimpleNamespace(weight=lambda *a:None,_attention_inputs=qkv,_family=cap,grouped_attention_calls=0,grouped_attention_wall_ms=0,runtime=SimpleNamespace(lm_head=fail))
        model.prefill=lambda h:prefill(model,h)
        import threading
        lock=threading.Lock()
        engine=SimpleNamespace(load=lambda:None,board=SimpleNamespace(evidence=lambda:{}),vision=lambda *a:None,
                               language=model,tokenizer=object(),_inference_lock=lock,config={'tokenizer':'fake'})
        stream_env=dict(np=np,time=time,preprocess=lambda f:{'pixel_values':None,'image_grid_thw':None,'patch_positions':None},
                        tokenize=lambda *a:[0]*159,M276_KNIFE_PROMPT='fake',latest_input_embeddings=lambda *a:self.values,
                        constrained_knife_decision=fail,_server=SimpleNamespace())
        stream=frozen_method('deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py','M276ShortPromptBinaryRuntime','stream',stream_env)
        request=SimpleNamespace(frames_rgb_u8=np.zeros((4,448,448,3),np.uint8))
        with self.assertRaises(CaptureBoundary):list(stream(engine,request))
        self.assertFalse(lock.locked())
        self.assertEqual(calls,[(0,n) for n in ('q','kv','attention_out','gate_up')])
        self.assertTrue(cap.done)


if __name__=='__main__':unittest.main(verbosity=2)
