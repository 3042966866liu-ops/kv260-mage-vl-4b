"""Offline whole-block deletion. No board/control APIs."""
import copy, hashlib, json, sys, time
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
ROOT=H.parents[1]; OPT=ROOT/'deployment/mage_vl4b/optimization_v1'; R=OPT/'runs'
OLD=ROOT/'experiments/visual_ps_prune_20261024'
sys.path[:0]=[str(OLD),str(ROOT/'experiments/speed_target_30s_20261020'),str(ROOT/'experiments/adaptive_exec_error'),str(ROOT/'deployment/mage_vl4b/scripts'),str(ROOT/'deployment/mage_vl4b/m276_short_prompt_source'),str(ROOT/'deployment/mage_vl4b/m273_latest_binary_source'),str(ROOT/'scripts/optimization')]
PREFIX='M523-whole-layer-joint-128'
PREP=R/(PREFIX+'-protocol-01'); SEARCH=R/(PREFIX+'-search-01'); QUALITY=R/(PREFIX+'-quality-01')
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
def array(p,a):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:np.save(f,a,allow_pickle=False)
def files(p):return [dict(path=rel(f),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(p.rglob('*')) if f.is_file()]
def verify():
    p=read(PREP/'RESULT.json')
    for name,h in p['frozen'].items():assert sha(ROOT/name)==h,name
    return p
def margin(z,label):
    z=np.asarray(z,np.float64);e=np.exp(z-z.max());e/=e.sum()
    return float((e[9454]-e[2753])*(1 if label else -1)*100)
def decision(z):
    i=int(np.argmax(z));return 'Yes' if i==9454 else 'No' if i==2753 else 'Other'
def correct(z,label):return decision(z)==('Yes' if label else 'No')
def stats_hook(torch,bank,key):
    def hook(m,args,out):
        x=args[0].detach().float();y=(out[0] if isinstance(out,tuple) else out).detach().float()
        assert x.shape==y.shape and torch.isfinite(y).all()
        d=y-x
        row=bank.setdefault(key,dict(calls=0,residual2=0.,output2=0.,input2=0.))
        row['calls']+=1;row['residual2']+=float((d*d).double().sum());row['output2']+=float((y*y).double().sum());row['input2']+=float((x*x).double().sum())
    return hook
def ranked(bank,active,branch,p):
    protected=set(p['protected'][branch]);result=[]
    for i in active:
        if i in protected:continue
        key=branch+'_'+str(i).zfill(2);s=bank[key]
        damage=(s['residual2']/max(s['output2'],1e-30))**.5
        cost=p['costs'][key]['rank_cost_s']
        result.append(dict(index=i,key=key,residual_relative_L2=damage,rank_cost_s=cost,damage_per_cost=damage/max(cost,1e-9),calls=s['calls'],single_layer_task_effect_measured=False))
    return sorted(result,key=lambda r:(r['damage_per_cost'],r['index']))
