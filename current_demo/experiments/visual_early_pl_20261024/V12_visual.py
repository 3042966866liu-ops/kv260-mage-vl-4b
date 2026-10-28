"""Current22 in both arms, with only original-width V12 offloaded in B."""
import copy
from pathlib import Path
from M455_twentytwo_visual_scope523290 import TwentytwoPLRangeScope
from M455_combination_visual52301 import AdaptiveVisualBatchCheck
from V12_borrowed import BorrowedVisual


class V12BatchCheck(AdaptiveVisualBatchCheck):
    def __init__(self,cases,submit):
        assert set(cases)==set(range(12,24)) and all(set(c)=={'fc1','fc2'} for c in cases.values())
        # Original batch/retry state machine; exact additional V12 positions.
        self.cases=copy.deepcopy(cases);self.submit=submit
        self.positions=tuple((i,part,start) for i in range(12,24) for part in ('fc1','fc2') for start in range(0,392,32))
        self.groups=[];self.current=-1
    def require_complete(self,batches):
        assert len(self.groups)==312 and self.current==311 and set(batches)==set(map(str,range(12,24)))
        for row in self.groups:
            observed=batches[str(row['layer'])][row['part']][row['start']//32];shifts=row['attempted_shifts']
            assert observed['start']==row['start'] and observed['rows']==min(32,392-row['start'])
            assert observed['initial_shift']==shifts[0] and observed['selected_shift']==shifts[-1]
            assert observed['attempted_shifts']==shifts and observed['physical_calls']==row['completed_calls']==len(shifts)
        return dict(logical_batches=312,physical_calls=sum(len(r['attempted_shifts']) for r in self.groups),
            adaptive_attempts=copy.deepcopy(self.groups),old_saved_wire_or_shift_pass_claimed=False)


class V12Scope(TwentytwoPLRangeScope):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        assert self.selected==tuple(range(13,24)) and set(range(12,24))<=set(self.targets)
        # RangeScope's unchanged hooks/release/one-active-layer checks use this explicit set.
        self.selected=tuple(range(12,24))


class V12VisualProvider:
    def __init__(self,baseline,plan,lower_root):
        self.baseline=baseline;self.original=baseline.original;self.idle=baseline.idle;self.plan=plan
        self.lower_root=Path(lower_root);self.active=False;self.in_request=False
        from target import resolve_target,verify_matrices
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        p=self.original;target,topology=resolve_target(p.engine.vision.vision,M206ProgressLayer,M196PrecisionBoundary,p.torch)
        matrices=verify_matrices(target,M207FP32GemmW4Linear,p.torch)
        assert matrices==plan['native_V12_matrices']
        self.targets=dict(p.targets);self.targets[12]=target
        self.cases=copy.deepcopy(baseline.cases);self.windows=copy.deepcopy(baseline.windows)
        self.cases[12]=copy.deepcopy(plan['V12_chains']);self.windows[12]=copy.deepcopy(plan['V12_windows'])
        assert set(self.cases)==set(self.windows)==set(range(12,24))
    def choose(self,arm):
        assert arm in ('A','B') and not self.in_request
        self.idle();self.active=arm=='B'
    def select(self,current22):
        assert current22 is True and not self.in_request
        self.idle();self.baseline.select(True)
    def __call__(self,*args,**kwargs):
        if not self.active:return self.baseline(*args,**kwargs)
        p=self.original;self.idle()
        assert not self.in_request and not p.disposed and p.current_owner is p.current_scope is None
        assert not p.result.get('language_scope_active',False)
        self.in_request=True;owner=None
        try:
            with BorrowedVisual(p.runtime,p.policy,p.base,p.result,enabled=True,
                    language_active=lambda:p.result.get('language_scope_active',False)) as owner:
                p.current_owner=owner;check=V12BatchCheck(self.cases,owner.submit)
                def stage(index,part,chain):
                    root=self.lower_root if index==12 else (self.baseline.cropped_root if index in self.baseline.crops else p.root)
                    return owner.stage(index,part,chain,self.windows[index][part],root)
                scope=V12Scope(p.torch,p.engine.vision.vision.encoder.layers,self.targets,
                    lambda i:dict(chains=self.cases[i]),p.initial,p.abi.visual_host(),lambda *unused:None,lambda label:None,
                    stage,check,cropped=True,crops=self.baseline.crops)
                p.current_scope=scope;p.result['vision_request_active']=True
                try:
                    with scope:visual=p.original_vision_call(p.engine.vision,*args,**kwargs)
                finally:p.result['vision_request_active']=False
                observed=check.require_complete(scope.batches)
            expected=sum(r['bytes'] for i in range(12,24) for part in ('fc1','fc2') for r in self.windows[i][part])
            assert scope.complete and scope.restored and scope.peak_live_layer_scopes==1
            assert not owner.retained and not owner.entered and len(owner.rows)==observed['physical_calls']
            assert len(owner.staging)==24 and sum(r['bytes'] for r in owner.staging)==expected
            p.result.setdefault('V12_visual_requests',[]).append(dict(selected=list(range(12,24)),staging=owner.staging,**observed))
            p.current_owner=p.current_scope=None;self.in_request=False
            return visual
        finally:
            if owner is not None and (owner.retained or p.policy.active):p.current_owner=owner
