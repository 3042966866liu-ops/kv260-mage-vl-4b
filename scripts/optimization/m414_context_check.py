"""Frozen actual input/runtime CPU context isolation, never a board claim."""
import contextlib,gc,hashlib,importlib.util,json,sys,weakref
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M409-saved-MLP-reference-01'
spec=importlib.util.spec_from_file_location('m414_paths',PKG/'frozen_video_identity.py')
identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity);identity.RELEASE=ROOT
sys.path[:0]=[str(p) for p in identity.module_paths() if p.name!='runtime_site']
sys.path.insert(0,str(PKG));sys.path.insert(0,str(ROOT/'scripts/optimization'))
import numpy as np
import torch
from m273_latest_vision_runtime import M273LatestPSVisionRuntime
from m273_latest_multiscale_contract import preprocess
from m206_ps_vision_runtime import M206ProgressLayer
from ps_vision_runtime import M196PrecisionBoundary
from m408_target03 import resolve_target
from m408_mlp_capture04 import Capture
from m413_quality import tensor
frames=[]
for name,digest in identity.FRAMES.items():
    p=ROOT/'release_staging/m328_release_video_addon_20260926_v3/fixtures'/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    frames.append(np.load(p,allow_pickle=False))
stack=np.ascontiguousarray(np.stack(frames));assert hashlib.sha256(stack.tobytes()).hexdigest()==identity.STACK_SHA
args=preprocess(np.ascontiguousarray(stack[-1:]));base=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');owner=weakref.ref(runtime)
leaf,topology=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
saved=[];values=[]
for mode in ('original-call-boundary','outer-inference-context'):
    with (torch.inference_mode() if mode=='outer-inference-context' else contextlib.nullcontext()):
        with Capture(leaf.mlp,norm=leaf.layer_norm2) as cap:
            answer=runtime(args['pixel_values'],args['image_grid_thw'],args['patch_positions'])
    cap.require_complete();assert cap.restored
    saved.append(dict(mode=mode,visual=tensor(answer),capture={k:tensor(v) for k,v in cap.values.items()}));values.append(answer.copy())
    print('M414_CONTEXT_COMPLETE '+mode,flush=True)
report=dict(status='COMPLETED_WSL_FROZEN_RUNTIME_CONTEXT_ISOLATION',WSL_not_board=True,board_root_cause_proven=False,
    original_source_files_unchanged=True,actual_frozen_runtime_and_input=True,topology=topology,
    full_visual_forward_calls=2,language_forward_calls=0,Overlay_loads=0,
    evidence=saved,visual_bit_equal=bool(np.array_equal(values[0].view(np.uint32),values[1].view(np.uint32))),
    layer12_capture_bit_equal={k:saved[0]['capture'][k]==saved[1]['capture'][k] for k in saved[0]['capture']},
    max_abs=float(np.max(np.abs(values[0].astype(np.float64)-values[1].astype(np.float64)))),
    performance_claim=False)
del leaf,cap,answer,values
runtime.close();runtime=None;gc.collect();report['owner_collected']=owner() is None;assert report['owner_collected']
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True)
with target.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print('M414_CONTEXT_RESULT='+json.dumps(report),flush=True)
