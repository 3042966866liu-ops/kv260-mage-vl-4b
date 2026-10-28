"""Explicit fake wire batches and scope rejection tests; no device or model."""
import copy,importlib.util,json
from pathlib import Path
def check(pkg):
    from V12_visual import V12BatchCheck
    cases={i:{part:dict(input_bytes=17,output_bytes=9) for part in ('fc1','fc2')} for i in range(12,24)}
    checker=V12BatchCheck(cases,lambda *args:b'x'*9);batches={str(i):{'fc1':[],'fc2':[]} for i in range(12,24)}
    for i,part,start in checker.positions:
        assert checker(i,part,cases[i][part],start,6,b'y'*17)==b'x'*9
        batches[str(i)][part].append(dict(start=start,rows=min(32,392-start),initial_shift=6,selected_shift=6,attempted_shifts=[6],physical_calls=1))
    assert checker.require_complete(batches)['physical_calls']==312
    rejected=0
    for action in [lambda:V12BatchCheck({i:c for i,c in cases.items() if i!=12},lambda *args:b'x'*9),
        lambda:V12BatchCheck(cases,lambda *args:b'x'*9)(13,'fc1',cases[13]['fc1'],0,6,b'y'*17),
        lambda:V12BatchCheck(cases,lambda *args:b'x'*9)(12,'fc1',cases[12]['fc1'],0,7,b'y'*17),
        lambda:checker.require_complete({k:v for k,v in batches.items() if k!='12'})]:
        try:action()
        except (AssertionError,ValueError,RuntimeError):rejected+=1
        else:raise AssertionError('Out-of-scope batch accepted')
    assert rejected==4
    from V12_borrowed import BorrowedVisual
    owner=BorrowedVisual.__new__(BorrowedVisual);owner.entered=True
    for index in (11,24):
        try:owner.stage(index,'fc1',{},[{}]*4,Path(pkg))
        except RuntimeError:rejected+=1
        else:raise AssertionError('Unadmitted layer stage accepted')
    assert rejected==6
    return dict(explicit_fake_wire=True,complete_batches=312,negative_checks=rejected,device_API_calls=0,model_forwards=0)
