"""M537 matched V4 recovery causality study. No board/optimizer actions."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
OPT=ROOT/'deployment/mage_vl4b/optimization_v1';RUNS=OPT/'runs'
PROTO=RUNS/'M537-V4-matched-ablation-protocol-01/RESULT.json'
BASE=ROOT/'experiments/v4_recovery_20261025'
FIT=RUNS/'M536-V4-3584-recovery-fit-01'
PARENT=OPT/'candidates/M534-visual-profile-board-02'
HEAD=OPT/'candidates/M523-fixed-demo-subset-board-07'
REUSE=RUNS/'M537-V4-parent-child-reuse-01'
OUT=RUNS/'M537-V4-matched-ablation-quality-01'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf8').write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def npz(p,**v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:np.savez_compressed(f,**v)
def verify():
    p=read(PROTO)
    for n,h in p['frozen'].items():assert sha(ROOT/n)==h,n
    return p
def classify(text):return {'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(text.strip().casefold().rstrip('.,!?;:'),'Invalid')
def metrics(z,expected):
    p=np.exp(z.astype(np.float64)-float(z.max()));p/=p.sum()
    return float((p[9454]-p[2753])*(1 if expected=='Yes' else -1)*100)
def core(layer):
    for _ in range(4):
        if hasattr(layer,'mlp') and hasattr(layer,'self_attn'):return layer
        layer=layer.layer
    raise AssertionError('Original visual wrapper required')
