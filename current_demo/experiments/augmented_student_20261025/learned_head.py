"""Portable learned full-vocabulary residual; no token-specific processing."""
import hashlib,time
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class LearnedHead:
    def __init__(self,root,manifest):
        root=Path(root);self.manifest=manifest;self.calls=0;self.elapsed_s=0.;self.original=None
        for name in ('A','B'):
            row=manifest[name];f=root/row['path']
            assert not f.is_symlink() and f.stat().st_nlink==1 and sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
            value=np.load(f,allow_pickle=False)
            assert value.dtype==np.float32 and value.flags.c_contiguous and np.isfinite(value).all()
            setattr(self,name,value)
        assert self.A.shape==(8,2560) and self.B.shape==(151936,8) and manifest['scale']==1.
        self.A.flags.writeable=False;self.B.flags.writeable=False
    def add(self,values,logits):
        t=time.perf_counter_ns()
        x=np.asarray(values,dtype=np.float32);y=np.asarray(logits,dtype=np.float32)
        assert x.shape==(1,2560) and y.shape==(1,151936) and np.isfinite(x).all() and np.isfinite(y).all()
        # Same operation on every vocabulary row. Nothing reads a token label.
        low=np.dot(x,self.A.T);correction=np.dot(low,self.B.T)
        out=y+correction
        assert out.dtype==np.float32 and out.shape==y.shape and np.isfinite(out).all()
        self.calls+=1;self.elapsed_s+=(time.perf_counter_ns()-t)/1e9
        return out
    def install(self,runtime):
        assert self.original is None
        self.runtime=runtime;self.original=runtime.lm_head
        def wrapped(values):
            saved=np.asarray(values,dtype=np.float32).copy()
            base=self.original(values)
            return self.add(saved,base)
        runtime.lm_head=wrapped;self.wrapped=wrapped
    def close(self):
        if self.original is not None:
            assert self.runtime.lm_head is self.wrapped
            self.runtime.lm_head=self.original;self.original=None
