"""M541 explicitly authorized fixed-demonstration adaptation, not generic accuracy."""
import sys,json,hashlib,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
SOURCE=RUNS/'M541-demo-adaptation-sources-01/RESULT.json'
FRAMES=RUNS/'M541-demo-adaptation-frames-01'
PROTO=RUNS/'M541-demo-adaptation-protocol-01/RESULT.json'
CAP=RUNS/'M541-demo-adaptation-capture-01'
FIT=RUNS/'M541-demo-adaptation-fit-01'
RELOAD=RUNS/'M541-demo-adaptation-reload-01'
HEAD=OPT/'candidates/M523-fixed-demo-subset-board-07'
BODY=OPT/'candidates/M536-V4-3584-recovery-01'
PARENT=OPT/'candidates/M534-visual-profile-board-02'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def npz(p,**v):
    with p.open('xb') as f:np.savez_compressed(f,**v)
def verify(file=PROTO):
    p=read(file)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    return p
def core(m):
    for _ in range(4):
        if hasattr(m,'mlp') and hasattr(m,'self_attn'):return m
        m=m.layer
    raise AssertionError('Original visual layer required')
def classify(s):return {'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(s.strip().casefold().rstrip('.,!?;:'),'Invalid')
def decision(z,target,tokenizer):
    assert z.shape==(151936,) and z.dtype==np.float32 and np.isfinite(z).all()
    i=int(z.argmax());text=tokenizer.decode([i],skip_special_tokens=True);a=classify(text)
    other=z.copy();other[target]=-np.inf
    return dict(token_id=i,raw_token=text,actual=a,correct=a==('Yes' if target==9454 else 'No'),
        target_gap=float(z[target])-float(other.max()),logits_raw_sha256=digest(z))
def setup_engine():
    sys.path.insert(0,str(ROOT/'experiments/augmented_student_20261025'))
    from common_joint import engine_class
    base=read(RUNS/'M525-joint-augmented-student-128-protocol-02/RESULT.json')
    return engine_class()(base['runtime_protocol'])
def forward(e,frame,ids):
    torch=e.torch
    import m273_latest_multiscale_contract as m273
    a=m273.preprocess(np.ascontiguousarray(frame[None]));assert a['pixel_values'].shape==(392,768)
    x={k:torch.from_numpy(v.copy()) for k,v in a.items()};before=dict(e.counts);e.oracle.trace=[];hidden={}
    def observe(module,args):hidden['x']=args[0].detach().float().cpu().numpy().reshape(-1,2560)[-1:].copy()
    hook=e.model.lm_head.register_forward_pre_hook(observe,prepend=True)
    try:
        with torch.inference_mode():
            f=e.vision(a['pixel_values'],a['image_grid_thw'],a['patch_positions']);assert f.shape==(98,2560) and np.isfinite(f).all()
            pl=set(e.v)&set(range(13,24));assert len(e.oracle.trace)==26*len(pl) and {r['layer'] for r in e.oracle.trace}==pl
            e.injected=dict(features=torch.from_numpy(f.copy()),pixels=x['pixel_values'].to(e.visual.embeddings.patch_embedding.weight.dtype),grid=x['image_grid_thw'],positions=x['patch_positions'])
            e.visual_calls=0;cache=e.DynamicCache(config=e.model.config.text_config);assert cache.get_seq_length()==0
            try:
                output=e.model(**x,input_ids=torch.tensor([ids]),attention_mask=torch.ones((1,128),dtype=torch.long),past_key_values=cache,use_cache=True,logits_to_keep=1)
                assert output.past_key_values is cache and cache.get_seq_length()==128 and len(cache.layers)==len(e.l)
                z=output.logits[0,-1].float().cpu().numpy().copy();h=hidden.pop('x')[0]
            finally:e.discard(torch,cache)
        assert cache.get_seq_length()==0 and e.visual_calls==1
        for branch,size,active in [('vision',24,e.v),('language',36,e.l)]:
            assert all(e.counts.get(branch+'_'+str(i).zfill(2),0)-before.get(branch+'_'+str(i).zfill(2),0)==int(i in active) for i in range(size))
        assert z.shape==(151936,) and h.shape==(2560,) and np.isfinite(z).all() and np.isfinite(h).all();e.unchanged()
        return h,z,f
    finally:hook.remove()
