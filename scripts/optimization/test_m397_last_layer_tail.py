"""Offline control/packet/scale/parser checks, not FPGA/model numerical evidence.

Real frozen M241 loop and NumPy RMS/RoPE/SiLU, real dimensions and packet/parser.
Weights, Linear outputs, Attention, DMA and memory policy are explicit fakes.
"""
import ast
import math
from pathlib import Path
from types import SimpleNamespace
import time
import unittest
import numpy as np
from m351_workflow import ROOT
from m397_last_layer_tail_scope import LastLayerTailScope, RetainedTailOwnerError, call_plan

RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
RUNTIME=RELEASE/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime'
SOURCE=RELEASE/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
PARSER=SOURCE.with_name('m236_prefill_runtime.py')

def functions(path,names,namespace):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    selected=[]
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name in names:selected.append(n)
        if isinstance(n,ast.ClassDef):selected.extend(x for x in n.body if isinstance(x,ast.FunctionDef) and x.name in names)
    assert len(selected)==len(names)
    # Preserve each frozen source's postponed annotation semantics when extracting.
    future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future]+selected,type_ignores=[])),str(path),'exec'),namespace)
    return namespace

NS=dict(np=np,math=math,RMS_EPS=1e-6,ROPE_THETA=5_000_000.0,HEAD_DIM=128)
functions(RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py',{'rms_norm','silu','apply_rope','rotate_half'},NS)
PACK=dict(np=np,TOKENS=32,GROUP_SIZE=64,ACTIVATION_RECORD_BYTES=80)
functions(RUNTIME/'contract_runtime.py',{'quantize_t32','pack_chain_input'},PACK)
BR=ast.parse((RUNTIME/'board_runtime.py').read_text(encoding='utf-8-sig'))
SCALE=dict(np=np,math=math)
for n in BR.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('MAX_ACTIVATION_SCALE_SHIFT','MIN_ACTIVATION_SCALE_SHIFT','MAX_TRANSMITTED_ACTIVE_SCALE') for t in n.targets):
        exec(compile(ast.Module(body=[n],type_ignores=[]),'constants','exec'),SCALE)
functions(RUNTIME/'board_runtime.py',{'_initial_scale_shift'},SCALE)

