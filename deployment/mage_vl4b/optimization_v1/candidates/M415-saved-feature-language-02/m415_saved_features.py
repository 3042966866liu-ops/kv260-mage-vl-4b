"""Saved feature identity and fixed-input decision consistency, not accuracy."""
import hashlib, io, json, os
from pathlib import Path
import numpy as np

M414_SHA='5733f75049b8bee7aae6da9d8a1cdc451416a637d5a4e7b28c617aa767043408'
FEATURE_DIR=Path('/home/ubuntu/m414_layer12_full_visual_01')

def tensor(x):
    x=np.ascontiguousarray(x)
    if not np.isfinite(x).all():raise ValueError('Nonfinite tensor')
    return dict(shape=list(x.shape),dtype=str(x.dtype),bytes=int(x.nbytes),sha256=hashlib.sha256(x.tobytes()).hexdigest())

def load_features(plan,folder=FEATURE_DIR):
    raw=(folder/'BOARD_RESULT.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=M414_SHA or plan['M414_raw_sha256']!=M414_SHA:raise ValueError('M414 identity differs')
    r=json.loads(raw)
    if r['status']!='PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY' or not r['feature_quality_pass'] or r['gate_return_code']:raise ValueError('M414 quality prerequisite differs')
    rows=r['retained_visual_features']
    if rows!=plan['features'] or [x['path'] for x in rows]!=['original_visual.npy','candidate_visual.npy']:raise ValueError('Feature manifest differs')
    arrays=[];identities=[]
    for row in rows:
        p=folder/row['path'];before=p.lstat()
        if p.is_symlink() or before.st_size!=1003648 or row['file_bytes']!=1003648:raise ValueError('Feature size/symlink differs')
        data=p.read_bytes();after=p.lstat()
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if identity(before)!=identity(after) or hashlib.sha256(data).hexdigest()!=row['file_sha256']:raise ValueError('Feature changed or SHA differs')
        x=np.load(io.BytesIO(data),allow_pickle=False)
        if x.shape!=(98,2560) or x.dtype!=np.float32 or tensor(x)!=row['tensor']:raise ValueError('Feature tensor differs')
        x.flags.writeable=False;arrays.append(x);identities.append(dict(path=str(p),file_sha256=row['file_sha256'],tensor=tensor(x)))
    return arrays,identities

def save_array(path,x):
    if path.exists():raise RuntimeError('Immutable array exists')
    temp=path.with_suffix('.part')
    with temp.open('wb') as f:np.save(f,x,allow_pickle=False);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    return dict(path=path.name,file_bytes=path.stat().st_size,file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),tensor=tensor(x))

def compare_logits(a,b,decision_a,decision_b):
    if a.shape!=(151936,) or b.shape!=a.shape or a.dtype!=np.float32 or b.dtype!=np.float32:raise ValueError('Full FP32 vocabulary required')
    tensor(a);tensor(b)
    x=a.astype(np.float64);y=b.astype(np.float64);d=y-x
    norm=float(np.linalg.norm(x));den=norm*float(np.linalg.norm(y))
    if not norm or not den:raise ValueError('Degenerate logits')
    equal=bool(np.array_equal(a.view(np.uint32),b.view(np.uint32)))
    same=all(decision_a[k]==decision_b[k] for k in ('token_id','text','verdict'))
    return dict(full_logits_bit_equal=equal,changed_FP32_words=int(np.count_nonzero(a.view(np.uint32)!=b.view(np.uint32))),
        relative_l2=float(np.linalg.norm(d)/norm),cosine=float(np.dot(x,y)/den),RMSE=float(np.sqrt(np.mean(d*d))),max_abs=float(np.max(np.abs(d))),
        original=decision_a,candidate=decision_b,knife_score_delta=float(decision_b['knife_score']-decision_a['knife_score']),
        margin_delta=float(decision_b['logit_margin_yes_minus_no']-decision_a['logit_margin_yes_minus_no']),
        same_constrained_decision=same,quality_scope='One fixed last-frame two-view knife decision consistency; no labeled accuracy or category/location coverage',
        predeclared_acceptance='Exact original reference and all finite full candidate outputs plus unchanged constrained 0/1 decision; logit distances recorded without fitted thresholds',
        accuracy_proven=False,performance_proven=False)
