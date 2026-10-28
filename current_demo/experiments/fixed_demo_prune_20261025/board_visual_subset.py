"""Retained visual blocks, unchanged borrowed-owner and completion checks."""
import copy
from contextlib import nullcontext
from M455_combination_visual52301 import AdaptiveVisualBatchCheck
from M455_twentytwo_visual_scope523290 import TwentytwoPLRangeScope

class SubsetBatchCheck(AdaptiveVisualBatchCheck):
    def __init__(self,cases,submit,retained):
        selected=tuple(retained)
        if selected!=tuple(sorted(set(selected))) or not set(selected)<=set(range(13,24)) or set(cases)!=set(selected):raise ValueError('Exact retained PL subset required')
        if any(set(cases[i])!={'fc1','fc2'} for i in cases):raise ValueError('Both original Linear chains required')
        self.cases=copy.deepcopy(cases);self.submit=submit;self.retained=selected
        self.positions=tuple((i,part,start) for i in selected for part in ('fc1','fc2') for start in range(0,392,32))
        self.groups=[];self.current=-1
    def require_complete(self,batches):
        logical=26*len(self.retained)
        if len(self.groups)!=logical or self.current!=logical-1 or set(batches)!=set(map(str,self.retained)):raise ValueError('Complete retained-layer batch sequence required')
        for row in self.groups:
            observed=batches[str(row['layer'])][row['part']][row['start']//32];shifts=row['attempted_shifts']
            if (observed['start']!=row['start'] or observed['rows']!=min(32,392-row['start']) or
                observed['initial_shift']!=shifts[0] or observed['selected_shift']!=shifts[-1] or
                observed['attempted_shifts']!=shifts or observed['physical_calls']!=len(shifts) or row['completed_calls']!=len(shifts)):
                raise RuntimeError('Actual parser selection / retries / physical completion disagree')
        return dict(logical_batches=logical,physical_calls=sum(len(r['attempted_shifts']) for r in self.groups),adaptive_attempts=copy.deepcopy(self.groups),old_saved_wire_or_shift_pass_claimed=False)

class SubsetPLScope(TwentytwoPLRangeScope):
    def __init__(self,*args,retained,**kwargs):
        super().__init__(*args,**kwargs)
        self.retained=tuple(retained);self.selected=tuple(i for i in self.retained if i>=13)
    def before(self,index):
        if index not in self.retained:
            if self.active is not None or index!=len(self.seen):raise RuntimeError('Deleted-block callback boundary differs')
            self.checkpoint('layer'+str(index)+':bypass');return
        return super().before(index)

class SubsetVisualProvider:
    def __init__(self,parent,retained,idle):
        idle();self.parent,self.original,self.idle=parent,parent.original,idle
        self.retained=tuple(retained)
        if not self.retained or self.retained!=tuple(sorted(set(self.retained))) or not set(self.retained)<=set(range(24)):raise ValueError('Retained visual block list required')
        self.pl=tuple(i for i in self.retained if i>=13);self.in_request=False
    def __call__(self,*args,**kwargs):
        from m431_borrowed_visual import BorrowedVisual
        p=self.original;self.idle()
        if self.in_request or p.disposed or p.current_owner is not None or p.current_scope is not None or p.result.get('language_scope_active',False):raise RuntimeError('Previous owner or visual scope unresolved')
        if not self.parent.active:raise RuntimeError('Original current22 crop binding must remain selected')
        self.in_request=True;owner=scope=None
        cases={i:self.parent.cases[i] for i in self.pl};windows={i:self.parent.windows[i] for i in self.pl}
        try:
            context=BorrowedVisual(p.runtime,p.policy,p.base,p.result,enabled=True,language_active=lambda:p.result.get('language_scope_active',False)) if self.pl else nullcontext(None)
            with context as owner:
                p.current_owner=owner
                def forbidden(*args):raise RuntimeError('No visual PL submit allowed for an empty retained PL set')
                check=SubsetBatchCheck(cases,owner.submit if owner else forbidden,self.pl)
                def stage(i,part,c):
                    if owner is None or i not in self.pl:raise RuntimeError('Excluded visual layer staging forbidden')
                    root=self.parent.cropped_root if i in self.parent.crops else p.root
                    return owner.stage(i,part,c,windows[i][part],root)
                scope=SubsetPLScope(p.torch,p.engine.vision.vision.encoder.layers,p.targets,lambda i:dict(chains=cases[i]),p.initial,p.abi.visual_host(),
                    lambda *unused:None,lambda label:None,stage,check,cropped=True,crops=self.parent.crops,retained=self.retained)
                p.current_scope=scope;p.result['vision_request_active']=True
                try:
                    with scope:visual=p.original_vision_call(p.engine.vision,*args,**kwargs)
                finally:p.result['vision_request_active']=False
                observed=check.require_complete(scope.batches)
            expected=sum(row['bytes'] for i in self.pl for part in ('fc1','fc2') for row in windows[i][part])
            actual_staging=[] if owner is None else owner.staging
            if (not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=int(bool(self.pl)) or
                len(actual_staging)!=2*len(self.pl) or sum(row['bytes'] for row in actual_staging)!=expected or
                owner is not None and (owner.retained or owner.entered or len(owner.rows)!=observed['physical_calls'])):
                raise RuntimeError('Retained visual full lifecycle incomplete')
            p.result.setdefault('subset_visual_requests',[]).append(dict(retained_visual=list(self.retained),retained_PL=list(self.pl),staging=actual_staging,**observed))
            p.current_owner=p.current_scope=None;self.in_request=False;return visual
        finally:
            if owner is not None and (owner.retained or p.policy.active):p.current_owner=owner
