"""M534 passive nested visual timers; all original calls/values are delegated.

No device APIs. CPU Linear is synchronous; nested totals are not additive.
The first request alone snapshots three real normalized MLP inputs; hot timers
never clone tensors. PL callbacks/forward substitutions keep their old objects.
"""
import hashlib,time,io,os
from pathlib import Path
from collections import defaultdict
import numpy as np

def tensor_sha(x):
    return hashlib.sha256(x.detach().float().cpu().contiguous().numpy().tobytes()).hexdigest()

def core_layer(outer):
    wrappers=[];core=outer
    while not hasattr(core,'self_attn'):
        wrappers.append(type(core).__name__)
        assert hasattr(core,'layer') and len(wrappers)<=3,'Actual visual wrapper closure differs'
        core=core.layer
    assert all(hasattr(core,n) for n in ('mlp','layer_norm1','layer_norm2'))
    return core,wrappers

class VisionProfiler:
    def __init__(self,torch,original_layers,retained,vision_model=None):
        self.torch=torch;self.retained=tuple(retained);self.handles=[];self.saved=[]
        self.active=False;self.capture=False;self.stack=[];self.events=[];self.inputs={};self.cores={};self.topology={}
        for index in self.retained:
            outer=original_layers[index];core,wrappers=core_layer(outer);self.cores[index]=core
            self.topology[str(index)]=dict(wrappers=wrappers,core=type(core).__name__,attention=type(core.self_attn).__name__,MLP=type(core.mlp).__name__)
            modules=dict(layer=outer,attention=core.self_attn,qkv=core.self_attn.qkv,proj=core.self_attn.proj,
                         mlp=core.mlp,fc1=core.mlp.fc1,fc2=core.mlp.fc2,norm1=core.layer_norm1,norm2=core.layer_norm2)
            for name,module in modules.items():self._hook(module,index,name)
        if vision_model is not None:
            for name in ('embeddings','layernorm_pre','layernorm_post','merger'):
                module=getattr(vision_model,name,None)
                if module is not None:self._hook(module,-1,name)
        # Wrap each shared store only once; method identity is restored exactly.
        stores={id(m.store):m.store for core in self.cores.values() for m in (core.self_attn.qkv,core.self_attn.proj,core.mlp.fc1,core.mlp.fc2) if hasattr(m,'store')}
        for store in stores.values():
            original=store.decode
            def decoded(*args,_old=original,**kwargs):
                if not self.active:return _old(*args,**kwargs)
                began=time.perf_counter_ns();value=_old(*args,**kwargs)
                self._leaf('decode',began);return value
            self._replace(store,'decode',decoded)
        original=torch.nn.functional.linear
        def linear(*args,**kwargs):
            if not self.active:return original(*args,**kwargs)
            began=time.perf_counter_ns();value=original(*args,**kwargs)
            self._leaf('cpu_linear',began);return value
        self._replace(torch.nn.functional,'linear',linear)

    def _replace(self,obj,name,value):
        owned=name in obj.__dict__;old=obj.__dict__.get(name)
        self.saved.append((obj,name,owned,old));setattr(obj,name,value)

    def _leaf(self,name,began):
        index,part,_=self.stack[-1] if self.stack else (-1,'outside_encoder',0)
        self.events.append(dict(layer=index,part=part,kind=name,elapsed_s=(time.perf_counter_ns()-began)/1e9))

    def _hook(self,module,index,name):
        def before(module,args):
            if not self.active:return
            if name=='mlp' and self.capture and index in (2,3,6):
                assert index not in self.inputs
                value=args[0];assert tuple(value.shape)==(1,392,1024) and value.dtype==self.torch.float32
                self.inputs[index]=value.detach().clone()
            self.stack.append((index,name,time.perf_counter_ns()))
        def after(module,args,value):
            if not self.active:return
            i,n,began=self.stack.pop();assert (i,n)==(index,name)
            self.events.append(dict(layer=index,part=name,kind='module',elapsed_s=(time.perf_counter_ns()-began)/1e9))
        self.handles.extend([module.register_forward_pre_hook(before),module.register_forward_hook(after)])

    def begin(self,capture=False):
        assert not self.active and not self.stack
        self.events=[];self.capture=bool(capture);self.active=True

    def end(self):
        assert self.active and not self.stack;self.active=False;self.capture=False
        rows=[]
        for i in self.retained:
            sums=defaultdict(float);counts=defaultdict(int)
            for e in self.events:
                if e['layer']==i:
                    k=e['kind']+':'+e['part'];sums[k]+=e['elapsed_s'];counts[k]+=1
            assert all(counts['module:'+n]==1 for n in ('layer','attention','qkv','proj','mlp','fc1','fc2','norm1','norm2'))
            row=dict(layer=i,MLP_execution='PS' if i<13 else 'PL',sums=dict(sums),counts=dict(counts))
            row['attention_non_projection_s']=sums['module:attention']-sums['module:qkv']-sums['module:proj']
            row['MLP_non_linear_s']=sums['module:mlp']-sums['module:fc1']-sums['module:fc2']
            row['layer_other_s']=sums['module:layer']-sums['module:attention']-sums['module:mlp']-sums['module:norm1']-sums['module:norm2']
            rows.append(row)
        outside=defaultdict(float)
        for event in self.events:
            if event['layer']==-1:outside[event['kind']]+=event['elapsed_s']
        components={e['part']:e['elapsed_s'] for e in self.events if e['layer']==-1 and e['kind']=='module'}
        return dict(rows=rows,events=list(self.events),topology=self.topology,outside_encoder=dict(outside),outside_components=components,
                    nested_intervals_not_additive=True,CPU_linear_delegates_original=True,
                    hot_requests_no_tensor_capture=True)

    def close(self,idle=None):
        if self.active or self.stack:
            assert callable(idle),'Aborted observer requires original caller idle proof'
            idle()
            self.active=False;self.stack=[]
        for handle in reversed(self.handles):handle.remove()
        self.handles=[]
        for obj,name,owned,old in reversed(self.saved):
            if owned:setattr(obj,name,old)
            else:delattr(obj,name)
        assert all((name in obj.__dict__)==owned and (not owned or obj.__dict__[name] is old) for obj,name,owned,old in self.saved)
        self.saved=[]

