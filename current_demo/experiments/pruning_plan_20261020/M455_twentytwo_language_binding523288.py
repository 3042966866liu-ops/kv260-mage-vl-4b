"""One atomic L1+L2 dispatch binding, retaining the original M238 executor.

Explicit four-chain override and frozen FP32 R1; no constructor or hardware API.
"""
import copy,threading
import numpy as np
from M455_single_language_integration52301 import SIZES,digest
LANGUAGE_LAYERS=(1, 2, 4, 12, 14, 15, 16, 20, 21, 22, 23, 24, 26, 27, 28, 29, 31, 32, 34)

def normalize(case,original,layer):
    if type(layer) is not int or layer not in LANGUAGE_LAYERS or case['chain']['layer']!=layer or original['layer']!=layer:
        raise ValueError('Explicit current22 language layers only')
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


class TwentytwoLanguageBinding:
    def __init__(self,runtime,language,specs,*,safe,ledger,base):
        if set(specs)!=set(LANGUAGE_LAYERS) or not callable(safe) or not safe():raise ValueError('Admitted idle exact19-language scope only')
        ledger.verify_full(runtime)
        self.runtime,self.language,self.safe,self.base=runtime,language,safe,base
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        if tuple(b.nbytes for b in self.buffers)!=SIZES:raise RuntimeError('Original seven owners required')
        self.ids=tuple(map(id,self.buffers));self.addresses=tuple(base.physical_address(b) for b in self.buffers)
        self.original_lookup=runtime._language_chain;self.original_stage=runtime._stage;self.original_family=language._family
        self.entries={};self.originals={};self.biases={};self.records=[];self.active=False;self.closed=False
        for layer in LANGUAGE_LAYERS:
            cases,layouts,bias=specs[layer]
            if len(cases)!=2 or len(layouts)!=2:raise ValueError('Both changed families required')
            b=np.array(bias,copy=True)
            if b.dtype!=np.float32 or b.shape!=(2560,) or not np.isfinite(b).all():raise ValueError('Frozen FP32 R1 required')
            b.setflags(write=False);self.biases[layer]=b
            for case,layout in zip(cases,layouts):
                family=case['chain']['family'];key=(layer,family);original=self.original_lookup(*key)
                if key in self.entries:raise ValueError('Duplicate changed family')
                c=normalize(case,original,layer);start,size=base.chain_window(layout,c)
                if start!=0 or size!=c['stage_bytes_per_shard'] or size>runtime.maximum_weight_window_bytes:raise ValueError('Exact owner/layout geometry required')
                self.entries[key]=(c,layout);self.originals[key]=copy.deepcopy(original)
        if set(self.entries)!={(i,f) for i in LANGUAGE_LAYERS for f in ('gate_up','mlp_down')}:raise ValueError('Exactly38 explicit changed chains')
        self.previous=[(obj,key,key in obj.__dict__,obj.__dict__.get(key)) for obj,key in ((runtime,'_language_chain'),(runtime,'_stage'),(language,'_family'))]
        runtime._language_chain=self.lookup;runtime._stage=self.stage;language._family=self.family
    def idle(self):
        if self.closed or not self.safe():raise RuntimeError('Unknown active or closed owner')
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(map(id,current))!=self.ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Owner identity/address drift')
        if any(t.name.startswith(('m238-pack','m238-parse')) for t in threading.enumerate()):raise RuntimeError('Original worker still active')
    def select(self,active):
        if type(active) is not bool:raise ValueError('Atomic original or L1+L2 selection required')
        self.idle();self.active=active;self.runtime._programmed_config=None;self.runtime._programmed_weight_addresses=None
    def lookup(self,layer,family):
        key=(layer,family)
        if self.active and key in self.entries:return self.entries[key][0]
        c=self.original_lookup(layer,family)
        if key in self.originals and c!=self.originals[key]:raise RuntimeError('Original contract mutated')
        return c
    def stage(self,layout,chain):
        for registered,target in self.entries.values():
            if registered is chain:
                if not self.active:raise RuntimeError('Candidate stage outside selected combination')
                self.idle();return self.base.M120BoardRuntime._stage(self.runtime,target,chain)
        return self.original_stage(layout,chain)
    def family(self,layer,family,values):
        outputs=self.original_family(layer,family,values)
        if self.active and layer in self.biases and family=='mlp_down':
            key=f'model.language_model.layers.{layer}.mlp.down_proj';y=outputs[key]
            if y.dtype!=np.float32 or y.ndim!=2 or y.shape[1]!=2560 or not np.isfinite(y).all():raise ValueError('Actual parsed complete Down output required')
            outputs=dict(outputs);outputs[key]=np.add(y,self.biases[layer][None,:],dtype=np.float32)
            if not np.isfinite(outputs[key]).all():raise FloatingPointError('Nonfinite compensated output')
            self.records.append(dict(layer=layer,rows=len(y),bias_sha256=digest(self.biases[layer].tobytes()),extra_PL_chain=False))
        return outputs
    def close(self):
        self.idle()
        for obj,key,owned,value in reversed(self.previous):
            if owned:setattr(obj,key,value)
            else:delattr(obj,key)
        if not all((key in obj.__dict__)==owned and (not owned or obj.__dict__[key] is value) for obj,key,owned,value in self.previous):raise RuntimeError('Binding restoration differs')
        self.closed=True
