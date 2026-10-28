"""Frozen, offline PS-MLP pruning experiment; no board APIs."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np

sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OPT=ROOT/'deployment/mage_vl4b/optimization_v1'
R=OPT/'runs'
PREFIX='M523-PS-V2-V3-V6-3072'
PREP=R/(PREFIX+'-protocol-01')
FIT=R/(PREFIX+'-fit-01')
FEATURES=R/(PREFIX+'-features-01')
QUALITY=R/(PREFIX+'-quality-01')
PACKAGE=OPT/'candidates/M523-M455-twentytwo-layer-R1-research-240'
RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
PARENT=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'
CLOSURE=OPT/'candidates/J1-request-native-reference-03/SOURCE_CLOSURE.json'
sys.path[:0]=[str(ROOT/'experiments/speed_target_30s_20261020'),str(ROOT/'experiments/adaptive_exec_error'),
    str(ROOT/'deployment/mage_vl4b/scripts'),str(ROOT/'scripts/optimization')]

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for b in iter(lambda:stream.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def array(p,a):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:np.save(stream,a,allow_pickle=False)
def relative(p):return Path(p).relative_to(ROOT).as_posix()
def files(root):return [dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(root.rglob('*')) if p.is_file()]
def verify():
    p=read(PREP/'RESULT.json')
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    return p
def check_files(root):
    v=read(root/'RESULT.json');assert v['original_rc']==0
    for row in v['files']:assert sha(root/row['path'])==row['sha256'],row['path']
    return v
def metric(a,b):
    a=np.asarray(a,np.float64).reshape(-1,a.shape[-1]);b=np.asarray(b,np.float64).reshape(a.shape)
    assert np.isfinite(a).all() and np.isfinite(b).all()
    return dict(relative_L2=float(np.linalg.norm(a-b)/np.linalg.norm(b)),
        global_cosine=float(np.sum(a*b)/np.linalg.norm(a)/np.linalg.norm(b)),
        min_token_cosine=float(np.min(np.sum(a*b,axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)))))
def setup():
    import torch,transformers,PIL,tokenizers
    torch.set_num_threads(8);torch.set_num_interop_threads(1);torch.manual_seed(523)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    c=read(CLOSURE)
    sys.path[1:1]=[str(RELEASE/d) for d in c['module_dirs'] if d!='runtime_site']
    from m273_latest_vision_runtime import M273LatestPSVisionRuntime
    from m207_ps_vision_runtime import M207FP32GemmW4Linear
    from m276_prompt_contract import preprocess
    for name,path in c['modules'].items():
        if name in sys.modules:assert Path(sys.modules[name].__file__).resolve()==(RELEASE/path).resolve(),name
    runtime=M273LatestPSVisionRuntime(PARENT/'ps_vision_payload',PARENT/'vision_layout',PARENT/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    assert not any(n in sys.modules for n in ('pynq','pyxrt'))
    return torch,runtime,M207FP32GemmW4Linear,preprocess
def inner(runtime,index):
    outer=runtime.vision.encoder.layers[index]
    return outer.layer if index<2 else outer.layer.layer
def inputs(torch,preprocess,request):
    file=ROOT/request['frames'];assert sha(file)==request['frames_sha256']
    frames=np.load(file,allow_pickle=False);assert frames.shape==(2,448,448,3)
    arrays=preprocess(frames[request['timestamp_index']:request['timestamp_index']+1])
    assert arrays['pixel_values'].shape==(392,768)
    return {k:torch.from_numpy(a.copy()) for k,a in arrays.items()}

class CropStore:
    """Exact original W4 decode followed by selected rows/columns; no A8."""
    def __init__(self,dense):self.dense=np.ascontiguousarray(dense,dtype=np.float32)
    def decode(self,name):return self.dense

def replace_PS(torch,runtime,linear_cls,index,z):
    mlp=inner(runtime,index).mlp;old=(mlp.fc1,mlp.fc2)
    assert old[0].output_dtype==old[1].output_dtype==torch.float32
    for part,bias in (('fc1','bias1'),('fc2','bias2')):
        original=getattr(mlp,part);codes=z[part+'_codes'];scales=z[part+'_scales']
        dense=(codes.astype(np.float32)*scales.astype(np.float32)[...,None]).reshape(len(codes),-1)
        new=linear_cls(torch,CropStore(dense),original.name,dense.shape[1],dense.shape[0],True,torch.float32)
        new.bias=torch.nn.Parameter(torch.from_numpy(z[bias].copy()),requires_grad=False)
        assert new.bias.dtype==original.bias.dtype==torch.float32
        setattr(mlp,part,new)
    return mlp,old
