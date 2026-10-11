"""Same validated four bindings, with numerical hashes outside request timing."""
from contextlib import ExitStack
from m423_request_visual import VisualProvider


class TimedVisualProvider(VisualProvider):
    def __init__(self,*a,enabled=False,**kw):
        if enabled is not True:raise RuntimeError('Timed visual candidate disabled by default')
        super().__init__(*a,**kw)
        self.enabled=True

    def __call__(self,index,*args,**kw):
        from m411_mlp_binding import PLMLPBinding
        from m422_borrowed_visual import BorrowedVisual
        if getattr(self,'enabled',False) is not True or index not in (0,1) or self.current_owner is not None or self.result.get('language_scope_active',False):
            raise RuntimeError('Timed visual scope/order/owner invalid')
        owner=None;bindings={}
        try:
            with ExitStack() as stack:
                if index==1:
                    owner=stack.enter_context(BorrowedVisual(self.runtime,self.policy,self.base,self.result,
                        enabled=True,numerical_reference=None,
                        language_active=lambda:self.result.get('language_scope_active',False)))
                    self.current_owner=owner
                    for layer in (12,13):
                        stage=lambda part,c,layer=layer:owner.stage(layer,part,c,self.windows[layer][part],self.root)
                        submit=lambda part,c,start,shift,packet,layer=layer:owner.submit(layer,part,c,start,shift,packet)
                        bindings[layer]=stack.enter_context(PLMLPBinding(self.torch,self.targets[layer].mlp,
                            self.cases[layer],self.initial,self.host,stage,submit))
                self.result['vision_request_active']=True
                try:
                    # The stored original class call bypasses only the timer wrapper.
                    # Synthetic component fixtures supply an explicitly fake callable.
                    call=getattr(self,'original_vision_call',None)
                    if call is None:visual=self.engine.vision(*args,**kw)
                    else:visual=call(self.engine.vision,*args,**kw)
                finally:self.result['vision_request_active']=False
            if any(not x.restored or x.calls!={'fc1':1,'fc2':1} for x in bindings.values()):raise RuntimeError('All four timed bindings must restore')
            if owner is not None:
                if owner.retained or owner.entered or len(owner.rows)!=52 or len(owner.staging)!=4:raise RuntimeError('Timed visual completion/ownership incomplete')
                self.result['visual_staging']=owner.staging
                self.result['borrowed_buffer_identity_preserved']=True
                self.result['visual_static_cache_invalidated']=self.runtime._programmed_config is None and self.runtime._programmed_weight_addresses is None
            self.current_owner=None
            return visual
        finally:
            if owner is not None and (owner.retained or self.policy.active):self.current_owner=owner