def screen_or_route(torch,profile,ps_selector,profiler,output):
    """Frozen branch: stop MLP shrinking if aggregate PS attention dominates."""
    rows=profile['rows'];ps=[r for r in rows if r['layer']<13]
    attn=sum(r['sums']['module:attention'] for r in ps);mlp=sum(r['sums']['module:mlp'] for r in ps)
    base=dict(PS_attention_s=attn,PS_MLP_s=mlp,training_updates=0,new_full_model_forwards=0)
    if attn>=mlp:
        target=max(rows,key=lambda r:r['sums']['module:attention'])
        return dict(base,status='ROUTE_TO_ATTENTION_STOP_MLP_WIDTH_SCREEN',target_layer=target['layer'],
                    target_component='qkv_projection' if target['sums']['module:qkv']>=max(target['sums']['module:proj'],target['attention_non_projection_s']) else 'attention_core_or_proj',
                    reason='Current measured aggregate PS attention >= PS MLP; no candidate widths or distillation executed')
    eligible=[r for r in ps if r['layer'] in (2,3,6)];target=max(eligible,key=lambda r:r['sums']['module:mlp'])['layer']
    row=next(r for r in ps_selector.rows if r['index']==target);fc1,fc2=row['cropped'];x=profiler.inputs[target]
    assert torch.get_num_threads()==4 and x.dtype==torch.float32 and tuple(x.shape)==(1,392,1024)
    # Only frozen weight energy, no answers or evaluation inputs select groups.
    c1,s1=fc1.store.codes,fc1.store.scales;c2,s2=fc2.store.codes,fc2.store.scales
    w1=fc1.store.decode(fc1.name);w2=fc2.store.decode(fc2.name)
    energy=(np.square(w1.astype(np.float64)).reshape(48,64,1024).sum((1,2))*np.square(w2.astype(np.float64)).reshape(1024,48,64).sum((0,2)))
    weights={};selected={};act=profiler.cores[target].mlp.activation_fn
    for width in (3072,2816,2560):
        groups=np.sort(np.argsort(-energy,kind='stable')[:width//64]);ids=(groups[:,None]*64+np.arange(64)).reshape(-1)
        selected[str(width)]=groups.tolist()
        weights[width]=(torch.from_numpy(np.ascontiguousarray(w1[ids])),fc1.bias.detach()[ids].contiguous(),torch.from_numpy(np.ascontiguousarray(w2[:,ids])),fc2.bias.detach())
    def run(width):
        a,b,c,d=weights[width]
        return torch.nn.functional.linear(act(torch.nn.functional.linear(x,a,b)),c,d)
    times={w:[] for w in weights};outputs={}
    with torch.inference_mode():
        for w in weights:outputs[w]=run(w)
        for w in (3072,2816,2560,2560,2816,3072):
            began=time.perf_counter_ns();y=run(w);elapsed=(time.perf_counter_ns()-began)/1e9
            assert torch.equal(y,outputs[w]);times[w].append(elapsed)
    reference=outputs[3072].numpy();candidates=[]
    for width in weights:
        y=outputs[width].numpy();den=np.linalg.norm(reference.astype(np.float64));relative=float(np.linalg.norm((y-reference).astype(np.float64))/max(den,1e-30))
        cosine=float(np.dot(y.ravel().astype(np.float64),reference.ravel().astype(np.float64))/max(np.linalg.norm(y.astype(np.float64))*den,1e-30))
        candidates.append(dict(width=width,elapsed_s=times[width],mean_s=sum(times[width])/2,raw_MLP_relative_L2=relative,raw_MLP_cosine=cosine,output_sha256=tensor_sha(outputs[width])))
    candidates.sort(key=lambda r:r['width'],reverse=True);a=candidates[0]['mean_s']
    qualified=[c for c in candidates if c['width']!=3072 and c['mean_s']<a*.95 and c['raw_MLP_relative_L2']<=.20 and c['raw_MLP_cosine']>=.98]
    # Exactly one bounded replay input, after all timed requests. Kept separate
    # from persistent diagnostics and from live DMA owners; no per-request pileup.
    output=Path(output);assert not output.exists();output.mkdir()
    stream=io.BytesIO();np.savez_compressed(stream,MLP_input=x.detach().cpu().numpy())
    payload=stream.getvalue();assert len(payload)<=2<<20
    file=output/'selected_MLP_input.npz'
    with file.open('xb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
    return dict(base,status='SCREENED_PS_MLP_WIDTHS_NOT_QUALITY_PASS',target_layer=target,input_sha256=tensor_sha(x),input_shape=list(x.shape),selected_current_groups=selected,candidates=candidates,
                saved_real_input=dict(path=str(file),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),bounded_RAM_replay_asset=True,outside_TTFT=True),
                recommended_width=min(qualified,key=lambda r:r['mean_s'])['width'] if qualified else None,
                selection='>=5% observed CPU local speed gain, raw relativeL2<=.20 and cosine>=.98; screening only, no complete quality claim',
                old_R1_not_applied_to_new_width=True,complete_raw_fc1_GELU_fc2=True,original_thread_precision=True)
