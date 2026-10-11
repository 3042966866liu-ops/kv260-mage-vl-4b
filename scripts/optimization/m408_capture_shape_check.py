"""Actual fixed-input frozen constructor/forward capture and native-rank replay, WSL CPU."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import weakref
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M408-local-MLP-A8-capture-03'
spec=importlib.util.spec_from_file_location('capture_paths',PKG/'frozen_video_identity.py')
identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity);identity.RELEASE=ROOT
sys.path[:0]=[str(p) for p in identity.module_paths() if p.name!='runtime_site']
import numpy as np
import torch
import contract_runtime
from m273_latest_vision_runtime import M273LatestPSVisionRuntime
from m273_latest_multiscale_contract import preprocess
from m206_ps_vision_runtime import M206ProgressLayer
from ps_vision_runtime import M196PrecisionBoundary
from m408_target03 import resolve_target
from m408_mlp_capture04 import Capture,qdq_matrix
frames=[]
for name,digest in identity.FRAMES.items():
    path=ROOT/'release_staging/m328_release_video_addon_20260926_v3/fixtures'/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    frames.append(np.load(path,allow_pickle=False))
stack=np.ascontiguousarray(np.stack(frames));assert hashlib.sha256(stack.tobytes()).hexdigest()==identity.STACK_SHA
tensors=preprocess(np.ascontiguousarray(stack[-1:]))
base=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
owner=weakref.ref(runtime)
leaf,topology=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
with Capture(leaf.mlp,norm=leaf.layer_norm2) as captured:
    visual=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
captured.require_complete()
native={k:[1,*list(v.shape)] for k,v in captured.values.items()}
assert captured.native_shapes==native and captured.restored
with torch.inference_mode():
    x=torch.from_numpy(captured.values['input']).unsqueeze(0)
    with Capture(leaf.mlp) as replay:leaf.mlp(x)
    replay.require_complete()
    assert all(np.array_equal(captured.values[k].view(np.uint32),v.view(np.uint32)) for k,v in replay.values.items())
    batches={}
    def qdq(key,value):
        assert tuple(value.shape)==tuple(native[key])
        arr,rows=qdq_matrix(value.detach().numpy()[0],contract_runtime.quantize_t32)
        batches[key]=rows
        return torch.from_numpy(arr).unsqueeze(0)
    with Capture(leaf.mlp,qdq=qdq) as candidate:leaf.mlp(x)
    candidate.require_complete()
    assert candidate.native_shapes==replay.native_shapes
    assert set(batches)=={'input','gelu'} and all([r['rows'] for r in b]==[32]*12+[8] for b in batches.values())
    assert captured.restored and replay.restored and candidate.restored
result=dict(status='PASS_WSL_ACTUAL_CAPTURE_NATIVE_RANK_REPLAY_COMPONENT',topology=topology,native_shapes=native,
    real_same_input_frozen_MLP_replay_bit_exact=True,original_visual_shape=list(visual.shape),
    original_capture_visual_sha256=hashlib.sha256(visual.tobytes()).hexdigest(),
    original_host_quantizer_two_13_batches=True,original_GELU_preserved=True,hooks_restored=True,
    WSL_not_board=True,local_A8_quality_not_adjudicated=True,performance_pass=False)
del leaf,captured,replay,candidate,x,qdq,visual
runtime.close();runtime=None;gc.collect();result['owner_collected']=owner() is None;assert result['owner_collected']
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print('M408_CAPTURE_SHAPE_CHECK='+json.dumps(result))
