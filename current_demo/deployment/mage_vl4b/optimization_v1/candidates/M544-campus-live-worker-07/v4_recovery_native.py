"""One original M207 PS MLP width/bias override; no PYNQ/device APIs."""
import hashlib,json
from pathlib import Path
import numpy as np

class SignedStore:
    def __init__(self,name,c,s):self.name,self.codes,self.scales=name,c,s
    def decode(self,name):
        assert name==self.name
        return np.multiply(self.codes.astype(np.float32),self.scales.astype(np.float32)[...,None],dtype=np.float32).reshape(len(self.codes),-1)

class V4Recovery:
    def __init__(self,torch,mlp,package,idle):
        idle();self.idle=idle;self.mlp=mlp;self.original=(mlp.fc1,mlp.fc2);self.active=False;self.closed=False
        package=Path(package);p=json.loads((package/'V4_PLAN.json').read_bytes());f=package/p['weights']['path']
        assert hashlib.sha256(f.read_bytes()).hexdigest()==p['weights']['sha256']
        with np.load(f,allow_pickle=False) as z:weights={k:z[k].copy() for k in z.files}
        keep=weights['kept_original_groups'];assert keep.shape==(56,) and np.array_equal(keep,np.unique(keep)) and keep.min()>=0 and keep.max()<64
        self.new=[]
        for i,(part,bias) in enumerate((('fc1','bias1'),('fc2','bias2'))):
            old=self.original[i];assert type(old).__name__=='M207FP32GemmW4Linear' and old.output_dtype==torch.float32
            c,s=weights[part+'_codes'],weights[part+'_scales'];assert c.dtype==np.int8 and s.dtype==np.float16 and c.shape[:2]==s.shape and c.shape[2]==64
            assert np.isfinite(s).all() and (s>0).all() and np.isfinite(weights[bias]).all()
            store=SignedStore(old.name,c,s)
            m=type(old)(torch,store,old.name,c.shape[1]*64,c.shape[0],True,torch.float32)
            m.bias=torch.nn.Parameter(torch.from_numpy(weights[bias]),requires_grad=False);self.new.append(m)
        assert (self.new[0].in_features,self.new[0].out_features,self.new[1].in_features,self.new[1].out_features)==(1024,3584,3584,1024)
    def select(self,enabled):
        assert type(enabled)is bool and not self.closed;self.idle()
        self.mlp.fc1,self.mlp.fc2=self.new if enabled else self.original;self.active=enabled
    def close(self):
        if not self.closed:self.select(False);self.closed=True
