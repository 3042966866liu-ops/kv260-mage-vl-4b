"""M536 isolated V4 recovery; original splits, no board access."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
PROTOCOL=RUNS/'M536-V4-3584-recovery-protocol-01/RESULT.json'
FIT=RUNS/'M536-V4-3584-recovery-fit-01'
PKG=OPT/'candidates/M536-V4-3584-recovery-01'
REL=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
PARENT=OPT/'candidates/M534-visual-profile-board-02'
COMPONENT=OPT/'candidates/M523-PS3072-ttft01'

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def digest(x):return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def npz(p,**v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:np.savez_compressed(f,**v)
def verify():
    p=read(PROTOCOL)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    return p
def metric(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64);assert a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    return dict(relative_L2=float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-30)),
        cosine=float(np.sum(a*b)/max(np.linalg.norm(a)*np.linalg.norm(b),1e-30)))
def passes(metrics):return all(r['relative_L2']<=.20 and r['cosine']>=.98 for r in metrics)
def core(m):
    for _ in range(4):
        if hasattr(m,'mlp') and hasattr(m,'self_attn'):return m
        m=m.layer
    raise AssertionError('Original PS wrapper required')
def cpu_setup():
    import torch
    torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(536)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    closure=read(COMPONENT/'SOURCE_CLOSURE.json')
    sys.path[:0]=[str(PARENT),str(COMPONENT)]+[str(REL/d) for d in closure['module_dirs'] if d!='runtime_site']
    from m273_latest_vision_runtime import M273LatestPSVisionRuntime
    from PS_crop_native import PSCropSelector
    from visual_cache_profiler import CacheAB
    from board_subset import VisionSubset
    from m273_latest_multiscale_contract import preprocess
    candidate=REL/'deployment/mage_vl4b/m181_m120_video_board_candidate'
    runtime=M273LatestPSVisionRuntime(candidate/'ps_vision_payload',candidate/'vision_layout',candidate/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    crop=PSCropSelector(torch,runtime,COMPONENT,idle=lambda:None);crop.choose('B')
    cache=CacheAB(crop);cache.begin('B')
    subset=VisionSubset(torch,runtime,read(PARENT/'DEMO_BOARD_PLAN.json')['retained_vision'],lambda:None);subset.select(True)
    return torch,runtime,crop,subset,preprocess

class PrefixComplete(Exception):pass

def prefix_input(torch,runtime,mlp,preprocess,frame):
    captured=[]
    def grab(module,args):
        x=args[0];assert tuple(x.shape)==(1,392,1024) and x.dtype==torch.float32
        captured.append(x.detach().clone());raise PrefixComplete()
    h=mlp.register_forward_pre_hook(grab)
    a=preprocess(np.ascontiguousarray(frame[None]))
    assert a['pixel_values'].shape==(392,768) and int(a['merged_visual_tokens'])==98
    try:
        with torch.inference_mode():runtime.vision(torch.from_numpy(a['pixel_values']).to(runtime.compute_dtype),grid_thw=torch.from_numpy(a['image_grid_thw']),patch_positions=torch.from_numpy(a['patch_positions']))
    except PrefixComplete:pass
    else:raise AssertionError('V4 prefix must stop before MLP')
    finally:h.remove()
    assert len(captured)==1
    return captured[0]
