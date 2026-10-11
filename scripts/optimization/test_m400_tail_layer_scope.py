"""Actual frozen layer, real NumPy math/dimensions/NPY; explicit fake Linear/DMA."""
import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
import weakref
import numpy as np
from m351_workflow import ROOT
from m343_layer_scope import derive as original_layer
from m400_tail_layer_scope import TailLayerScope,derive,RetainedChainOwnerError
from m399_tail_chain_scope import digest
from m398_reference_capture import SHAPES
from m368_video_contract import tensor
from test_m397_last_layer_tail import SOURCE,NS,functions

TEMP=ROOT/'tmp/m400/component-tests'


class Tests(unittest.TestCase):
    def fixture(self,d,fault=None):
        destination=Path(d); records={}; calls=[]; unsafe=[False]
        def family(layer,name,x):
            calls.append((layer,name,x.shape))
            if fault=='consumer' and name=='gate_up':raise RuntimeError('EXPLICIT_FAKE_PL_FAILURE')
            prefix=f'model.language_model.layers.{layer}.'
            specs={'qkv':{'self_attn.q_proj':4096,'self_attn.k_proj':1024,'self_attn.v_proj':1024},
                   'attention_out':{'self_attn.o_proj':2560},'gate_up':{'mlp.gate_proj':9728,'mlp.up_proj':9728},'mlp_down':{'mlp.down_proj':2560}}
            out={prefix+k:(x[:,np.arange(width)%x.shape[1]]*np.float32(.03)+np.float32(.001*(i+1))).astype(np.float32) for i,(k,width) in enumerate(specs[name].items())}
            records[name]=(x.copy(),{k:v.copy() for k,v in out.items()})
            return out
        model=SimpleNamespace(_family=family,weight=lambda name:np.ones(128 if '.q_norm.' in name or '.k_norm.' in name else 2560,np.float32),grouped_attention_calls=0,grouped_attention_wall_ms=0)
        def attention_inputs(layer,x):
            out=model._family(layer,'qkv',x);p=f'model.language_model.layers.{layer}.'
            return out[p+'self_attn.q_proj'],out[p+'self_attn.k_proj'],out[p+'self_attn.v_proj']
        model._attention_inputs=attention_inputs
        ns=dict(NS,np=np,math=math,time=time,HIDDEN=2560,HEADS=32,KV_HEADS=8,HEAD_DIM=128,LAYERS=36,MAX_CONTEXT=1024,
                KVCache=lambda k,v:SimpleNamespace(keys=k,values=v))
        functions(SOURCE,{'causal_attention_grouped'},ns)
        baseline=ast.parse(original_layer(SOURCE.read_bytes()));loop=next(n for n in baseline.body[0].body if isinstance(n,ast.For));loop.iter=ast.parse('range(35,36)',mode='eval').body
        exec(compile(ast.fix_missing_locations(baseline),'<original-final-layer>','exec'),ns)
        hidden=np.random.default_rng(71).standard_normal((159,2560),dtype=np.float32)*np.float32(.1)
        # Baseline explicit fake Linear must run before enabling requested faults.
        saved_fault=fault;fault=None
        full,kv=ns['one_layer'](model,hidden)
        p='model.language_model.layers.35.'
        arrays=dict(residual_full=hidden,attended_full=records['attention_out'][0],
                    attention_out_input_tail=records['attention_out'][0][128:],attention_out_output_tail=records['attention_out'][1][p+'self_attn.o_proj'][128:],
                    gate_up_input_tail=records['gate_up'][0][128:],gate_tail=records['gate_up'][1][p+'mlp.gate_proj'][128:],up_tail=records['gate_up'][1][p+'mlp.up_proj'][128:],
                    mlp_down_input_tail=records['mlp_down'][0][128:],mlp_down_output_tail=records['mlp_down'][1][p+'mlp.down_proj'][128:],hidden_tail=full[128:],
                    final_norm=ns['rms_norm'](full[-1:],np.ones(2560,np.float32)))
        files={}
        for name,shape in SHAPES.items():
            if name=='logits':files[name]={'unused_metadata_explicit_fake':True};continue
            a=np.ascontiguousarray(arrays[name]);path=destination/(name+'.npy');np.save(path,a,allow_pickle=False)
            files[name]=dict(path=str(path),file_bytes=path.stat().st_size,file_sha256=digest(path),tensor=tensor(a),original_token_start=0 if name.endswith('_full') else 158 if name=='final_norm' else 128)
        qkv=dict(layer=35,family='qkv',input=tensor(records['qkv'][0]),output={k:tensor(v) for k,v in records['qkv'][1].items()})
        original=dict(status='PASS_M398_ORIGINAL_TAIL_REFERENCE',gate_return_code=0,reference_capture_pass=True,tail_candidate_executed=False,candidate_numerical_pass=False,
                      reference_capture=dict(closed=True,retained=False,binding_callback_removed=True,candidate_tail_not_executed=True,file_count=12,fixtures=files),
                      video_result=dict(families=[qkv],keys=[{}]*35+[tensor(kv.keys[0])],values=[{}]*35+[tensor(kv.values[0])]))
        if saved_fault=='kv':original['video_result']['keys'][35]['sha256']='0'*64
        if saved_fault=='attention':
            a=arrays['attended_full'].copy();a[0,0]=np.nextafter(a[0,0],np.float32(10));path=destination/'attended_full.npy';np.save(path,a,allow_pickle=False)
            files['attended_full'].update(file_sha256=digest(path),tensor=tensor(a))
        raw=destination/'load-memory.json';raw.write_text(json.dumps(original),encoding='utf-8')
        calls.clear();records.clear();model.grouped_attention_calls=0;fault=saved_fault
        module=SimpleNamespace(__file__=str(SOURCE),**ns)
        scope=TailLayerScope(model,SimpleNamespace(safe=lambda:not unsafe[0],capture=lambda *a:None),lambda:True,raw,digest(raw),enabled=True)
        return scope,model,module,calls,raw,unsafe

    def dispose_fake(self,s):
        # Only self-owned fixtures/fake model; no board, DMA or actual worker.
        for a in s.maps.values():a._mmap.close()
        s.maps.clear()
        if s.observer is not None:s.model._family=s.original_family
        for n in s.bindings:n.pop('_m400_select',None)
        s.bindings.clear()

    def test_full_real_PS_math_last_layer_and_all_reference_checks(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            s,m,module,calls,raw,unsafe=self.fixture(d);owner=weakref.ref(s);original=m._family
            r=s.run(module,derive(SOURCE.read_bytes()))
            self.assertEqual([(n,x[0]) for _,n,x in calls],[('qkv',159),('attention_out',31),('gate_up',31),('mlp_down',31)])
            self.assertTrue(r['full_QKV_KV_SHA_equal']);self.assertTrue(r['full_attention_and_tail_tensors_bitwise_equal'])
            self.assertEqual(m.grouped_attention_calls,1);self.assertEqual(r['key']['shape'],[159,8,128]);self.assertEqual(r['hidden_tail']['shape'],[31,2560])
            s.close();s.close();report=s.report();self.assertEqual(report['reference_files_checked'],11)
            self.assertTrue(report['reference_maps_released'] and report['binding_callback_removed'] and report['original_family_restored'])
            self.assertIs(m._family,original);del s;self.assertIsNone(owner())

    def test_default_off(self):
        with self.assertRaisesRegex(RuntimeError,'disabled'):TailLayerScope(None,None,None,None,None)

    def test_consumers_or_KV_Attention_mismatch_retain_and_stop(self):
        for fault in ('consumer','kv','attention'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory(dir=TEMP) as d:
                s,m,module,calls,raw,unsafe=self.fixture(d,fault)
                try:
                    with self.assertRaises(RetainedChainOwnerError):s.run(module,derive(SOURCE.read_bytes()))
                    self.assertTrue(s.retained);self.assertIs(s.model,m);self.assertTrue(s.maps)
                    if fault in ('consumer','attention'):self.assertFalse(any(n=='mlp_down' for _,n,_ in calls))
                    with self.assertRaises(RetainedChainOwnerError):s.close()
                finally:self.dispose_fake(s)

    def test_source_change_refused_before_family(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            s,m,module,calls,raw,unsafe=self.fixture(d)
            try:
                with self.assertRaises(RetainedChainOwnerError):s.run(module,derive(SOURCE.read_bytes())+'#wrong\n')
                self.assertEqual(calls,[]);self.assertTrue(s.retained)
            finally:self.dispose_fake(s)

    def test_postuse_raw_change_retains_close_resources(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            s,m,module,calls,raw,unsafe=self.fixture(d)
            try:
                s.run(module,derive(SOURCE.read_bytes()));raw.write_text(raw.read_text(encoding='utf-8')+' ',encoding='utf-8')
                with self.assertRaises(RetainedChainOwnerError):s.close()
                self.assertTrue(s.maps and s.retained and s.bindings)
            finally:self.dispose_fake(s)

    def test_double_run_stale_family_and_head_forbidden(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as d:
            s,m,module,calls,raw,unsafe=self.fixture(d)
            with self.assertRaisesRegex(RuntimeError,'LM head'):s.load('logits')
            s.run(module,derive(SOURCE.read_bytes()));n=len(calls);s.close()
            with self.assertRaises(RetainedChainOwnerError):s.run(module,derive(SOURCE.read_bytes()))
            self.assertEqual(len(calls),n)

    def test_actual_derived_loop_only_range_and_selector(self):
        original=ast.parse(original_layer(SOURCE.read_bytes()));candidate=ast.parse(derive(SOURCE.read_bytes()))
        ol=next(n for n in original.body[0].body if isinstance(n,ast.For));cl=next(n for n in candidate.body[0].body if isinstance(n,ast.For))
        self.assertEqual(ast.unparse(cl.iter),'range(35, 36)');cl.iter=ol.iter
        cl.body=[n for n in cl.body if '_m400_select' not in ast.unparse(n)]
        self.assertEqual(ast.dump(ol,include_attributes=False),ast.dump(cl,include_attributes=False))
        self.assertNotIn('lm_head',derive(SOURCE.read_bytes()))


if __name__=='__main__':
    TEMP.mkdir(parents=True,exist_ok=True);unittest.main()
