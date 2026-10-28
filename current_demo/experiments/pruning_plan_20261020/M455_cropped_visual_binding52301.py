"""V14 crop through the original PLMLPBinding, GELU and original FP32 biases.

The actual submit/stage capabilities are supplied by the original resource owner.
No hardware access, allocation or PS GEMM fallback is exposed here.
"""
from types import SimpleNamespace
import numpy as np
class CroppedVisualBinding:
    def __init__(self,torch,mlp,chains,kept_ids,r1,initial,host,stage,submit,binding_class):
        self.torch,self.mlp,self.chains=torch,mlp,chains;self.previous=[];self.restored=False;self.entered=False
        ids=np.array(kept_ids,copy=True)
        if ids.dtype.kind not in 'iu' or ids.shape!=(3584,) or not np.array_equal(np.unique(ids),ids) or ids.min()<0 or ids.max()>=4096:raise ValueError('Frozen ascending V14 energy channels required')
        groups=ids.reshape(56,64)
        if not np.all(groups==groups[:,0,None]+np.arange(64)) or np.any(groups[:,0]%64):raise ValueError('Whole original G64 groups required')
        if set(chains)!={'fc1','fc2'} or chains['fc1']['groups']!=16 or chains['fc2']['groups']!=56:raise ValueError('Explicit V14 1024->3584->1024 chains required')
        for part,width in (('fc1',3584),('fc2',1024)):
            c=chains[part]
            if c['bits']!=4 or c.get('expected_build_id')!=0x4D343535 or max(d['row_start']+d['valid_rows'] for d in c['descriptors'])!=width:raise ValueError('Exact M455 W4 output ABI/width required')
            module=getattr(mlp,part)
            if module.name!='encoder.layers.14.mlp.'+part:raise ValueError('Actual V14 Linear identity required')
            if module.output_dtype!=torch.float32 or module.bias.dtype!=torch.float32 or tuple(module.bias.shape)!=((4096,) if part=='fc1' else (1024,)):raise ValueError('Actual original FP32 bias geometry required')
        b=np.array(r1,copy=True)
        if b.dtype!=np.float32 or b.shape!=(1024,) or not np.isfinite(b).all():raise ValueError('Frozen post-fc2 FP32 R1 required')
        b.setflags(write=False);self.r1=b
        selected=mlp.fc1.bias.index_select(0,torch.from_numpy(ids.astype(np.int64))).clone()
        # Facades supply cropped bias to the exact original binding; real Linear metadata/bias stay intact.
        proxy=SimpleNamespace(fc1=SimpleNamespace(output_dtype=torch.float32,bias=selected),fc2=SimpleNamespace(output_dtype=torch.float32,bias=mlp.fc2.bias))
        self.proxy=proxy;self.inner=binding_class(torch,proxy,chains,initial,host,stage,submit,expected=None)
    @property
    def calls(self):return self.inner.calls
    @property
    def batches(self):return self.inner.batches
    def __enter__(self):
        if self.entered or self.restored:raise RuntimeError('One bounded visual scope only')
        self.inner.__enter__()
        try:
            for part in ('fc1','fc2'):
                module=getattr(self.mlp,part);owned='forward' in module.__dict__;old=module.__dict__.get('forward');self.previous.append((module,owned,old))
                forward=getattr(self.proxy,part).forward
                if part=='fc2':
                    def compensated(values,original=forward):
                        answer=original(values);a=answer.detach().cpu().numpy()
                        if a.dtype!=np.float32 or a.shape not in ((392,1024),(1,392,1024)) or not np.isfinite(a).all():raise ValueError('Actual complete parsed fc2/bias FP32 output required')
                        z=np.add(a,self.r1,dtype=np.float32)
                        if not np.isfinite(z).all():raise FloatingPointError('Nonfinite V14 R1 output')
                        return self.torch.from_numpy(z)
                    module.forward=compensated
                else:module.forward=forward
            self.entered=True;return self
        except BaseException:self.__exit__(None,None,None);raise
    def __exit__(self,*unused):
        for module,owned,old in reversed(self.previous):
            if owned:module.forward=old
            else:del module.__dict__['forward']
        restored=all(('forward' in module.__dict__)==owned and (not owned or module.__dict__['forward'] is old) for module,owned,old in self.previous)
        self.previous.clear();self.inner.__exit__(None,None,None);self.restored=restored and self.inner.restored;self.entered=False
        if not self.restored:raise RuntimeError('Actual visual Linear binding restoration differs')
        return False
