"""Actual frozen wrapper/encoder/M207 + exact oracle, synthetic small MLP.

All24 boundaries use the real392x1024 shape; synthetic weights, narrow MLP
and Attention are explicit. This validates orchestration, not model quality.
"""
import ast, __future__, hashlib, json, sys, threading, time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import numpy as np

def component(root):
    import torch
    from m408_target_component04 import actual_class
    from m355_reference import decode_records
    from m407_mlp_contract import chain_for
    from m409_ftz_reference import SoftwareMLPBinding
    from test_m409_ftz_reference import actual_host
    from m426_range import RangeScope, SELECTED
    p=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py','M206ProgressLayer',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time))
    b=actual_class(torch,root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py','M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    linear=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    model=root/'deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/modeling_mage_vl.py'
    cls=next(n for n in ast.parse(model.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='MageVLVisionEncoderLayer')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward');ns={}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(model),'exec',flags=__future__.annotations.compiler_flag),ns)
    class Attention(torch.nn.Module):
        def forward(self,hidden_states,**unused):return hidden_states*.03125,None
    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__();self.fc1=torch.nn.Linear(1024,64);self.fc2=torch.nn.Linear(64,1024)
        def forward(self,x):return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__();self.mlp=MLP();self.layer_norm1=torch.nn.LayerNorm(1024);self.layer_norm2=torch.nn.LayerNorm(1024);self.self_attn=Attention()
        forward=ns['forward']
    torch.manual_seed(426);layers=torch.nn.ModuleList();cases={};targets={};inputs={}
    for i in range(24):
        inner=Encoder();dtype=torch.bfloat16 if i<2 else torch.float32;inner.to(dtype)
        layers.append(p(b(inner,dtype,torch.bfloat16),index=i,heartbeat_seconds=30.,run_elapsed=lambda:0.))
        if i<2:continue
        targets[i]=inner;chains={};windows={}
        for k,rows,columns in (('fc1',64,1024),('fc2',1024,64)):
            groups=columns//64;per=rows//4;size=groups*(per//8)*272
            tile=dict(tile_index=0,row_start=0,valid_rows=rows,rows_per_shard=per,shard_offsets=[0]*4,record_bytes_per_shard=size)
            c=chain_for(dict(module=k,shape=[rows,columns],input_groups=groups,bits=4,tiles=[tile]),i*2+(k=='fc2'));chains[k]=c
            window=(np.full(8,.0078125,'<f2').tobytes()+bytes([0x9a])*256)*(groups*per//8);windows[k]=[window]*4
            codes,scales=decode_records(window,groups,per,4)
            weight=np.tile((codes.astype(np.float32)*scales.astype(np.float32)[...,None]).transpose(1,0,2).reshape(per,columns),(4,1))
            class Store:
                def __init__(self,w):self.w=w
                def decode(self,name):return self.w.copy()
            mod=linear(torch,Store(weight),k,columns,rows,True,torch.float32)
            mod.bias=torch.nn.Parameter(torch.arange(rows,dtype=torch.float32)*(.000013*i),requires_grad=False)
            setattr(inner.mlp,k,mod)
        cases[i]=dict(chains=chains,windows=windows)
    host,initial=actual_host(root)
    def forward():
        x=((torch.arange(392*1024).reshape(1,392,1024)%137-68).float()*.013).to(torch.bfloat16)
        for layer in layers:x=layer(x)[0]
        return x
    def clean():
        return all('forward' not in getattr(targets[i].mlp,k).__dict__ for i in targets for k in ('fc1','fc2')) and all(not l._forward_hooks and not l._forward_pre_hooks for l in layers)
    boundary=[];loads=[]
    def sink(i,a):boundary.append((i,hashlib.sha256(a.tobytes()).hexdigest()))
    def load(i):loads.append(i);return cases[i]
    with torch.inference_mode():
        with RangeScope(torch,layers,targets,SELECTED,'original',load,initial,host,sink,lambda label:None) as original_scope:original=forward()
        assert loads==[] and original_scope.complete and original_scope.restored and clean()
        original_boundaries=tuple(boundary);boundary.clear()
        with RangeScope(torch,layers,targets,SELECTED,'software',load,initial,host,sink,lambda label:None) as scope:software=forward()
        assert scope.complete and scope.restored and clean() and loads==list(SELECTED) and scope.peak_live_layer_scopes==1
        assert sum(len(batch) for parts in scope.batches.values() for batch in parts.values())==572
        assert len(boundary)==24 and boundary[0]==original_boundaries[0] and boundary[1]==original_boundaries[1]
        assert any(boundary[i]!=original_boundaries[i] for i in SELECTED)
        with ExitStack() as stack:
            for i in SELECTED:
                stack.enter_context(SoftwareMLPBinding(torch,targets[i].mlp,cases[i]['chains'],cases[i]['windows'],initial,host.pack_chain_input,host.parse_chain_output))
            independent=forward()
        assert torch.equal(software,independent) and clean()
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (ValueError,RuntimeError,MemoryError):rejected.append(label)
        else:raise AssertionError('Invalid scope accepted '+label)
        assert clean()
    for label,selected,mode in [('duplicate',(2,2),'software'),('descending',(3,2),'software'),('BF16',(0,2),'software'),('empty',(),'software'),('PL',SELECTED,'PL')]:
        reject(label,lambda selected=selected,mode=mode:RangeScope(torch,layers,targets,selected,mode,load,initial,host,sink,lambda x:None))
    def execute_bad(loader=load,checkpoint=lambda x:None,sink_fn=sink):
        with torch.inference_mode(),RangeScope(torch,layers,targets,(2,3),'software',loader,initial,host,sink_fn,checkpoint):forward()
    def failure(i):
        if i==3:raise RuntimeError('Explicit second-layer fixture failure')
        return cases[i]
    reject('second-load',lambda:execute_bad(loader=failure))
    old=targets[3].mlp.fc2.bias;targets[3].mlp.fc2.bias=None
    try:reject('partial-bind',execute_bad)
    finally:targets[3].mlp.fc2.bias=old
    def bad_sink(i,a):
        if i==2:raise RuntimeError('Explicit boundary sink failure')
    reject('sink',lambda:execute_bad(sink_fn=bad_sink))
    def bad_budget(label):
        if label=='layer2:after':raise MemoryError('Explicit memory stop')
    reject('budget',lambda:execute_bad(checkpoint=bad_budget))
    assert clean()
    return dict(actual_frozen_wrappers_encoder_M207=True,synthetic_narrow_weights_and_attention=True,
                selected_layers=list(SELECTED),logical_reference_calls=572,all24_boundaries=True,
                independent_all_bindings_full_output_exact=True,unchanged_BF16_prefix=True,
                dynamic_cumulative_inputs=True,peak_live_layer_scopes=1,restored=True,
                negative_checks=rejected,model_quality_or_performance=False)

if __name__=='__main__':
    print('M426_COMPONENT='+json.dumps(component(Path(sys.argv[1]))),flush=True)
