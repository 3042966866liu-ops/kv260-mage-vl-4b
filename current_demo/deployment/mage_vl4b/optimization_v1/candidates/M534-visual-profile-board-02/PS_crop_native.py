"""Native M273 CPU-only V2/V3/V6 crop; no PL/DMA or device imports.

Selected native M207 Linear objects use exact frozen integer codes/FP16 scales.
Original PS GELU, precision wrappers, residuals and every other layer stay live.
"""
from collections import OrderedDict
import hashlib,json
from pathlib import Path
import numpy as np

class DecodeBudget:
    def __init__(self,limit=32<<20):
        assert type(limit)is int and 24<<20<=limit<=32<<20
        self.limit=limit;self.cache=OrderedDict();self.bytes=0;self.high_water=0
    def obtain(self,key,codes,scales):
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        expected=int(codes.size*4);assert expected<=self.limit
        while self.bytes+expected>self.limit:
            _,old=self.cache.popitem(last=False);self.bytes-=old.nbytes
        dense=np.multiply(codes.astype(np.float32),scales.astype(np.float32)[...,None],dtype=np.float32).reshape(len(codes),-1)
        assert dense.nbytes==expected and np.isfinite(dense).all()
        self.cache[key]=dense;self.bytes+=dense.nbytes;self.high_water=max(self.high_water,self.bytes)
        assert self.bytes<=self.limit
        return dense

class CropStore:
    def __init__(self,key,codes,scales,budget):self.key,self.codes,self.scales,self.budget=key,codes,scales,budget
    def decode(self,name):
        assert name==self.key
        return self.budget.obtain(self.key,self.codes,self.scales)

class PSCropSelector:
    def __init__(self,torch,vision_runtime,package,*,idle):
        assert callable(idle);idle()
        self.torch,self.runtime,self.idle=torch,vision_runtime,idle
        self.active=False;self.closed=False;self.handles=[];self.rows=[];self.calls={}
        self.budget=DecodeBudget();package=Path(package)
        p=json.loads((package/'PS_NATIVE_PLAN.json').read_bytes())
        assert [r['index'] for r in p['selected']]==[2,3,6]
        self.compact_bytes=0
        for row in p['selected']:
            i=row['index'];outer=vision_runtime.vision.encoder.layers[i]
            assert outer.index==i and outer.layer.target_dtype==torch.float32 and outer.layer.output_dtype==torch.bfloat16
            mlp=outer.layer.layer.mlp;original=(mlp.fc1,mlp.fc2)
            assert type(original[0]).__name__==type(original[1]).__name__=='M207FP32GemmW4Linear'
            assert (original[0].in_features,original[0].out_features,original[1].in_features,original[1].out_features)==(1024,4096,4096,1024)
            file=package/row['codes']['path'];assert hashlib.sha256(file.read_bytes()).hexdigest()==row['codes']['sha256']
            with np.load(file,allow_pickle=False) as z:
                weights={k:z[k].copy() for k in ('fc1_codes','fc1_scales','fc2_codes','fc2_scales','bias1','bias2','kept_original_groups')}
            keep=weights['kept_original_groups'];assert keep.shape==(48,) and keep.dtype.kind in 'iu'
            ids=(keep[:,None]*64+np.arange(64)).reshape(-1)
            assert np.array_equal(ids,np.unique(ids)) and ids.shape==(3072,) and 0<=ids.min()<ids.max()<4096
            assert np.array_equal(original[0].bias.detach().numpy()[ids],weights['bias1'])
            assert original[1].bias.detach().numpy().tobytes()==weights['bias2'].tobytes()
            new=[]
            for part,old,bias in (('fc1',original[0],'bias1'),('fc2',original[1],'bias2')):
                assert old.output_dtype==torch.float32 and old.bias.dtype==torch.float32
                c,s=weights[part+'_codes'],weights[part+'_scales']
                assert c.dtype==np.int8 and s.dtype==np.float16 and c.shape[:2]==s.shape and c.shape[-1]==64
                self.compact_bytes+=c.nbytes+s.nbytes
                store=CropStore(old.name,c,s,self.budget)
                module=type(old)(torch,store,old.name,c.shape[1]*64,c.shape[0],True,torch.float32)
                module.bias=torch.nn.Parameter(torch.from_numpy(weights[bias]),requires_grad=False)
                new.append(module)
            assert (new[0].in_features,new[0].out_features,new[1].in_features,new[1].out_features)==(1024,3072,3072,1024)
            file=package/row['R1']['path'];raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['R1']['sha256']
            r1=np.frombuffer(raw,np.float32).copy();assert r1.shape==(1024,) and np.isfinite(r1).all()
            self.rows.append(dict(index=i,mlp=mlp,original=original,cropped=tuple(new),R1=torch.from_numpy(r1)))
        assert self.compact_bytes<=21<<20
    def choose(self,arm):
        assert arm in ('A','B') and not self.closed;self.idle();active=arm=='B'
        if active==self.active:return
        for handle in self.handles:handle.remove()
        self.handles=[]
        for row in self.rows:
            mlp=row['mlp'];mlp.fc1,mlp.fc2=row['cropped'] if active else row['original']
            if active:
                def correct(module,args,output,row=row):
                    assert tuple(output.shape)==(1,392,1024) and output.dtype==self.torch.float32
                    self.calls[row['index']]=self.calls.get(row['index'],0)+1
                    return self.torch.add(output,row['R1'])
                self.handles.append(mlp.register_forward_hook(correct))
        self.active=active
    def begin_request(self):self.calls.clear()
    def end_request(self):
        assert self.calls==({2:1,3:1,6:1} if self.active else {})
        return dict(active_PS_crops=[2,3,6] if self.active else [],MLP_calls=dict(self.calls),
            compact_code_scale_bytes=self.compact_bytes,decoded_cache_bytes=self.budget.bytes,
            decoded_cache_limit=self.budget.limit,decoded_cache_high_water=self.budget.high_water,
            device_APIs=0,full_MLP_FP32_R1_before_original_BF16_boundary=True)
    def close(self):
        self.choose('A');self.closed=True
        assert not self.handles and all((r['mlp'].fc1,r['mlp'].fc2)==r['original'] for r in self.rows)
