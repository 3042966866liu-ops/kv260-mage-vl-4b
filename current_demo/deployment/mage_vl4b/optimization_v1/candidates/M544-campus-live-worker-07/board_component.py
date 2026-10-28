"""CPU scheduling fixtures: actual M241 control/math, fake Linear capabilities.

No Overlay, allocation or DMA. This is not FPGA numerical or task evidence.
"""
import ast,copy,hashlib,math,textwrap,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from board_subset import LanguageSubset,StageSubset,indices

def execute_node(path,name,namespace,inside=None):
    source=Path(path).read_text(encoding='utf-8');tree=ast.parse(source)
    parent=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==inside) if inside else tree
    node=next(x for x in parent.body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace[name]

def inherited_check(pkg,original,release):
    pkg,original,release=map(Path,(pkg,original,release));plan=__import__('json').loads((pkg/'DEMO_BOARD_PLAN.json').read_bytes())
    path=release/'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    raw=release/'deployment/mage_vl4b/m181_m120_video_board_candidate/video_language_runtime.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=plan['M241_module_sha256']:raise ValueError('Actual source module SHA differs')
    class Cache:
        def __init__(self,k,v):self.keys,self.values=k,v
    ns=dict(np=np,math=math,time=time,HIDDEN=2560,HEADS=32,HEAD_DIM=128,KV_HEADS=8,MAX_CONTEXT=1024,LAYERS=36,RMS_EPS=1e-6,ROPE_THETA=5000000.,KVCache=Cache)
    for name in ('rms_norm','rotate_half','apply_rope','silu'):execute_node(raw,name,ns)
    execute_node(path,'causal_attention_grouped',ns);prefill=execute_node(path,'prefill',ns,inside='M241VideoLanguageModel')
    class FakeLanguage:
        def __init__(self):
            self.grouped_attention_calls=0;self.grouped_attention_wall_ms=0.;self.layers_seen=[];self.family_seen=[];self.runtime=SimpleNamespace(lm_head=self.head)
        def weight(self,name):return np.ones(128 if name.endswith(('q_norm.weight','k_norm.weight')) else 2560,np.float32)
        def _attention_inputs(self,layer,x):
            self.layers_seen.append(layer)
            return np.tile(x,(1,2))[:,:4096].copy(),x[:,:1024].copy(),x[:,:1024].copy()
        def _family(self,layer,family,x):
            self.family_seen.append((layer,family));prefix='model.language_model.layers.'+str(layer)
            if family=='attention_out':return {prefix+'.self_attn.o_proj':np.ascontiguousarray(x[:,:2560]*np.float32(.01))}
            if family=='gate_up':
                y=np.tile(x,(1,4))[:,:9728]*np.float32(.01+(layer%3)*.001)
                return {prefix+'.mlp.gate_proj':y,prefix+'.mlp.up_proj':y.copy()}
            if family=='mlp_down':return {prefix+'.mlp.down_proj':np.repeat(np.mean(x,axis=1,keepdims=True,dtype=np.float32),2560,axis=1)}
            raise AssertionError(family)
        def head(self,x):
            z=np.zeros((1,151936),np.float32);z[0,:2560]=x[0];return z
    FakeLanguage.prefill=prefill
    x=(np.arange(128*2560,dtype=np.float32).reshape(128,2560)%257)*np.float32(.001)
    parent=FakeLanguage();expected=parent.prefill(x.copy())
    candidate=FakeLanguage();scope=LanguageSubset(candidate,list(range(36)),lambda:None,plan['M241_prefill_source_sha256']);scope.select(True)
    same=candidate.prefill(x.copy());assert np.array_equal(expected[1],same[1]) and all(np.array_equal(a,b) for a,b in zip(expected[2].keys,same[2].keys))
    scope.close();assert 'prefill' not in candidate.__dict__
    retained=plan['retained_language'];candidate=FakeLanguage();scope=LanguageSubset(candidate,retained,lambda:None,plan['M241_prefill_source_sha256']);scope.select(True);observed=candidate.prefill(x.copy())
    assert candidate.layers_seen==retained and len(observed[2].keys)==len(retained) and len(observed[2].values)==len(retained)
    assert {i for i,_ in candidate.family_seen}==set(retained) and all(a.shape==(128,8,128) for a in observed[2].keys+observed[2].values)
    scope.close();assert 'prefill' not in candidate.__dict__
    rejected=[]
    for bad in ([],[0,0],[2,1],[-1],[36],[True]):
        try:indices(bad,36)
        except ValueError:rejected.append(bad)
        else:raise AssertionError('Invalid retained list accepted')
    windows=__import__('json').loads((original/'STAGE_WINDOWS.json').read_bytes())['windows']
    chains=[dict(layer=i,family=f) for i in range(36) for f in (('q','kv','attention_out','gate_up','mlp_down') if i<10 else ('qkv','attention_out','gate_up','mlp_down'))];head=[dict(layer=-1,family='lm_head') for _ in range(8)]
    runtime=SimpleNamespace(language_contract=SimpleNamespace(chains=chains),head_contract=SimpleNamespace(chains=head),staged_buffers=[object() for _ in range(4)])
    reader=SimpleNamespace(future=None,pending=None,slots=[bytearray(1) for _ in range(4)])
    prefetch=SimpleNamespace(active=False,reader=reader);stage=StageSubset(runtime,prefetch,windows,retained,lambda:None)
    full=stage.select(False);small=stage.select(True)
    expected_groups=[i for i,c in enumerate(chains) if c['layer'] in retained]+list(range(154,162))
    assert small['source_group_indices']==expected_groups and len(prefetch.groups)==len(expected_groups)
    assert full['effective_bytes']==sum(w['effective_bytes'] for w in windows) and small['effective_bytes']<=full['effective_bytes']
    reader.future=object()
    try:stage.select(False)
    except RuntimeError:pass
    else:raise AssertionError('Active read future accepted')
    reader.future=None;stage.select(False);assert len(prefetch.groups)==162
    # Execute the original strict adaptive call checker with only the selected
    # sequence changed. Fake byte wires test sequencing, never hardware math.
    ns={'copy':copy};execute_node(original/'M455_combination_visual52301.py','AdaptiveVisualBatchCheck',ns)
    Check=execute_node(pkg/'board_visual_subset.py','SubsetBatchCheck',ns)
    pl=[i for i in plan['retained_vision'] if i>=13]
    cases={i:{part:dict(input_bytes=4,output_bytes=8) for part in ('fc1','fc2')} for i in pl}
    checker=Check(cases,lambda *args:b'\0'*8,pl);batches={}
    for i in pl:
        batches[str(i)]={}
        for part in ('fc1','fc2'):
            batches[str(i)][part]=[]
            for start in range(0,392,32):
                checker(i,part,cases[i][part],start,6,b'\0'*4)
                batches[str(i)][part].append(dict(start=start,rows=min(32,392-start),initial_shift=6,selected_shift=6,attempted_shifts=[6],physical_calls=1))
    checked=checker.require_complete(batches);assert checked['logical_batches']==26*len(pl)
    bad_rejected=0
    if pl:
        i=pl[0]
        for part,start,shift,packet,expected in [('fc2',0,6,b'\0'*4,'order'),('fc1',0,7,b'\0'*4,'shift'),('fc1',0,6,b'\0'*3,'length')]:
            check=Check(cases,lambda *args:b'\0'*8,pl)
            try:check(i,part,cases[i][part],start,shift,packet)
            except ValueError:bad_rejected+=1
            else:raise AssertionError(expected)
        broken=copy.deepcopy(batches);broken[str(i)]['fc1'][-1]['rows']=32
        try:checker.require_complete(broken)
        except RuntimeError:bad_rejected+=1
        else:raise AssertionError('Wrong final8 row count accepted')
        check=Check(cases,lambda *args:b'\0'*8,pl)
        check(i,'fc1',cases[i]['fc1'],0,6,b'\0'*4)
        try:check(i,'fc1',cases[i]['fc1'],0,6,b'\0'*4)
        except ValueError:bad_rejected+=1
        else:raise AssertionError('Non-descending repeated shift accepted')
    return dict(status='PASS_CPU_RETAINED_BLOCK_SCHEDULING_FIXTURES_NOT_FPGA',actual_M241_body_reused=True,full36_reference_logits_and_KV_bit_exact=True,retained_language=retained,removed_layer_family_calls=0,compact_cache_layers=len(observed[2].keys),invalid_retained_lists_rejected=len(rejected),active_worker_retarget_rejected=True,full_stage=full,candidate_stage=small,retained_visual_PL=pl,checked_logical_visual_batches=checked['logical_batches'],visual_bad_sequence_shift_length_rows_retry_rejected=bad_rejected,model_constructors=0,Overlay=0,DMA=0,physical_transactions=0)


def check(pkg,original,release):
    value=inherited_check(pkg,original,release)
    from head_component import check_head
    value["learned_head"]=check_head(pkg)
    value['actual_padded_head']=check_actual_head(pkg,original)
    from check_language_parser import run as check_parser
    import platform
    import gate_up_native
    library=Path(pkg)/'m532_parser_kernel.so'
    assert platform.machine()=='aarch64' and gate_up_native.GateUpNative(library).library.m455_parser_neon()==1
    report=Path('/dev/shm/m544_live_component07.json')
    assert not report.exists()
    assert check_parser(library,Path(original)/'private_runtime',report)==0
    value['all_language_C_dispatch']=__import__('json').loads(report.read_bytes())
    from check_visual_cache import check as cache_check
    value['visual_cache_component']=cache_check(original)
    from check_vision_profiler import check as profile_check
    value['vision_profile_component']=profile_check()
    from board_helpers import component as v4_check
    value['V4_actual_PS_recovery']=v4_check(pkg,release)
    from live_protocol import tests
    value['live_frame_protocol']=tests()
    return value


def check_actual_head(pkg,original):
    import types,json
    from learned_head import LearnedHead
    pkg,original=Path(pkg),Path(original);namespace=dict(np=np,TOKENS=32)
    runtime=original/'private_runtime/board_runtime.py';contract=original/'private_runtime/contract_runtime.py'
    for name,file in [('merge_outputs',contract),('require_complete',contract),('lm_head',runtime)]:
        node=next(n for n in ast.walk(ast.parse(file.read_text(encoding='utf-8'))) if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'),namespace)
    cases=[]
    for label in ('negative','positive'):
        with np.load(pkg/('head_fixture_'+label+'.npz'),allow_pickle=False) as f:x=f['x'].copy();first=f['z'].copy();target=int(f['target'])
        base=np.repeat(first,32,axis=0);base[1:]+=np.arange(1,32,dtype=np.float32)[:,None]*.001
        for mode in ('resident-fixture','staged-low-cma'):
            class Fake:
                def _stage(self,layout,chain):return [],0
                def _execute(self,chain,values,buffers,*args):
                    assert values.shape==(1,2560)
                    y=np.full((32,151936),np.nan,np.float32);a,b=chain['start'],chain['stop'];y[:,a:b]=base[:,a:b]
                    return {'lm_head':y}
            fake=Fake();fake.weight_mode=mode;fake.head_contract=types.SimpleNamespace(chains=[dict(start=i*18992,stop=(i+1)*18992) for i in range(8)]);fake.head_layout=types.SimpleNamespace(manifest={'modules':[{'shape':[151936,2560]}]});fake.head_buffers=[]
            fake.lm_head=types.MethodType(namespace['lm_head'],fake)
            assert np.array_equal(fake.lm_head(x),base)
            head=LearnedHead(pkg,json.loads((pkg/'HEAD_MANIFEST.json').read_bytes()));head.install(fake);result=fake.lm_head(x)
            assert result.shape==(32,151936) and np.array_equal(result[1:].view(np.uint32),base[1:].view(np.uint32)) and int(result[0].argmax())==target
            head.close();assert np.array_equal(fake.lm_head(x),base)
            cases.append(dict(label=label,weight_mode=mode,actual_frozen_method_and_merge=True,device_execution_is_fake=True,padded_shape=list(result.shape),unused31_rows_bit_exact=True,argmax=target))
    return dict(status='PASS_ACTUAL_HEAD_PADDING_INTERFACE_COMPONENT_NOT_FPGA',cases=cases,model_forwards=0,Overlay=0,DMA=0)
