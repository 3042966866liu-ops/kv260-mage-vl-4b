"""Default-off isolated Prefill scope. Does not modify release or runtime methods.

Only the original final T32 batch is retained after full final-layer Attention.
An exceptional call retains its owner; this helper never frees DMA or workers.
"""
import ast
import copy
import hashlib
from pathlib import Path
import threading

SOURCE_SHA='24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09'

class RetainedTailOwnerError(RuntimeError): pass

def call_plan(tokens):
    if not isinstance(tokens,int) or isinstance(tokens,bool) or not 1<=tokens<=1024:
        raise ValueError('Token count outside original contract')
    batches=(tokens+31)//32
    return dict(tokens=tokens,tail_start=(batches-1)*32,tail_count=tokens-(batches-1)*32,
                original_logical=154*batches+8,logical=154*batches+8-3*(batches-1))

class LastLayerTailScope:
    def __init__(self,model,policy,resident,*,tokens,enabled=False):
        if not enabled:raise RuntimeError('M397 disabled by default')
        if tokens not in (30,159):raise ValueError('Only independent fixed30/159 diagnostics admitted')
        self.plan=call_plan(tokens);self.model=model;self.policy=policy;self.resident=resident
        self.closed=False;self.retained=False;self.invoked=False;self.selected=[];self.bindings=[]
        self.barrier()
    def barrier(self):
        if not self.resident() or not self.policy.safe() or any(t.name.startswith(('m238-pack','m238-parse')) for t in threading.enumerate()):
            raise RetainedTailOwnerError('Complete runtime/safe drained DMA and original futures required')
    def select(self,model,layer,attended,residual):
        if model is not self.model or self.closed or self.retained or layer!=35 or self.selected:
            raise RetainedTailOwnerError('Unexpected/stale last-layer selection')
        n=self.plan['tokens'];start=self.plan['tail_start']
        if attended.shape!=(n,4096) or residual.shape!=(n,2560) or str(attended.dtype)!='float32' or str(residual.dtype)!='float32':
            raise ValueError('Original full Attention/residual shape or dtype differs')
        self.selected.append(dict(layer=35,original_token_start=start,local_token_start=0,token_count=n-start,
                                  original_dma_slot=(start//32)&1,candidate_dma_slot=0))
        return attended[start:],residual[start:]
    def bind(self,module):
        if self.closed or self.retained or self.bindings:raise RetainedTailOwnerError('Only one live binding allowed')
        raw=Path(module.__file__).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise RuntimeError('Frozen actual M241 source differs')
        for name,value in dict(LAYERS=36,HIDDEN=2560,HEADS=32,KV_HEADS=8,HEAD_DIM=128,MAX_CONTEXT=1024).items():
            if getattr(module,name,None)!=value:raise RuntimeError('Original module dimension/context differs: '+name)
        from m401_prefill_source import derive
        namespace=dict(vars(module));namespace['_m397_select']=self.select
        generated=derive(raw)
        exec(compile('from __future__ import annotations\n'+generated,'<m401-frozen-original-prefill-tail>','exec'),namespace)
        self.bindings.append(namespace);candidate=namespace['prefill']
        def invoke(model,hidden):
            if model is not self.model or self.closed or self.retained or self.invoked:raise RetainedTailOwnerError('Stale/busy one-request scope')
            if hidden.shape!=(self.plan['tokens'],2560):raise ValueError('Diagnostic input shape differs')
            self.barrier();self.invoked=True
            try:
                result=candidate(model,hidden)
                if len(self.selected)!=1 or result[1].shape!=(151936,) or len(result[2].keys)!=36 or len(result[2].values)!=36:
                    raise RuntimeError('Output contract differs')
                if any(v.shape!=(self.plan['tokens'],8,128) for v in result[2].keys+result[2].values):
                    raise RuntimeError('Full K/V must be retained')
                self.barrier();return result
            except BaseException as exc:
                self.retained=True
                raise RetainedTailOwnerError('Failed request; retain scope, process and DMA owner') from exc
        return invoke
    def close(self):
        if self.closed:return
        if self.retained:raise RetainedTailOwnerError('Failure owner must be retained')
        self.barrier()
        for ns in self.bindings:ns.pop('_m397_select',None)
        self.bindings.clear();self.model=None;self.resident=None;self.policy=None;self.closed=True
    def report(self):
        return dict(plan=dict(self.plan),selected=list(self.selected),invoked=self.invoked,closed=self.closed,
                    retained=self.retained,binding_callback_removed=not self.bindings,extra_dma_allocations=0,
                    ps_prefetch=False,parser_workers=1,silu_workspace=False)
