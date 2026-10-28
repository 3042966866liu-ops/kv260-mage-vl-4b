"""Original full visual schedule; only select the corresponding wire ABI."""
import copy
from m432_request_visual import VisualProvider
from m431_borrowed_visual import BorrowedVisual
from m430_timed_scope import TimedPLRangeScope
from m429_pl_range import SavedWireCheck
from m455_runtime_abi01 import convert_chain


class LayoutBatchCheck(SavedWireCheck):
    def __init__(self,references,submit,variant):
        super().__init__(references,submit);self.variant=variant
    def __call__(self,index,part,chain,start,shift,packet):
        position=(index,part,start,shift)
        if len(self.seen)>=len(self.expected_position) or position!=self.expected_position[len(self.seen)]:raise ValueError('Original visual batch/shift order differs')
        old=self.references[str(index)][part][start//32];size=old['output_bytes']//(2 if self.variant=='B' else 1)
        if len(packet)!=old['input_bytes'] or chain['output_bytes']!=size:raise ValueError('Original input/new layout wire geometry differs')
        raw=self.submit(index,part,chain,start,shift,packet)
        if len(raw)!=size:raise ValueError('Full visual output size differs')
        self.seen.append(position);return raw


class TimedVisualProvider(VisualProvider):
    def __init__(self,*args,enabled=False,abi=None,**kwargs):
        if enabled is not True or abi is None:raise RuntimeError('Original94 dual-ABI visual scope disabled')
        super().__init__(*args,**kwargs);self.abi=abi
        self.legacy_cases=copy.deepcopy(self.cases)
        self.dense_cases={i:{part:convert_chain(c) for part,c in cases.items()} for i,cases in self.legacy_cases.items()}
    def __call__(self,index,*args,**kwargs):
        if index!=1 or self.disposed or self.current_owner is not None or self.current_scope is not None or self.result.get('language_scope_active',False):raise RuntimeError('Original visual owner/scope differs')
        owner=scope=None
        def forward():
            self.result['vision_request_active']=True
            try:return self.original_vision_call(self.engine.vision,*args,**kwargs)
            finally:self.result['vision_request_active']=False
        try:
            cases=self.dense_cases if self.abi.variant=='B' else self.legacy_cases
            with BorrowedVisual(self.runtime,self.policy,self.base,self.result,enabled=True,
                language_active=lambda:self.result.get('language_scope_active',False)) as owner:
                self.current_owner=owner;guard=LayoutBatchCheck(self.reference,owner.submit,self.abi.variant)
                scope=TimedPLRangeScope(self.torch,self.engine.vision.vision.encoder.layers,self.targets,
                    lambda i:dict(chains=cases[i]),self.initial,self.abi.visual_host(),lambda *unused:None,lambda label:None,
                    lambda i,part,c:owner.stage(i,part,c,self.windows[i][part],self.root),guard)
                self.current_scope=scope
                with scope:visual=forward()
                guard.require_complete()
            if not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=1 or owner.retained or owner.entered or len(owner.rows)!=286 or len(owner.staging)!=22 or sum(r['bytes'] for r in owner.staging)!=49020928:
                raise RuntimeError('Original full visual staged lifecycle differs')
            self.result.update(visual_staging=owner.staging,borrowed_buffer_identity_preserved=True,
                visual_static_cache_invalidated=self.runtime._programmed_config is None and self.runtime._programmed_weight_addresses is None,
                visual_bindings_restored=True,peak_live_visual_layer_scopes=1,visual_matched_wire_batches=len(guard.seen))
            self.current_owner=self.current_scope=None;return visual
        finally:
            if owner is not None and (owner.retained or self.policy.active):self.current_owner=owner
