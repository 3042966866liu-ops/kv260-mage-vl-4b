"""Read-only actual frozen visual constructor audit, WSL CPU; no forward or PL."""
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import weakref
from m416_target13 import resolve_target,verify_matrices

ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M408-local-MLP-A8-capture-04'
spec=importlib.util.spec_from_file_location('frozen_paths_audit',PKG/'frozen_video_identity.py')
identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
identity.RELEASE=ROOT
# runtime_site contains board-only wheel fragments; use actual WSL packages for this CPU-only audit.
sys.path[:0]=[str(p) for p in identity.module_paths() if p.name!='runtime_site']
import torch
from m273_latest_vision_runtime import M273LatestPSVisionRuntime
from m207_ps_vision_runtime import M207FP32GemmW4Linear
from m206_ps_vision_runtime import M206ProgressLayer
from ps_vision_runtime import M196PrecisionBoundary

ids={x['path']:x for x in json.loads((PKG/'M348_SOURCE_IDENTITIES.json').read_bytes())['files']}
sources={}
for name in ('ps_vision_runtime','m206_ps_vision_runtime','m207_ps_vision_runtime','m222_vectorized_w4_runtime',
             'm258_vectorized_w4_runtime','m259_variable_vision_runtime','m260_cached_w4_runtime',
             'm261_budgeted_w4_runtime','m273_latest_vision_runtime'):
    p=Path(sys.modules[name].__file__).resolve();rel=p.relative_to(ROOT).as_posix()
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest==ids[rel]['sha256'],(name,rel)
    sources[name]=dict(path=rel,sha256=digest)
base=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
runtime=None
try:
    runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    owner=weakref.ref(runtime)
    assert runtime.compute_dtype==torch.bfloat16 and len(runtime.vision.encoder.layers)==24
    outer=runtime.vision.encoder.layers[13];boundary=outer.layer;leaf=boundary.layer
    assert type(outer) is M206ProgressLayer and outer.index==13
    assert type(boundary) is M196PrecisionBoundary
    assert boundary.target_dtype==torch.float32 and boundary.output_dtype==torch.bfloat16
    assert type(leaf).__name__=='MageVLVisionEncoderLayer'
    checked,topology=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
    assert checked is leaf
    matrices={}
    for part,shape in (('fc1',(1024,4096)),('fc2',(4096,1024))):
        mod=getattr(leaf.mlp,part)
        assert type(mod) is M207FP32GemmW4Linear
        assert mod.name==f'encoder.layers.13.mlp.{part}'
        assert (mod.in_features,mod.out_features)==shape and mod.output_dtype==torch.float32
        assert mod.bias is not None and mod.bias.dtype==torch.float32 and tuple(mod.bias.shape)==(shape[1],)
        assert runtime.store.entries[mod.name]['module']==f'model.visual.{mod.name}'
        matrices[part]=dict(name=mod.name,in_features=mod.in_features,out_features=mod.out_features,
            output_dtype=str(mod.output_dtype),bias_dtype=str(mod.bias.dtype),bias_shape=list(mod.bias.shape),
            bias_sha256=hashlib.sha256(mod.bias.detach().numpy().tobytes()).hexdigest())
    assert verify_matrices(leaf,M207FP32GemmW4Linear,torch)==matrices
    result=dict(status='PASS_ACTUAL_FROZEN_CONSTRUCTOR_CPU_METADATA',sources=sources,
        compute_dtype=str(runtime.compute_dtype),target_dtype=str(boundary.target_dtype),output_dtype=str(boundary.output_dtype),
        progress=type(outer).__name__,precision=type(boundary).__name__,encoder=type(leaf).__name__,matrices=matrices,
        model_forward_calls=0,overlay_loaded=False,dma_allocations=0,WSL_not_board=True)
    result['topology']=topology
    del mod,outer,boundary,leaf,checked
    runtime.close();runtime=None;gc.collect()
    result['owner_collected']=owner() is None
    assert result['owner_collected']
    if len(sys.argv)==2:
        target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print('M416_CONSTRUCTOR_JSON='+json.dumps(result))
finally:
    if runtime is not None:runtime.close()
