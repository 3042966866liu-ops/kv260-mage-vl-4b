"""Actual frozen wrapper/encoder forward checks with explicit small attention fixture."""
import ast
import __future__
import hashlib
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from m408_mlp_capture import Capture
from m408_target03 import resolve_target


def check(torch, progress_cls, boundary_cls, encoder_forward):
    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.fc1=torch.nn.Linear(64,128); self.fc2=torch.nn.Linear(128,64)
        def forward(self,x): return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
    class AttentionFixture(torch.nn.Module):
        def forward(self,hidden_states,**unused): return hidden_states*.125,None
    class MageVLVisionEncoderLayer(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.mlp=MLP(); self.layer_norm1=torch.nn.LayerNorm(64)
            self.layer_norm2=torch.nn.LayerNorm(64); self.self_attn=AttentionFixture()
    MageVLVisionEncoderLayer.forward=encoder_forward
    inner=MageVLVisionEncoderLayer()
    boundary=boundary_cls(inner,torch.float32,torch.bfloat16)
    outer=progress_cls(boundary,index=12,heartbeat_seconds=30.,run_elapsed=lambda:0.)
    vision=SimpleNamespace(encoder=SimpleNamespace(layers=[None]*12+[outer]+[None]*11))
    target,evidence=resolve_target(vision,progress_cls,boundary_cls,torch)
    assert target is inner
    shapes={k:(3,128 if k in ('fc1','gelu') else 64) for k in ('residual','input','fc1','gelu','fc2','output')}
    with torch.inference_mode():
        values=(torch.arange(192,dtype=torch.float32).reshape(3,64)*.013).to(torch.bfloat16)
        original=outer(values)[0]
        with Capture(target.mlp,norm=target.layer_norm2,shapes=shapes) as capture: answer=outer(values)[0]
        capture.require_complete()
        assert torch.equal(original,answer) and capture.restored
        assert torch.equal(answer,torch.from_numpy(capture.values['residual']+capture.values['output']).to(torch.bfloat16))
    rejects=0
    for modify,restore in (
        (lambda:setattr(boundary,'output_dtype',torch.float32),lambda:setattr(boundary,'output_dtype',torch.bfloat16)),
        (lambda:setattr(boundary,'target_dtype',torch.bfloat16),lambda:setattr(boundary,'target_dtype',torch.float32)),
        (lambda:setattr(outer,'index',11),lambda:setattr(outer,'index',12)),
        (lambda:vision.encoder.layers.__setitem__(12,boundary),lambda:vision.encoder.layers.__setitem__(12,outer))):
        try:
            modify()
            try:resolve_target(vision,progress_cls,boundary_cls,torch)
            except RuntimeError:rejects+=1
            else:raise AssertionError('Wrong wrapper topology accepted')
        finally:restore()
    return dict(actual_frozen_wrappers_and_encoder_forward=True,target_path='encoder.layers.12.layer.layer',
                original_capture_bit_exact=True,hooks_restored=True,residual_reference_exact=True,
                topology_rejects=rejects,topology=evidence,attention_and_weights_explicit_fixture=True,
                real_model_or_PL_evidence=False)


def actual_class(torch,source,name,namespace):
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    node=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(source),'exec',
                 flags=__future__.annotations.compiler_flag),namespace)
    return namespace[name]


def from_sources(torch,root):
    progress=root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py'
    boundary=root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py'
    encoder=root/'deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/modeling_mage_vl.py'
    ns=dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time)
    p=actual_class(torch,progress,'M206ProgressLayer',ns)
    b=actual_class(torch,boundary,'M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    node=next(x for x in ast.parse(encoder.read_text(encoding='utf-8-sig')).body if isinstance(x,ast.ClassDef) and x.name=='MageVLVisionEncoderLayer')
    fn=next(x for x in node.body if isinstance(x,ast.FunctionDef) and x.name=='forward')
    ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(encoder),'exec',flags=__future__.annotations.compiler_flag),ns)
    result=check(torch,p,b,ns['forward'])
    result['sources']={x.relative_to(root).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in (progress,boundary,encoder)}
    return result


if __name__=='__main__':
    import json
    import torch
    print('M408_TARGET_JSON='+json.dumps(from_sources(torch,Path(__file__).resolve().parents[2])))
