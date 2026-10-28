"""Exact V14/V15/V21 substitutions within all eleven original PL visual layers."""
import copy
from m430_timed_scope import TimedPLRangeScope
from m411_mlp_binding import PLMLPBinding
from M455_combination_visual52301 import AdaptiveVisualBatchCheck
from M455_twentytwo_cropped_visual523289 import TwentytwoCroppedVisualBinding

class TwentytwoPLRangeScope(TimedPLRangeScope):
    def __init__(self,*args,cropped=False,crops=None,**kwargs):
        super().__init__(*args,**kwargs)
        if type(cropped)is not bool or set(crops)!={14,15,21}:raise ValueError('Exact three explicit visual recipes required')
        self.cropped,self.crops=cropped,crops
    def before(self,index):
        if not self.cropped or index not in self.crops:return super().before(index)
        if self.active is not None or index!=len(self.seen):raise RuntimeError('Actual layer order or active scope differs')
        self.checkpoint('layer'+str(index)+':before');case=self.load_case(index);crop=self.crops[index]
        binding=TwentytwoCroppedVisualBinding(self.torch,self.targets[index].mlp,case['chains'],crop['kept_ids'],crop['r1'],self.initial,self.host,
            lambda part,chain:self.stage(index,part,chain),
            lambda part,chain,start,shift,packet:self.wire_check(index,part,chain,start,shift,packet),PLMLPBinding,layer=index)
        self.active=(index,binding);binding.__enter__();self.peak_live_layer_scopes=1

class TwentytwoVisualProvider:
    def __init__(self,original,*,crops,cropped_root,idle):
        if not callable(idle):raise ValueError('Actual lifecycle idle predicate required')
        idle()
        if original.abi.variant!='B' or set(original.dense_cases)!=set(range(13,24)):raise ValueError('Actual complete M455 provider required')
        if set(crops)!={14,15,21}:raise ValueError('Exact current22 visual set required')
        self.original=original;self.idle=idle;self.cases=copy.deepcopy(original.dense_cases);self.windows=copy.deepcopy(original.windows)
        self.crops=crops
        for index,crop in crops.items():
            if set(crop)!={'chains','windows','kept_ids','r1'} or set(crop['chains'])!={'fc1','fc2'} or set(crop['windows'])!={'fc1','fc2'}:raise ValueError('Complete explicit visual recipe required')
            self.cases[index]=copy.deepcopy(crop['chains']);self.windows[index]=copy.deepcopy(crop['windows'])
        self.cropped_root=cropped_root;self.active=False;self.in_request=False
    def select(self,active):
        if type(active)is not bool or self.in_request:raise ValueError('Selection only between complete requests')
        self.idle();self.active=active
    def __call__(self,*args,**kwargs):
        from m431_borrowed_visual import BorrowedVisual
        p=self.original;self.idle()
        if self.in_request or p.disposed or p.current_owner is not None or p.current_scope is not None or p.result.get('language_scope_active',False):raise RuntimeError('Previous visual/language ownership unresolved')
        self.in_request=True;owner=scope=None;cases=self.cases if self.active else p.dense_cases;windows=self.windows if self.active else p.windows
        try:
            with BorrowedVisual(p.runtime,p.policy,p.base,p.result,enabled=True,language_active=lambda:p.result.get('language_scope_active',False)) as owner:
                p.current_owner=owner;check=AdaptiveVisualBatchCheck(cases,owner.submit)
                def stage(i,part,c):
                    root=self.cropped_root if self.active and i in self.crops else p.root
                    return owner.stage(i,part,c,windows[i][part],root)
                scope=TwentytwoPLRangeScope(p.torch,p.engine.vision.vision.encoder.layers,p.targets,lambda i:dict(chains=cases[i]),p.initial,p.abi.visual_host(),
                    lambda *unused:None,lambda label:None,stage,check,cropped=self.active,crops=self.crops)
                p.current_scope=scope;p.result['vision_request_active']=True
                try:
                    with scope:visual=p.original_vision_call(p.engine.vision,*args,**kwargs)
                finally:p.result['vision_request_active']=False
                observed=check.require_complete(scope.batches)
            expected_bytes=sum(row['bytes'] for i in range(13,24) for part in ('fc1','fc2') for row in windows[i][part])
            if not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=1 or owner.retained or owner.entered or len(owner.rows)!=observed['physical_calls'] or len(owner.staging)!=22 or sum(row['bytes'] for row in owner.staging)!=expected_bytes:
                raise RuntimeError('Actual whole visual PL lifecycle incomplete')
            p.result.setdefault('twentytwo_visual_requests',[]).append(dict(cropped_layers=[14,15,21] if self.active else [],staging=owner.staging,**observed))
            p.current_owner=p.current_scope=None;self.in_request=False;return visual
        finally:
            if owner is not None and (owner.retained or p.policy.active):p.current_owner=owner
