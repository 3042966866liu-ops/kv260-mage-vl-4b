"""Pure-CPU numerical/rejection fixture for the exact portable residual."""
from pathlib import Path
import json,time
import numpy as np
from learned_head import LearnedHead

def check_head(pkg):
    pkg=Path(pkg);head=LearnedHead(pkg,json.loads((pkg/'HEAD_MANIFEST.json').read_bytes()));cases=[]
    for label in ('negative','positive'):
        with np.load(pkg/('head_fixture_'+label+'.npz'),allow_pickle=False) as f:x=f['x'].copy();z=f['z'].copy();target=int(f['target'])
        actual=head.add(x,z)
        reference=(z.astype(np.float64)+((x.astype(np.float64)@head.A.astype(np.float64).T)@head.B.astype(np.float64).T)).astype(np.float32)
        error=float(np.max(np.abs(actual-reference)));assert error<.002 and int(actual.argmax())==target and np.isfinite(actual).all()
        cases.append(dict(label=label,full_vocab=151936,argmax=target,max_absolute_vs_FP64=error))
    rejected=0
    for x,z in ((np.zeros((1,2559),np.float32),np.zeros((1,151936),np.float32)),(np.zeros((1,2560),np.float32),np.zeros((1,2),np.float32)),(np.full((1,2560),np.nan,np.float32),np.zeros((1,151936),np.float32)),(np.zeros((1,2560),np.float32),np.full((1,151936),np.inf,np.float32))):
        try:head.add(x,z)
        except (AssertionError,ValueError):rejected+=1
        else:raise AssertionError('Bad head fixture accepted')
    assert rejected==4
    from types import SimpleNamespace
    runtime=SimpleNamespace(lm_head=lambda x:np.zeros((1,151936),np.float32));original=runtime.lm_head;head.install(runtime)
    assert runtime.lm_head(np.zeros((1,2560),np.float32)).shape==(1,151936);head.close();assert runtime.lm_head is original
    return dict(status='PASS_EXACT_PORTABLE_FULL_VOCAB_HEAD_CPU_FIXTURES',cases=cases,bad_shape_nonfinite_rejected=rejected,method_restored=True,extra_MACs=1235968,model_forwards=0,Overlay=0,DMA=0)
