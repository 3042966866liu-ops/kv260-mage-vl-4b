"""Full differentiable student with streamed frozen weights and checkpointing.

The teacher is cached. GPU FP32/BF16 surrogate, not an M455 numeric oracle.
"""
from common_joint import *
import re,gc
import numpy as np

class JointStudent:
    def __init__(self,p):
        import torch
        from torch import nn
        import torch.nn.functional as F
        from torch.utils.checkpoint import checkpoint
        from transformers.modeling_outputs import BaseModelOutputWithPooling
        self.torch=torch;self.p=p;self.device=torch.device('cuda');self.hidden={};self.handles=[]
        torch.manual_seed(p['seed']);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        e=engine_class()(p['runtime_protocol']);self.engine=e
        e.vision.vision.requires_grad_(False)
        for handle in e.hooks:handle.remove()
        e.hooks=[]
        planroot=OPT/'candidates/M523-M455-twentytwo-layer-R1-research-240'
        rows={r['key']:r for r in read(planroot/'TWENTYTWO_LAYER_PLAN.json')['layers']}
        cfg=read(OPT/'contracts/config.json');entries={r['name']:r for r in read(Path(cfg['checkpoint'])/'CHECKPOINT_MANIFEST.json')['entries']}
        self.linears={};rank=p['rank'];alpha=p['alpha']
        class StreamLinear(nn.Module):
            def __init__(self,weight,bias,dtype,name,bits,trainable):
                super().__init__()
                # Plain CPU tensor, deliberately not a registered buffer: .to()
                # must not move a full frozen checkpoint into8GB GPU memory.
                self._base_cpu=weight.detach().cpu().contiguous();self.output_dtype=dtype
                self.global_name=name;self.bits=bits;self.in_features=weight.shape[1];self.out_features=weight.shape[0]
                self.register_buffer('bias',None if bias is None else bias.detach().float().to('cuda'))
                if trainable:
                    self.A=nn.Parameter(torch.randn(rank,weight.shape[1],device='cuda')*.01)
                    self.B=nn.Parameter(torch.zeros(weight.shape[0],rank,device='cuda'));self.scale=alpha/rank
                else:self.register_parameter('A',None);self.register_parameter('B',None);self.scale=0.
            @property
            def weight(self):return self._base_cpu
            def forward(self,x):
                w=self._base_cpu.to(device=x.device,dtype=torch.float32)
                y=F.linear(x.float(),w,self.bias)
                if self.A is not None:y=y+F.linear(F.linear(x.float(),self.A),self.B)*self.scale
                return y.to(self.output_dtype)
        self.StreamLinear=StreamLinear
        def setmodule(root,name,value):
            owner=root.get_submodule(name.rsplit('.',1)[0]) if '.' in name else root
            setattr(owner,name.split('.')[-1],value)
        # Build every vision Linear, including frozen patch/merger components.
        for name,module in list(e.vision.vision.named_modules()):
            if not hasattr(module,'store'):continue
            found=re.search(r'encoder\.layers\.(\d+)\.',name);i=int(found.group(1)) if found else None
            if i is not None and i not in p['vision']:continue
            canonical=module.name
            weight=torch.from_numpy(module.store.decode(module.name).copy());bias=module.bias
            if i in e.oracle.crops and '.mlp.fc' in name:
                row=rows['vision_'+str(i).zfill(2)]
                with np.load(planroot/row['codes']['path'],allow_pickle=False) as z:
                    part=name.split('.')[-1];c=z[part+'_codes'];s=z[part+'_scales'];weight=torch.from_numpy((c.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(len(c),-1))
                if name.endswith('fc1'):bias=bias[torch.from_numpy(e.oracle.crops[i])]
            if name.endswith('mlp.fc2'):
                correction=None
                if i in (2,3,6):correction=np.frombuffer((RUNS/'M523-PS-V2-V3-V6-3072-fit-02/R1'/('vision_'+str(i).zfill(2)+'_FP32.bin')).read_bytes(),np.float32).copy()
                elif i in e.oracle.r1:correction=e.oracle.r1[i]
                if correction is not None:bias=bias.detach().float()+torch.from_numpy(correction)
            dtype=module.output_dtype
            if dtype==torch.bfloat16:weight=weight.to(torch.bfloat16)
            new=StreamLinear(weight,bias,dtype,canonical,4,i is not None)
            setmodule(e.vision.vision,name,new)
            if i is not None:self.linears['vision:'+str(i)+':'+name]=new
        for i in p['language']:
            block=e.original_language[i]
            for name,module in list(block.named_modules()):
                if not isinstance(module,nn.Linear):continue
                global_name='model.language_model.layers.'+str(i)+'.'+name
                bias=module.bias
                if name=='mlp.down_proj' and 'language_'+str(i).zfill(2) in rows:
                    row=rows['language_'+str(i).zfill(2)];correction=torch.from_numpy(np.frombuffer((planroot/row['R1']['path']).read_bytes(),np.float32).copy())
                    bias=correction if bias is None else bias.detach().float()+correction
                bits=int(entries[global_name+'.weight']['bits']);assert bits in (2,3,4)
                new=StreamLinear(module.weight,bias,module.weight.dtype,global_name,bits,True)
                setmodule(block,name,new);self.linears['language:'+str(i)+':'+name]=new
        e.model.lm_head=StreamLinear(e.model.lm_head.weight,None,e.model.lm_head.weight.dtype,'lm_head',int(entries['lm_head.weight']['bits']),False)
        e.set_active(p['vision'],p['language'])
        e.language.to('cuda');e.vision.vision.to('cuda')
        # The detached oracle is inference-only; new training uses the explicitly
        # differentiable precision surrogate above, never pretends exact M455.
        e.oracle.chains.clear();gc.collect();torch.cuda.empty_cache()
        for branch,indices,original in [('vision',p['vision'],e.original_vision),('language',p['language'],e.original_language)]:
            for i in indices:
                outer=original[i];core=outer
                if branch=='vision':
                    while not hasattr(core,'self_attn'):core=core.layer
                old_forward=core.forward
                def wrapped(*args,_forward=old_forward,**kwargs):
                    if torch.is_grad_enabled():return checkpoint(_forward,*args,use_reentrant=False,preserve_rng_state=True,**kwargs)
                    return _forward(*args,**kwargs)
                core.forward=wrapped
                key=branch+'_'+str(i).zfill(2)
                def observe(module,args,out,key=key):self.hidden[key]=out[0] if isinstance(out,tuple) else out
                self.handles.append(outer.register_forward_hook(observe))
        def injected(pixel_values,*args,**kwargs):
            assert self.feature is not None and self.visual_calls==0
            self.visual_calls+=1
            return BaseModelOutputWithPooling(last_hidden_state=self.feature)
        e.visual.forward=injected
        self.params=[x for m in self.linears.values() for x in (m.A,m.B)]
        allowed=set(map(id,self.params))
        assert {id(x) for x in list(e.model.parameters())+list(e.vision.vision.parameters()) if x.requires_grad}==allowed
        self.initial={k:dict(A=m.A.detach().cpu().clone(),B=m.B.detach().cpu().clone()) for k,m in self.linears.items()}
        self.feature=None
        assert all(m._base_cpu.device.type=='cpu' for m in self.linears.values())
    def reset(self):
        with self.torch.no_grad():
            for k,m in self.linears.items():m.A.copy_(self.initial[k]['A']);m.B.copy_(self.initial[k]['B'])
        for p in self.params:p.grad=None
    def forward(self,arrays):
        torch=self.torch;e=self.engine;self.hidden={};self.feature=None;self.visual_calls=0
        x={k:torch.from_numpy(v.copy()).to('cuda') for k,v in arrays.items()}
        e.vision._vision_started=time.monotonic()
        features=e.vision.vision(x['pixel_values'].to(e.vision.compute_dtype),grid_thw=x['image_grid_thw'],patch_positions=x['patch_positions']).last_hidden_state
        assert features.shape==(98,2560);self.feature=features
        z=e.model(**x,input_ids=torch.tensor([self.p['token_ids']],device='cuda'),attention_mask=torch.ones((1,128),dtype=torch.long,device='cuda'),use_cache=False,logits_to_keep=1).logits[0,-1].float()
        assert z.shape==(151936,) and self.visual_calls==1 and self.hidden.keys()==set(['vision_'+str(i).zfill(2) for i in self.p['vision']]+['language_'+str(i).zfill(2) for i in self.p['language']])
        return z,features,self.hidden
    def state(self):return {k:dict(A=m.A.detach().cpu(),B=m.B.detach().cpu(),scale=m.scale,bits=m.bits,global_name=m.global_name,shape=list(m._base_cpu.shape)) for k,m in self.linears.items()}
    def close(self):
        for h in self.handles:h.remove()
        self.engine.close()
