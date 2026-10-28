"""Original eleven-layer PL schedule with an explicit V14 crop and retry log.

No allocation/programming/device API; the original borrowed resource owner
provides stage/submit. Old saved shifts/widths are never relabelled as new gold.
"""
import copy
from m430_timed_scope import TimedPLRangeScope
from m411_mlp_binding import PLMLPBinding
from M455_cropped_visual_binding52301 import CroppedVisualBinding

class AdaptiveVisualBatchCheck:
    def __init__(self,cases,submit):
        if set(cases)!=set(range(13,24)) or any(set(cases[i])!={'fc1','fc2'} for i in cases):raise ValueError('All eleven PL layers required')
        self.cases=copy.deepcopy(cases);self.submit=submit
        self.positions=tuple((i,part,start) for i in range(13,24) for part in ('fc1','fc2') for start in range(0,392,32))
        self.groups=[];self.current=-1
    def __call__(self,index,part,chain,start,shift,packet):
        position=(index,part,start)
        if type(shift)is not int or not 0<=shift<=6 or index not in self.cases or part not in self.cases[index] or chain!=self.cases[index][part]:raise ValueError('Explicit current chain/shift required')
        if len(packet)!=chain['input_bytes']:raise ValueError('Actual current input geometry differs')
        if self.current>=0 and position==self.positions[self.current]:
            attempts=self.groups[-1]['attempted_shifts']
            if len(attempts)>=7 or shift!=attempts[-1]-1:raise ValueError('Only original bounded descending retry allowed')
            attempts.append(shift)
        else:
            next_index=self.current+1
            if next_index>=len(self.positions) or position!=self.positions[next_index]:raise ValueError('Complete original layer/part/T32 order required')
            self.current=next_index;self.groups.append(dict(layer=index,part=part,start=start,attempted_shifts=[shift],completed_calls=0))
        # Exceptions propagate. They do not mark a transaction or owner safe.
        raw=self.submit(index,part,chain,start,shift,packet)
        if len(raw)!=chain['output_bytes']:raise ValueError('Actual current output geometry differs')
        self.groups[-1]['completed_calls']+=1
        return raw
    def require_complete(self,batches):
        if len(self.groups)!=286 or self.current!=285 or set(batches)!=set(map(str,range(13,24))):raise ValueError('All eleven actual PL layers/286 logical batches required')
        for row in self.groups:
            observed=batches[str(row['layer'])][row['part']][row['start']//32]
            shifts=row['attempted_shifts']
            if (observed['start']!=row['start'] or observed['rows']!=min(32,392-row['start']) or
                observed['initial_shift']!=shifts[0] or observed['selected_shift']!=shifts[-1] or
                observed['attempted_shifts']!=shifts or observed['physical_calls']!=len(shifts) or row['completed_calls']!=len(shifts)):
                raise RuntimeError('Actual finite parser selection and physical attempts disagree')
        return dict(logical_batches=286,physical_calls=sum(len(r['attempted_shifts']) for r in self.groups),
            adaptive_attempts=copy.deepcopy(self.groups),old_saved_wire_or_shift_pass_claimed=False)

class CombinationPLRangeScope(TimedPLRangeScope):
    def __init__(self,*args,cropped=False,kept_ids=None,r1=None,**kwargs):
        super().__init__(*args,**kwargs)
        if type(cropped)is not bool:raise ValueError('Explicit original/combination selection required')
        self.cropped,self.kept_ids,self.r1=cropped,kept_ids,r1
    def before(self,index):
        if not self.cropped or index!=14:return super().before(index)
        if self.active is not None or index!=len(self.seen):raise RuntimeError('Actual layer order or active scope differs')
        self.checkpoint('layer14:before');case=self.load_case(14)
        binding=CroppedVisualBinding(self.torch,self.targets[14].mlp,case['chains'],self.kept_ids,self.r1,self.initial,self.host,
            lambda part,chain:self.stage(14,part,chain),
            lambda part,chain,start,shift,packet:self.wire_check(14,part,chain,start,shift,packet),PLMLPBinding)
        self.active=(14,binding);binding.__enter__();self.peak_live_layer_scopes=1

class CombinationVisualProvider:
    """Use an already constructed/identity-checked original M455 provider.

    Only the V14 two-chain/window recipe is substituted. Both arms retain all
    eleven PL layers, original adaptive arithmetic and one live MLP binding.
    """
    def __init__(self,original,*,cropped_chains,cropped_windows,cropped_root,kept_ids,r1,idle):
        if not callable(idle):raise ValueError('Actual lifecycle idle predicate required')
        idle()
        if original.abi.variant!='B' or set(original.dense_cases)!=set(range(13,24)):raise ValueError('Actual complete M455 provider required')
        if set(cropped_chains)!={'fc1','fc2'} or set(cropped_windows)!={'fc1','fc2'}:raise ValueError('Both explicit cropped families required')
        # Do not mutate original PLAN, its old wire references, or its providers.
        self.original=original;self.idle=idle;self.cases=copy.deepcopy(original.dense_cases)
        self.cases[14]=copy.deepcopy(cropped_chains);self.windows=copy.deepcopy(original.windows);self.windows[14]=copy.deepcopy(cropped_windows)
        self.cropped_root=cropped_root;self.kept_ids=kept_ids;self.r1=r1;self.active=False;self.in_request=False
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
                    root=self.cropped_root if self.active and i==14 else p.root
                    return owner.stage(i,part,c,windows[i][part],root)
                scope=CombinationPLRangeScope(p.torch,p.engine.vision.vision.encoder.layers,p.targets,lambda i:dict(chains=cases[i]),p.initial,p.abi.visual_host(),
                    lambda *unused:None,lambda label:None,stage,check,cropped=self.active,kept_ids=self.kept_ids,r1=self.r1)
                p.current_scope=scope;p.result['vision_request_active']=True
                try:
                    with scope:visual=p.original_vision_call(p.engine.vision,*args,**kwargs)
                finally:p.result['vision_request_active']=False
                observed=check.require_complete(scope.batches)
            expected_bytes=sum(row['bytes'] for i in range(13,24) for part in ('fc1','fc2') for row in windows[i][part])
            if not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=1 or owner.retained or owner.entered or len(owner.rows)!=observed['physical_calls'] or len(owner.staging)!=22 or sum(row['bytes'] for row in owner.staging)!=expected_bytes:
                raise RuntimeError('Actual whole visual PL lifecycle incomplete')
            p.result.setdefault('combination_visual_requests',[]).append(dict(cropped_V14=self.active,staging=owner.staging,**observed))
            p.current_owner=p.current_scope=None;self.in_request=False;return visual
        finally:
            # Do not erase an unresolved original owner/scope on failure.
            if owner is not None and (owner.retained or p.policy.active):p.current_owner=owner
