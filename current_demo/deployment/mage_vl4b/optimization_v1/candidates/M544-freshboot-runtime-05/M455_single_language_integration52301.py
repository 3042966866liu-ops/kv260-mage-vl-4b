"""Only L1 or L2 full-name contract routing and actual post-Down FP32 R1.

No constructors, allocation, programming, DMA or replacement arithmetic.
The original M238 executor and M241 prefill/decode retain their scheduling.
"""
import copy,hashlib,threading
from pathlib import Path
import numpy as np
SIZES=(6963200,)*4+(389152,2621440,2621440)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def normalize(case,original,layer):
    if type(layer) is not int or layer not in (1,2) or case['chain']['layer']!=layer or original['layer']!=layer:
        raise ValueError('Explicit admitted L1/L2 only')
    source=case['chain'];family=source['family']
    if family not in ('gate_up','mlp_down') or original['family']!=family or source['bits']!=original['bits'] or source['bits']!=4:
        raise ValueError('Original W4 family identity required')
    c=copy.deepcopy(source);prefix=f'model.language_model.layers.{layer}.mlp.'
    names={'gate':prefix+'gate_proj','up':prefix+'up_proj','down':prefix+'down_proj'}
    oldnames={d['module'] for d in original['descriptors']};expected={'gate','up'} if family=='gate_up' else {'down'}
    if {d['module'] for d in c['descriptors']}!=expected or {names[n] for n in expected}!=oldnames:
        raise ValueError('Complete original module mapping required')
    for d in c['descriptors']:
        d['module']=names[d['module']]
        # Preserve the production contract's macro accounting units.
        d['expected_macros']=d['valid_rows']*32*c['groups']
    c.update(chain_index=original['chain_index'],family_code=original['family_code'],
        expected_macros=32*c['groups']*sum(d['valid_rows'] for d in c['descriptors']),
        input_words128=c['input_bytes']//16,output_words64=c['output_bytes']//8)
    if c['groups']!=(40 if family=='gate_up' else 144) or c['input_bytes']>SIZES[4] or c['output_bytes']>SIZES[5]:
        raise ValueError('Only physical9216 with original owners')
    if c.get('expected_build_id')!=0x4D343535:raise ValueError('Actual M455 dense ABI required')
    return c

class SingleLayerBinding:
    """A new explicit local override, never a fake original154-contract PASS."""
    def __init__(self,runtime,language,layer,cases,layouts,bias,*,safe,ledger,base):
        if type(layer) is not int or layer not in (1,2) or not callable(safe):raise ValueError('Single explicitly admitted layer')
        if not safe():raise RuntimeError('Unknown or active owner')
        ledger.verify_full(runtime)
        self.runtime,self.language,self.layer,self.safe,self.base=runtime,language,layer,safe,base
        self.original_lookup=runtime._language_chain;self.original_stage=runtime._stage;self.original_family=language._family
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        if tuple(b.nbytes for b in self.buffers)!=SIZES:raise RuntimeError('Original seven capacity owners')
        self.owner_ids=tuple(map(id,self.buffers));self.addresses=tuple(base.physical_address(b) for b in self.buffers)
        self.bias=np.array(bias,copy=True);self.bias.setflags(write=False);self.entries={};self.originals={};self.active=False;self.closed=False;self.records=[]
        if self.bias.dtype!=np.float32 or self.bias.shape!=(2560,) or not np.isfinite(self.bias).all():raise ValueError('Actual frozen FP32 R1')
        if len(cases)!=2 or len(layouts)!=2:raise ValueError('Exactly two changed families')
        for case,layout in zip(cases,layouts):
            family=case['chain']['family'];original=self.original_lookup(layer,family);c=normalize(case,original,layer)
            if family in self.entries:raise ValueError('Duplicate changed family')
            start,size=base.chain_window(layout,c)
            if start!=0 or size!=c['stage_bytes_per_shard'] or size>runtime.maximum_weight_window_bytes:raise ValueError('Exact staged layout/owner geometry')
            self.entries[family]=(c,layout);self.originals[family]=copy.deepcopy(original)
        if set(self.entries)!={'gate_up','mlp_down'}:raise ValueError('Exactly two changed families')
        self.previous=[(obj,key,key in obj.__dict__,obj.__dict__.get(key)) for obj,key in ((runtime,'_language_chain'),(runtime,'_stage'),(language,'_family'))]
        runtime._language_chain=self.lookup;runtime._stage=self.stage;language._family=self.family
    def idle(self):
        if self.closed or not self.safe():raise RuntimeError('Unknown active/closed owner')
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(map(id,current))!=self.owner_ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Owner identity/address changed')
        if any(t.name.startswith(('m238-pack','m238-parse')) for t in threading.enumerate()):raise RuntimeError('Original request worker still active')
    def select(self,active):
        if type(active) is not bool:raise ValueError('Original or one fixed candidate only')
        self.idle();self.active=active;self.runtime._programmed_config=None;self.runtime._programmed_weight_addresses=None
    def lookup(self,layer,family):
        if self.active and layer==self.layer and family in self.entries:return self.entries[family][0]
        c=self.original_lookup(layer,family)
        if layer==self.layer and family in self.originals and c!=self.originals[family]:raise RuntimeError('Original contract mutated')
        return c
    def stage(self,layout,chain):
        for registered,target in self.entries.values():
            if registered is chain:
                if not self.active:raise RuntimeError('Changed stage outside selected candidate')
                self.idle();return self.base.M120BoardRuntime._stage(self.runtime,target,chain)
        return self.original_stage(layout,chain)
    def family(self,layer,family,values):
        outputs=self.original_family(layer,family,values)
        if self.active and layer==self.layer and family=='mlp_down':
            key=f'model.language_model.layers.{layer}.mlp.down_proj';y=outputs[key]
            if y.dtype!=np.float32 or y.ndim!=2 or y.shape[1]!=2560 or not np.isfinite(y).all():raise ValueError('Actual complete original Down FP32 output')
            outputs=dict(outputs);outputs[key]=np.add(y,self.bias[None,:],dtype=np.float32)
            if not np.isfinite(outputs[key]).all():raise FloatingPointError('Nonfinite post-Down R1')
            self.records.append(dict(layer=layer,rows=len(y),bias_sha256=digest(self.bias.tobytes()),order='actual M238 parse -> FP32 bias -> original M241 residual',extra_PL_chain=False))
        return outputs
    def close(self):
        self.idle()
        for obj,key,owned,value in reversed(self.previous):
            if owned:setattr(obj,key,value)
            else:delattr(obj,key)
        if not all((key in obj.__dict__)==owned and (not owned or obj.__dict__[key] is value) for obj,key,owned,value in self.previous):raise RuntimeError('Original Python binding restoration differs')
        self.closed=True
