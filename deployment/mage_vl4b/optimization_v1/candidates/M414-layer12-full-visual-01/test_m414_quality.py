"""Real Torch24-wrapper fixture; synthetic attention/weights/PL, no model claim."""
import ast, __future__, hashlib, json, sys, threading, time, tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M409-saved-MLP-reference-01'
sys.path.insert(0,str(OLD))
from m414_quality import tensor, visual_quality, VisualChecks, save_features
from m414_policy import MemoryBudget

def component(root=ROOT):
    import torch
    from m408_target_component04 import actual_class
    from m408_mlp_capture04 import Capture
    from m411_mlp_binding import PLMLPBinding
    from m409_ftz_reference import SoftwareMLPBinding
    from test_m409_ftz_reference import actual_host
    from m355_reference import decode_records,full_reference
    from m407_mlp_contract import chain_for
    progress=root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py'
    boundary=root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py'
    model=root/'deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/modeling_mage_vl.py'
    p=actual_class(torch,progress,'M206ProgressLayer',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time))
    b=actual_class(torch,boundary,'M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    cls=next(n for n in ast.parse(model.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='MageVLVisionEncoderLayer')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward')
    ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(model),'exec',flags=__future__.annotations.compiler_flag),ns)
    class AttentionFixture(torch.nn.Module):
        def forward(self,hidden_states,**unused):return hidden_states*.125,None
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__();self.mlp=torch.nn.Sequential()
            class MLP(torch.nn.Module):
                def __init__(self):
                    super().__init__();self.fc1=torch.nn.Linear(64,64);self.fc2=torch.nn.Linear(64,64)
                def forward(self,x):return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
            self.mlp=MLP();self.layer_norm1=torch.nn.LayerNorm(64);self.layer_norm2=torch.nn.LayerNorm(64);self.self_attn=AttentionFixture()
        forward=ns['forward']
    torch.manual_seed(413);layers=torch.nn.ModuleList()
    for i in range(24):
        inner=Encoder();dtype=torch.bfloat16 if i<2 else torch.float32;inner.to(dtype)
        layers.append(p(b(inner,dtype,torch.bfloat16),index=i,heartbeat_seconds=30.,run_elapsed=lambda:0.))
    mlp=layers[12].layer.layer.mlp
    linear=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    tile=dict(tile_index=0,row_start=0,valid_rows=64,rows_per_shard=16,shard_offsets=[0]*4,record_bytes_per_shard=544)
    chains={k:chain_for(dict(module=k,shape=[64,64],input_groups=1,bits=4,tiles=[tile]),i) for i,k in enumerate(('fc1','fc2'))}
    window=(np.full(8,.03125,'<f2').tobytes()+bytes([0x99])*256)*2;windows={k:[window]*4 for k in chains}
    codes,scales=decode_records(window,1,16,4);weight=np.tile((codes.astype(np.float32)*scales.astype(np.float32)[...,None]).reshape(16,64),(4,1))
    class Store:
        def decode(self,name):return weight.copy()
    for k in chains:
        mod=linear(torch,Store(),k,64,64,True,torch.float32);mod.bias=torch.nn.Parameter(torch.arange(64,dtype=torch.float32)*.0001,requires_grad=False);setattr(mlp,k,mod)
    host,initial=actual_host(root);vision=SimpleNamespace(encoder=SimpleNamespace(layers=layers))
    phase=['original'];points=[];baseline=dict(VmRSS=10<<20,MemAvailable=2<<30,CmaFree=0);budget=MemoryBudget(baseline,lambda:dict(baseline))
    shapes={k:(392,64) for k in ('residual','input','fc1','gelu','fc2','output')}
    def forward():
        x=(torch.arange(392*64).reshape(1,392,64).float()*.00013).to(torch.bfloat16)
        for layer in layers:x=layer(x)[0]
        return x
    staged=[];calls=[];saved={}
    with torch.inference_mode():
        with VisualChecks(vision,budget,points,phase) as checks:
            with Capture(mlp,norm=layers[12].layer.layer.layer_norm2,shapes=shapes) as capture:forward()
        capture.require_complete();assert checks.restored and capture.restored and len(points)==48
        before=capture.values['input'].copy()
        software=SoftwareMLPBinding(torch,mlp,chains,windows,initial,host.pack_chain_input,host.parse_chain_output,
                                   raw_sink=lambda part,start,shift,packet,raw:saved.update({(part,start,shift):(packet,raw)}))
        with software:expected=forward()
        phase[0]='candidate'
        def submit(part,c,start,shift,packet):
            calls.append((part,start,shift));return full_reference(c,windows[part],c['stage_base_words'],packet)
        binding=PLMLPBinding(torch,mlp,chains,initial,host,lambda part,c:staged.append(part),submit,saved)
        with VisualChecks(vision,budget,points,phase) as checks:
            with Capture(mlp,norm=layers[12].layer.layer.layer_norm2,shapes=shapes) as capture:
                with binding:answer=forward()
        capture.require_complete();assert checks.restored and capture.restored and binding.restored
        assert torch.equal(answer,expected) and np.array_equal(capture.values['input'],before)
        assert len(points)==96 and len(calls)==26 and staged==['fc1','fc2']
    assert all('forward' not in getattr(layers[i].layer.layer.mlp,k).__dict__ for i in range(24) for k in ('fc1','fc2'))
    rejected=0
    def fail(*unused):raise MemoryError('EXPLICIT boundary admission failure')
    broken=MemoryBudget(baseline,fail)
    try:
        with VisualChecks(vision,broken,[],phase) as checks:forward()
    except MemoryError:rejected+=1
    else:raise AssertionError('Admission fault ignored')
    assert checks.restored and all(not l._forward_hooks and not l._forward_pre_hooks for l in layers)
    rng=np.random.default_rng(413);reference=rng.normal(size=(98,2560)).astype(np.float32)
    assert visual_quality(reference,reference)['feature_screen_pass']
    with tempfile.TemporaryDirectory() as temp:
        saved_features=save_features(Path(temp),dict(original=reference,candidate=reference))
        assert len(saved_features)==2 and all(x['file_bytes']==1003648 for x in saved_features)
        assert all(np.array_equal(np.load(Path(temp)/x['path'],allow_pickle=False),reference) for x in saved_features)
        try:save_features(Path(temp),dict(original=reference,candidate=reference))
        except RuntimeError:rejected+=1
        else:raise AssertionError('Retained original features overwritten')
    for value in (-reference,reference*1.1):assert not visual_quality(reference,value)['feature_screen_pass'];rejected+=1
    for value in (reference.astype(np.float64),reference[:97],reference*float('nan'),np.zeros_like(reference)):
        try:visual_quality(reference,value)
        except ValueError:rejected+=1
        else:raise AssertionError('Wrong feature contract accepted')
    assert tensor(np.int64(2))['shape']==[1]
    now=dict(baseline,VmRSS=(10+769)<<20)
    try:MemoryBudget(baseline,lambda:now).check('above768')
    except MemoryError:rejected+=1
    else:raise AssertionError('Growth limit ignored')
    assert MemoryBudget(baseline,lambda:dict(baseline,VmRSS=(10+300)<<20)).check('above256')['CmaFree']==0
    return dict(actual_frozen24_wrappers_encoder_and_M207=True,first2_BF16_preserved=True,
                selected_layer12_only=True,real_Torch392_row_software_reference_equal=True,
                complete26_packets_raw_exact=True,all96_boundary_points=True,
                restored_hooks_and_binding=True,negative_checks=rejected,
                attention_weights_submit_and_memory_explicit_fixtures=True,
                board_quality_capacity_or_performance=False,
                source_sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (progress,boundary,model)})

if __name__=='__main__':
    result=component(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT)
    assert 'pynq' not in sys.modules
    print('M414_COMPONENT='+json.dumps(result))
