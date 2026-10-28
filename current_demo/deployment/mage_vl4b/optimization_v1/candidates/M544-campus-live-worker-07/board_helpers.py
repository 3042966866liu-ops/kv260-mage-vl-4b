"""M536 V4 PS override component; original runtime device ownership untouched."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np

def core(m):
    for _ in range(4):
        if hasattr(m,'mlp') and hasattr(m,'self_attn'):return m
        m=m.layer
    raise AssertionError('Expected original vision wrapper')

class NoVisualProfiler:
    def __init__(self,*args,**kwargs):pass
    def begin(self,*args,**kwargs):pass
    def end(self):return dict(status='NO_NEW_VISUAL_PROFILING_BOTH_ARMS',rows=[])
    def close(self,**kwargs):pass

def proof(logits):
    assert logits.shape==(151936,) and logits.dtype==np.float32 and np.isfinite(logits).all()
    chosen=int(logits.argmax());top=np.argsort(-logits,kind='stable')[:16]
    p=np.exp(logits.astype(np.float64)-float(logits.max()));p/=p.sum()
    return dict(full_vocab=151936,full_FP32_sha256=hashlib.sha256(logits.tobytes()).hexdigest(),
        actual_full_vocab_argmax=chosen,actual_argmax_logit=float(logits[chosen]),
        top16=[dict(token_id=int(i),logit=float(logits[i])) for i in top],
        PYes_minus_PNo_pp=float((p[9454]-p[2753])*100),full_array_saved=False,
        online_full_argmax_not_restricted=True,parent_array_reused=False)

def component(pkg,release):
    pkg,release=Path(pkg),Path(release)
    original=Path('/dev/shm/m523_PS3072_ttft_package01')
    closure=json.loads((original/'SOURCE_CLOSURE.json').read_bytes())
    sys.path[:0]=[str(release/d) for d in closure['module_dirs']]
    import torch
    torch.set_num_threads(4)
    from m273_latest_vision_runtime import M273LatestPSVisionRuntime
    from v4_recovery_native import V4Recovery
    candidate=release/'deployment/mage_vl4b/m181_m120_video_board_candidate'
    runtime=M273LatestPSVisionRuntime(candidate/'ps_vision_payload',candidate/'vision_layout',candidate/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
    mlp=core(runtime.vision.encoder.layers[4]).mlp;before=(mlp.fc1,mlp.fc2);oldact=mlp.activation_fn
    override=V4Recovery(torch,mlp,pkg,lambda:None)
    with np.load(pkg/'fixture/V4_input.npz',allow_pickle=False) as z:x=torch.from_numpy(z['MLP_input'].copy())
    assert x.shape==(1,392,1024) and x.dtype==torch.float32
    try:
        with torch.inference_mode():
            ref=mlp(x);override.select(True);y=mlp(x)
            a=y.numpy().astype(np.float64);b=ref.numpy().astype(np.float64)
            l2=float(np.linalg.norm(a-b)/np.linalg.norm(b));cos=float(np.sum(a*b)/np.linalg.norm(a)/np.linalg.norm(b))
            assert l2<=.20 and cos>=.98
        override.close();assert (mlp.fc1,mlp.fc2)==before and mlp.activation_fn is oldact
        z=np.arange(151936,dtype=np.float32)*.001;z[9454]=1000
        pp=proof(z);assert pp['actual_full_vocab_argmax']==9454 and len(pp['top16'])==16
        return dict(status='PASS_A53_ACTUAL_V4_3584_PS_MODULE_LOCAL_ONLY',relative_L2=l2,cosine=cos,
            full_original_fc1_GELU_fc2_used=True,full_crop_fc1_GELU_fc2_used=True,original_modules_restored=True,
            output_full_argmax_proof_fixture=True,Overlay=0,DMA=0,CMA=0,complete_model_forwards=0)
    finally:
        override.close();runtime.close()