def raw_contract():
    import json
    return json.loads((RUNTIME.parent/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json').read_text(encoding='utf-8'))
CHAINS={c['family']:c for c in raw_contract()['chains'] if c.get('layer')==35}

class Tests(unittest.TestCase):
    def model_case(self,n):
        self.calls=[];self.records={};self.last_hidden=None;self.head_calls=0;self.safe=True
        def family(layer,fam,v):
            self.calls.append((layer,fam,v.shape[0]))
            prefix=f'model.language_model.layers.{layer}'
            def expand(width,mult,offset):
                return (v[:,np.arange(width)%v.shape[1]]*np.float32(mult)+np.float32(offset)).astype(np.float32)
            if fam=='attention_out':result={prefix+'.self_attn.o_proj':expand(2560,.03,0)}
            elif fam=='gate_up':result={prefix+'.mlp.gate_proj':expand(9728,.2,.01),prefix+'.mlp.up_proj':expand(9728,.1,.02)}
            elif fam=='mlp_down':result={prefix+'.mlp.down_proj':expand(2560,.03,.001)}
            else:raise AssertionError(fam)
            if layer==35:
                packets=[]
                for start in range(0,v.shape[0],32):
                    b=v[start:start+32];s=SCALE['_initial_scale_shift'](b)
                    packets.append((s,PACK['pack_chain_input'](CHAINS[fam],b,CHAINS[fam]['staged_base_words'],s)))
                self.records[fam]=(v.copy(),{k:x.copy() for k,x in result.items()},packets)
            return result
        def attention_inputs(layer,v):
            return tuple((v[:,np.arange(width)%2560]*np.float32(.05)).astype(np.float32) for width in (4096,1024,1024))
        def head(v):
            self.head_calls+=1;self.last_hidden=v.copy()
            return v[:,np.arange(151936)%2560].copy()
        m=SimpleNamespace(weight=lambda name:np.ones(128 if '.q_norm.' in name or '.k_norm.' in name else 2560,np.float32),
                          _family=family,_attention_inputs=attention_inputs,grouped_attention_calls=0,grouped_attention_wall_ms=0,
                          runtime=SimpleNamespace(lm_head=head))
        ns=dict(NS,np=np,time=time,HIDDEN=2560,HEADS=32,KV_HEADS=8,HEAD_DIM=128,LAYERS=36,MAX_CONTEXT=1024,
                causal_attention_grouped=lambda q,k,v:q.reshape(n,4096).copy(),KVCache=lambda k,v:SimpleNamespace(keys=k,values=v))
        module=SimpleNamespace(__file__=str(SOURCE),**ns)
        functions(SOURCE,{'prefill'},ns)
        return m,module,ns['prefill']
    def compare(self,n):
        hidden=np.random.default_rng(71).standard_normal((n,2560),dtype=np.float32)*np.float32(.1)
        original_input=hidden.tobytes();m,module,original=self.model_case(n)
        baseline=original(m,hidden);baseline_hidden=self.last_hidden.copy();records=self.records;calls=self.calls.copy()
        m,module,_=self.model_case(n)
        scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:self.safe),lambda:True,tokens=n,enabled=True)
        candidate=scope.bind(module);actual=candidate(m,hidden)
        self.assertEqual(actual[0],baseline[0]);self.assertEqual(actual[1].tobytes(),baseline[1].tobytes())
        self.assertEqual(self.last_hidden.tobytes(),baseline_hidden.tobytes())
        for attr in ('keys','values'):
            self.assertEqual([x.tobytes() for x in getattr(actual[2],attr)],[x.tobytes() for x in getattr(baseline[2],attr)])
        start=scope.plan['tail_start'];tail=n-start
        for fam in ('attention_out','gate_up','mlp_down'):
            b,bo,bp=records[fam];a,ao,ap=self.records[fam]
            self.assertEqual(a.tobytes(),b[start:].tobytes())
            self.assertEqual(ap,[bp[-1]])
            for k in ao:self.assertEqual(ao[k].tobytes(),bo[k][start:].tobytes())
        self.assertEqual([x for x in self.calls if x[0]<35],[x for x in calls if x[0]<35])
        self.assertEqual([x[2] for x in self.calls if x[0]==35],[tail]*3)
        self.assertEqual(m.grouped_attention_calls,36);self.assertEqual(self.head_calls,1)
        self.assertEqual(hidden.tobytes(),original_input)
        self.assertEqual(len(actual[2].keys),36);self.assertEqual(scope.report()['selected'][0]['original_token_start'],start)
        scope.close();scope.close();self.assertTrue(scope.report()['binding_callback_removed'])
        count=len(self.calls)
        with self.assertRaises(RetainedTailOwnerError):candidate(m,hidden)
        self.assertEqual(len(self.calls),count)
    def test_real_size_synthetic159_control_and_packet_bits(self):self.compare(159)
    def test_fixed30_has_no_crop_and_same_control(self):self.compare(30)
    def test_default_disabled(self):
        with self.assertRaises(RuntimeError):LastLayerTailScope(None,None,None,tokens=159)
    def test_arbitrary_scope_input_refused(self):
        with self.assertRaises(ValueError):LastLayerTailScope(None,None,None,tokens=160,enabled=True)
    def test_call_plan_edges_and_exact159(self):
        for n in (1,30,31,32,33,64,65,128,159,160,1024):
            p=call_plan(n);self.assertEqual(p['tail_count'],(n-1)%32+1);self.assertEqual(p['tail_start']%32,0)
        self.assertEqual(call_plan(159)['logical'],766)
        for n in (0,1025,True,1.0):
            with self.assertRaises(ValueError):call_plan(n)
    def test_wrong_source_refused_without_families(self):
        m,module,_=self.model_case(159);module.__file__=__file__
        scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:True),lambda:True,tokens=159,enabled=True)
        with self.assertRaises(RuntimeError):scope.bind(module)
        self.assertEqual(self.calls,[]);scope.close()
    def test_wrong_owner_and_shape_before_execution(self):
        m,module,_=self.model_case(159);scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:True),lambda:True,tokens=159,enabled=True)
        fn=scope.bind(module)
        with self.assertRaises(RetainedTailOwnerError):fn(object(),np.zeros((159,2560),np.float32))
        with self.assertRaises(ValueError):fn(m,np.zeros((1,2560),np.float32))
        self.assertEqual(self.calls,[]);scope.close()
    def test_consumer_failure_retains_owner_and_callback(self):
        m,module,_=self.model_case(159);original=m._family
        def fault(layer,family,v):
            if layer==35 and family=='mlp_down':raise RuntimeError('Explicit fake hardware error')
            return original(layer,family,v)
        m._family=fault;scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:True),lambda:True,tokens=159,enabled=True)
        with self.assertRaises(RetainedTailOwnerError):scope.bind(module)(m,np.ones((159,2560),np.float32))
        self.assertTrue(scope.retained);self.assertIs(scope.model,m);self.assertEqual(self.head_calls,0)
        with self.assertRaises(RetainedTailOwnerError):scope.close()
        self.assertFalse(scope.report()['binding_callback_removed'])
    def test_unsafe_admission_refused(self):
        with self.assertRaises(RetainedTailOwnerError):LastLayerTailScope(None,SimpleNamespace(safe=lambda:False),lambda:True,tokens=159,enabled=True)
    def test_wrong_module_dimensions_and_second_binding_refused(self):
        m,module,_=self.model_case(159);scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:True),lambda:True,tokens=159,enabled=True)
        module.LAYERS=35
        with self.assertRaises(RuntimeError):scope.bind(module)
        module.LAYERS=36;scope.bind(module)
        with self.assertRaises(RetainedTailOwnerError):scope.bind(module)
        scope.close()
    def test_unsafe_head_completion_retains_owner(self):
        m,module,_=self.model_case(30);head=m.runtime.lm_head
        def fault(v):self.safe=False;return head(v)
        m.runtime.lm_head=fault
        scope=LastLayerTailScope(m,SimpleNamespace(safe=lambda:self.safe),lambda:True,tokens=30,enabled=True)
        with self.assertRaises(RetainedTailOwnerError):scope.bind(module)(m,np.ones((30,2560),np.float32))
        with self.assertRaises(RetainedTailOwnerError):scope.close()
        self.assertIs(scope.model,m);self.assertTrue(scope.retained)
    def test_actual_pending_retry_is_block_local(self):
        from concurrent.futures import Future
        ns=dict(np=np,base=SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=0))
        functions(PARSER,{'_resolve_pending'},ns)
        launched=[];accepted=[];pending=SimpleNamespace(future=Future(),values=np.ones((31,9728),np.float32),
                                                       output_buffer=object(),token_start=0,token_count=31,
                                                       initial_shift=6,attempted_shifts=[6])
        pending.future.set_result(False)
        runtime=SimpleNamespace(fused_nonfinite_detections=0,pipeline_retry_launches=0,
                                _launch_once=lambda c,v,b,o,base,s:launched.append((s,id(v),id(o))),
                                _parse_buffer=lambda c,o,t,start,n,s:s==4,
                                _accept_shift=lambda c,v,initial,tried,selected:accepted.append((initial,list(tried),selected)))
        targets={};ns['_resolve_pending'](runtime,CHAINS['mlp_down'],[],targets,0,pending)
        self.assertEqual(accepted,[(6,[6,5,4],4)]);self.assertEqual([x[0] for x in launched],[5,4])
        self.assertTrue(all(x[1]==id(pending.values) and x[2]==id(pending.output_buffer) for x in launched))
        next_pending=SimpleNamespace(**vars(pending));next_pending.future=Future();next_pending.future.set_result(True)
        next_pending.attempted_shifts=[6];ns['_resolve_pending'](runtime,CHAINS['mlp_down'],[],targets,0,next_pending)
        self.assertEqual(accepted[-1],(6,[6],6));self.assertEqual(runtime.pipeline_retry_launches,2)
    def test_frozen_parser_local_index_equals_original128(self):
        ns=dict(np=np)
        functions(SOURCE.with_name('m231_prefill_runtime.py'),{'_half_values_strided'},ns)
        functions(PARSER,{'_parse_into_and_check'},ns)
        chain=CHAINS['attention_out'];raw=bytearray(chain['output_bytes'])
        # Genuine stream order, deterministic finite FP16 words. Fake PL output.
        words=np.frombuffer(raw,dtype=np.uint8).reshape(-1,8)
        h=np.arange(len(words)*2,dtype=np.float32).reshape(-1,2)%97/np.float32(128)
        hp=h.astype('<f2').view(np.uint8).reshape(-1,4)
        words[:,:2]=hp[:,:2];words[:,4:6]=hp[:,2:4]
        module='model.language_model.layers.35.self_attn.o_proj'
        old={module:np.full((159,2560),np.nan,np.float32)};new={module:np.full((31,2560),np.nan,np.float32)}
        for s in (0,4,6):
            self.assertTrue(ns['_parse_into_and_check'](chain,raw,old,128,31,s))
            self.assertTrue(ns['_parse_into_and_check'](chain,raw,new,0,31,s))
            self.assertEqual(old[module][128:].tobytes(),new[module].tobytes())
        self.assertTrue(np.isnan(old[module][:128]).all())

if __name__=='__main__':unittest.main()
