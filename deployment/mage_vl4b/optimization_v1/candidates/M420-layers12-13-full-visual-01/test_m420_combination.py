"""Real24 frozen wrappers/MLP execution, explicit synthetic64-wide weights and PL."""
import ast,__future__,json,sys,threading,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np

def component(root):
    import torch
    from m408_target_component04 import actual_class
    from m355_reference import decode_records,full_reference
    from m407_mlp_contract import chain_for
    from test_m409_ftz_reference import actual_host
    from m420_combination import execute
    progress=root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py'
    boundary=root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py'
    model=root/'deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/modeling_mage_vl.py'
    p=actual_class(torch,progress,'M206ProgressLayer',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time))
    b=actual_class(torch,boundary,'M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    cls=next(n for n in ast.parse(model.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='MageVLVisionEncoderLayer')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward');ns={}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(model),'exec',flags=__future__.annotations.compiler_flag),ns)
    class Attention(torch.nn.Module):
        def forward(self,hidden_states,**unused):return hidden_states*.125,None
    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__();self.fc1=torch.nn.Linear(64,64);self.fc2=torch.nn.Linear(64,64)
        def forward(self,x):return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__();self.mlp=MLP();self.layer_norm1=torch.nn.LayerNorm(64);self.layer_norm2=torch.nn.LayerNorm(64);self.self_attn=Attention()
        forward=ns['forward']
    torch.manual_seed(420);layers=torch.nn.ModuleList()
    for index in range(24):
        inner=Encoder();dtype=torch.bfloat16 if index<2 else torch.float32;inner.to(dtype)
        layers.append(p(b(inner,dtype,torch.bfloat16),index=index,heartbeat_seconds=30.,run_elapsed=lambda:0.))
    targets={i:layers[i].layer.layer for i in (12,13)};cases={}
    linear=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    for index in targets:
        tile=dict(tile_index=0,row_start=0,valid_rows=64,rows_per_shard=16,shard_offsets=[0]*4,record_bytes_per_shard=544)
        chains={k:chain_for(dict(module=k,shape=[64,64],input_groups=1,bits=4,tiles=[tile]),index*2+j) for j,k in enumerate(('fc1','fc2'))}
        window=(np.full(8,.0234375 if index==12 else .03125,'<f2').tobytes()+bytes([0x99])*256)*2
        codes,scales=decode_records(window,1,16,4);weight=np.tile((codes.astype(np.float32)*scales.astype(np.float32)[...,None]).reshape(16,64),(4,1))
        class Store:
            def __init__(self,w):self.w=w
            def decode(self,name):return self.w.copy()
        for k in chains:
            mod=linear(torch,Store(weight),k,64,64,True,torch.float32);mod.bias=torch.nn.Parameter(torch.arange(64,dtype=torch.float32)*(.0001*index),requires_grad=False);setattr(targets[index].mlp,k,mod)
        cases[index]=dict(chains=chains,windows={k:[window]*4 for k in chains},capture_shapes={k:(392,64) for k in ('residual','input','fc1','gelu','fc2','output')})
    host,initial=actual_host(root)
    def forward():
        x=(torch.arange(392*64).reshape(1,392,64).float()*.00013).to(torch.bfloat16)
        for layer in layers:x=layer(x)[0]
        return x
    calls=[];stages=[]
    def submit(index,part,c,start,shift,packet):
        calls.append((index,part,start,shift));return full_reference(c,cases[index]['windows'][part],c['stage_base_words'],packet)
    with torch.inference_mode():
        original,cap_a,_=execute(torch,forward,targets,cases,initial,host,'original')
        software,cap_s,evidence=execute(torch,forward,targets,cases,initial,host,'software')
        pl,cap_b,p=execute(torch,forward,targets,cases,initial,host,'PL',stage=lambda i,k,c:stages.append((i,k)),submit=submit,expected=evidence['software_wire'])
    assert torch.equal(software,pl) and not torch.equal(original,software)
    assert len(calls)==52 and stages==[(12,'fc1'),(12,'fc2'),(13,'fc1'),(13,'fc2')]
    assert np.array_equal(cap_a[12]['input'],cap_s[12]['input'])
    assert not np.array_equal(cap_a[13]['input'],cap_s[13]['input'])
    assert all(np.array_equal(cap_s[i][k],cap_b[i][k]) for i in targets for k in cap_s[i])
    def clean():return all('forward' not in getattr(layers[i].layer.layer.mlp,k).__dict__ for i in range(24) for k in ('fc1','fc2')) and all(not l.layer.layer.layer_norm2._forward_hooks and not l.layer.layer.mlp._forward_hooks for l in layers)
    assert clean();rejects=0
    def bad_submit(index,*args):
        if index==13:raise RuntimeError('EXPLICIT second-layer submission failure')
        return submit(index,*args)
    with torch.inference_mode():
        try:execute(torch,forward,targets,cases,initial,host,'PL',stage=lambda *unused:None,submit=bad_submit,expected=evidence['software_wire'])
        except RuntimeError:rejects+=1
        else:raise AssertionError('Second layer failure ignored')
    assert clean()
    for bad in (None,{12:evidence['software_wire'][12]}):
        try:execute(torch,forward,targets,cases,initial,host,'PL',stage=lambda *unused:None,submit=submit,expected=bad)
        except ValueError:rejects+=1
        else:raise AssertionError('Missing dynamic layer13 reference accepted')
    assert clean()
    old=targets[13].mlp.fc2.bias;targets[13].mlp.fc2.bias=None
    try:
        try:execute(torch,forward,targets,cases,initial,host,'PL',stage=lambda *unused:None,submit=submit,expected=evidence['software_wire'])
        except RuntimeError:rejects+=1
        else:raise AssertionError('Second partial entry failure ignored')
    finally:targets[13].mlp.fc2.bias=old
    assert clean()
    return dict(actual_frozen24_wrappers_encoder_M207=True,selected_layers=[12,13],only_four_instance_forwards=True,
        dynamic_layer13_input_changed=True,whole_software_PL_output_bit_equal=True,all_captures_bit_equal=True,
        complete52_packets_raw_exact=True,four_windows_staged_in_layer_order=True,partial_entry_and_second_layer_failure_restore=True,
        negative_checks=rejects,weights_attention_DMA_explicit_synthetic=True,board_quality_or_performance=False)

if __name__=='__main__':print('M414_COMPONENT='+json.dumps(component(Path(sys.argv[1]))),flush=True)
