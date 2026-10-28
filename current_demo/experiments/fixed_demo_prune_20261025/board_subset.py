"""Default-off retained-block scheduling; no allocation, Overlay or DMA API.

Numerical per-layer operations and the actual original weight copier are kept.
The caller supplies an idle predicate and is responsible for original owners.
"""
import ast,copy,hashlib,inspect,textwrap,types

def indices(values,maximum):
    a=tuple(values)
    if not a or any(type(i)is not int for i in a) or tuple(sorted(set(a)))!=a or not set(a)<=set(range(maximum)):
        raise ValueError('Nonempty ascending retained original layer indices required')
    return a

class LanguageSubset:
    def __init__(self,language,retained,idle,source_sha256):
        idle();self.language,self.idle=language,idle;self.retained=indices(retained,36)
        self.owned='prefill' in language.__dict__;self.previous=language.__dict__.get('prefill');self.original=language.prefill
        source=textwrap.dedent(inspect.getsource(type(language).prefill))
        if hashlib.sha256(source.encode()).hexdigest()!=source_sha256:raise ValueError('Original M241 prefill source differs')
        tree=ast.parse(source);loops=[n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='layer']
        if len(loops)!=1 or ast.unparse(loops[0].iter)!='range(LAYERS)':raise ValueError('Unique original complete36 layer loop required')
        loops[0].iter=ast.Name(id='_DEMO_RETAINED_ORIGINAL_LAYERS',ctx=ast.Load());ast.fix_missing_locations(tree)
        namespace=dict(type(language).prefill.__globals__);namespace['_DEMO_RETAINED_ORIGINAL_LAYERS']=self.retained
        exec(compile(tree,'<frozen_M241_retained_layers>','exec'),namespace)
        self.candidate=types.MethodType(namespace['prefill'],language);self.active=False;self.closed=False
        self.source_sha256=source_sha256
    def select(self,candidate):
        if type(candidate)is not bool or self.closed:raise ValueError('Explicit idle variant only')
        self.idle();self.language.prefill=self.candidate if candidate else self.original;self.active=candidate
    def close(self):
        if self.closed:return
        self.idle()
        if self.owned:self.language.prefill=self.previous
        elif 'prefill' in self.language.__dict__:del self.language.__dict__['prefill']
        self.closed=True

class VisionSubset:
    def __init__(self,torch,runtime,retained,idle):
        idle();self.torch,self.runtime,self.idle=torch,runtime,idle;self.retained=indices(retained,24)
        self.original=tuple(runtime.vision.encoder.layers)
        if len(self.original)!=24:raise ValueError('Original24 constructor required')
        self.bypass_calls={};self.active=False;self.closed=False
        owner=self
        class Bypass(torch.nn.Module):
            def __init__(self,index):super().__init__();self.index=index
            def forward(self,hidden_states,*args,**kwargs):
                if tuple(hidden_states.shape)!=(1,392,1024) or hidden_states.dtype!=torch.bfloat16:
                    raise ValueError('Original BF16 visual block boundary required')
                owner.bypass_calls[self.index]=owner.bypass_calls.get(self.index,0)+1
                return (hidden_states,)
        self.bypasses={i:Bypass(i) for i in range(24) if i not in self.retained}
    def select(self,candidate):
        if type(candidate)is not bool or self.closed:raise ValueError('Explicit idle variant only')
        self.idle();self.bypass_calls.clear()
        # Preserve24 callback positions for the original resource scope, while
        # excluded Transformer modules execute zero times and read no weights.
        self.runtime.vision.encoder.layers=self.torch.nn.ModuleList([self.bypasses[i] if candidate and i in self.bypasses else layer for i,layer in enumerate(self.original)])
        self.active=candidate
    def verify_request(self):
        expected={i:1 for i in self.bypasses} if self.active else {}
        if self.bypass_calls!=expected:raise RuntimeError('Actual removed visual bypass count differs')
        return dict(retained_original_layers=list(self.retained) if self.active else list(range(24)),bypass_calls=dict(self.bypass_calls),real_removed_transformer_calls=0,callback_positions=24)
    def close(self):
        if not self.closed:self.select(False);self.closed=True

class StageSubset:
    def __init__(self,runtime,prefetch,windows,retained,idle):
        self.runtime,self.prefetch,self.idle=runtime,prefetch,idle;self.retained=indices(retained,36)
        self.chains=tuple(runtime.language_contract.chains);self.head=tuple(runtime.head_contract.chains)
        if len(windows)!=4*(len(self.chains)+len(self.head)):raise ValueError('Complete original staging sequence required')
        self.groups=tuple(tuple(dict(w) for w in windows[i:i+4]) for i in range(0,len(windows),4))
        self.kept=tuple(i for i,c in enumerate(self.chains) if c['layer'] in self.retained)+tuple(range(len(self.chains),len(self.groups)))
        self.buffer_ids=tuple(map(id,runtime.staged_buffers));self.slot_ids=tuple(map(id,prefetch.reader.slots))
        if len(self.slot_ids)!=4:raise ValueError('Original four ordinary-RAM prefetch slots required')
    def select(self,candidate):
        self.idle();p=self.prefetch
        if p.active or p.reader.future is not None or p.reader.pending is not None:raise RuntimeError('Prefetch worker must be drained before selection')
        if tuple(map(id,self.runtime.staged_buffers))!=self.buffer_ids or tuple(map(id,p.reader.slots))!=self.slot_ids:raise RuntimeError('Original DMA owners / ordinary RAM slots changed')
        chosen=self.kept if candidate else tuple(range(len(self.groups)))
        groups=[[dict(w) for w in self.groups[i]] for i in chosen]
        p.groups=groups;p.reader.groups=groups
        return dict(source_group_indices=list(chosen),weight_groups=len(groups),weight_windows=4*len(groups),effective_bytes=sum(w['effective_bytes'] for g in groups for w in g),ordinary_RAM_slots_reused=True,removed_layer_staging_groups_absent=True)

def verify_PS_counts(selector,retained):
    keep=set(retained);expected={i:1 for i in (2,3,6) if i in keep}
    if not selector.active or selector.calls!=expected:raise RuntimeError('Retained PS crop call count differs')
    return dict(active_PS_crops=sorted(expected),MLP_calls=dict(selector.calls),decoded_cache_bytes=selector.budget.bytes,decoded_cache_limit=selector.budget.limit,decoded_cache_high_water=selector.budget.high_water,device_APIs=0)
