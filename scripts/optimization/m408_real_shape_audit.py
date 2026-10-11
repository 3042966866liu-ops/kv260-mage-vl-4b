"""Exact original frozen PS visual forward: six hook shapes, no candidate math."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import weakref
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M408-local-MLP-A8-capture-03'
spec=importlib.util.spec_from_file_location('shape_paths',PKG/'frozen_video_identity.py')
identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity);identity.RELEASE=ROOT
sys.path[:0]=[str(p) for p in identity.module_paths() if p.name!='runtime_site']
import numpy as np
import torch
from m273_latest_vision_runtime import M273LatestPSVisionRuntime
from m273_latest_multiscale_contract import preprocess
from m206_ps_vision_runtime import M206ProgressLayer
from ps_vision_runtime import M196PrecisionBoundary
from m408_target03 import resolve_target
frames=[]
for name,digest in identity.FRAMES.items():
    path=ROOT/'release_staging/m328_release_video_addon_20260926_v3/fixtures'/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    frames.append(np.load(path,allow_pickle=False))
stack=np.ascontiguousarray(np.stack(frames));assert hashlib.sha256(stack.tobytes()).hexdigest()==identity.STACK_SHA
tensors=preprocess(np.ascontiguousarray(stack[-1:]))
base=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
owner=weakref.ref(runtime);handles=[];records={}
leaf,topology=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
def note(key,value):
    assert key not in records
    records[key]=dict(shape=list(value.shape),dtype=str(value.dtype),finite=bool(torch.isfinite(value).all()))
def pre(key):
    def hook(module,args):note(key,args[0])
    return hook
def post(key):
    def hook(module,args,result):note(key,result)
    return hook
before=[(m,tuple(m._forward_pre_hooks),tuple(m._forward_hooks)) for m in (leaf.layer_norm2,leaf.mlp.fc1,leaf.mlp.fc2,leaf.mlp)]
try:
    for module,key in ((leaf.layer_norm2,'residual'),(leaf.mlp.fc1,'input'),(leaf.mlp.fc2,'gelu')):handles.append(module.register_forward_pre_hook(pre(key)))
    for module,key in ((leaf.mlp.fc1,'fc1'),(leaf.mlp.fc2,'fc2'),(leaf.mlp,'output')):handles.append(module.register_forward_hook(post(key)))
    output=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
finally:
    for handle in handles:handle.remove()
assert all(tuple(m._forward_pre_hooks)==a and tuple(m._forward_hooks)==b for m,a,b in before)
assert set(records)=={'residual','input','fc1','gelu','fc2','output'}
for k,r in records.items():assert r==dict(shape=[1,392,4096 if k in ('fc1','gelu') else 1024],dtype='torch.float32',finite=True)
result=dict(status='PASS_ACTUAL_ORIGINAL_FORWARD_SHAPE_ONLY',topology=topology,records=records,model_forward_calls=1,
    hooks_restored=True,WSL_not_target_board=True,local_A8_screen_pass=False,performance_pass=False,
    visual=dict(shape=list(output.shape),dtype=str(output.dtype),sha256=hashlib.sha256(output.tobytes()).hexdigest()))
del leaf,module,before,output
runtime.close();runtime=None;gc.collect();result['owner_collected']=owner() is None;assert result['owner_collected']
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print('M408_REAL_SHAPE_AUDIT='+json.dumps(result))
