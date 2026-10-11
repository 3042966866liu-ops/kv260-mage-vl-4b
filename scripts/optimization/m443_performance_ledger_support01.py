"""Explicit configuration-credit component fixtures; no board execution or credits."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import m351_workflow as w
from m441_host_io08 import atomic
import m443_performance_ledger01 as module


def main():
    new_path=w.BASE/'runs/M443-buildid-board-01/BOARD_RESULT.json';build=json.loads(new_path.read_bytes())
    new=copy.deepcopy(build['configuration_record']);new.update(index=2,variant='B')
    old_path=w.BASE/'runs/M441-complete-request-performance-board-17/BOARD_RESULT.json'
    old_raw=json.loads(old_path.read_bytes());old=copy.deepcopy(next(x for x in old_raw['configuration_CMA_ledger'] if x['bit_sha256']==module.M441_BIT));old['variant']='A'
    app=new['application_sha256'];manifest=new['manifest_sha256']
    assert module.validate(new,app,manifest)==module.validate(old,app,manifest)=={'reserved:alloc_pages_success':1904}
    mutations=[]
    for key,value in [('variant','A'),('pid',1),('kernel','wrong'),('page_size',8192),('bit_sha256','0'*64),('pages',1905),('application_sha256','0'*64),('manifest_sha256','0'*64),('shell_closure_sha256','0'*64),('overlay_returned',False),('configuration_credits_granted',1904)]:
        bad=copy.deepcopy(new);bad[key]=value;mutations.append(bad)
    for key,value in [('own_instance_removed',False),('observer_errors',['explicit']),('elapsed_trace_s',31),('pid',1),('trace_sha256','0'*64)]:
        bad=copy.deepcopy(new);bad['trace'][key]=value;mutations.append(bad)
    bad=copy.deepcopy(new);bad['after']['reserved:alloc_pages_success']+=1;mutations.append(bad)
    bad=copy.deepcopy(new);bad['after']['reserved:alloc_pages_fail']=1;mutations.append(bad)
    bad=copy.deepcopy(new);bad['trace']['stats']['cpu0']=bad['trace']['stats']['cpu0'].replace('overrun: 0','overrun: 1');mutations.append(bad)
    for record in mutations:
        try:module.validate(record,app,manifest)
        except (AssertionError,KeyError,ValueError,RuntimeError):pass
        else:raise AssertionError('Unknown configuration accepted for credit')
    def ledger(record):
        obj=module.StagePolicy.__new__(module.StagePolicy)
        obj.application_sha,obj.manifest_sha=app,manifest;obj.credits={};obj.initial_counts=copy.deepcopy(record['before'])
        obj.result={'configuration_CMA_ledger':[]};obj.raw_counters=lambda:copy.deepcopy(record['after'])
        return obj
    obj=ledger(new);record=copy.deepcopy(new);obj.commit(record)
    assert obj.credits=={'reserved:alloc_pages_success':1904} and obj.accounted_counts()==new['before']
    assert record['original_baseline_unchanged']==new['before'] and record['verified_released_configuration_pages']==obj.credits
    obj=ledger(new);obj.initial_counts['reserved:alloc_pages_success']+=1
    try:obj.commit(copy.deepcopy(new))
    except AssertionError:pass
    else:raise AssertionError('Changed cumulative baseline accepted')
    assert not obj.credits and not obj.result['configuration_CMA_ledger']
    bad=copy.deepcopy(new);bad['after']['reserved:alloc_pages_success']+=1;obj=ledger(bad)
    try:obj.commit(bad)
    except AssertionError:pass
    else:raise AssertionError('Unknown allocation credited')
    assert not obj.credits and not obj.result['configuration_CMA_ledger']
    # Actual wrapper retains a returned object when post-programming verification fails.
    token=object()
    class TraceFixture:
        details={'own_instance_removed':False}
        def start(self):pass
        def stop(self):self.details['own_instance_removed']=True;return copy.deepcopy(new['trace'])
    obj=ledger(new);obj.sealed=True;obj.pending=dict(trace=TraceFixture(),path='/explicit-fixture.bit',index=2,variant='B',bit_sha256=module.BIT_SHA,bit_bytes=7797914)
    obj.configuration_overlay_history=[]
    with patch.object(module.os,'sysconf',lambda name:4096,create=True),patch.object(module.platform,'release',lambda:module.KERNEL),patch.object(module.os,'getpid',lambda:new['pid']):
        try:obj.wrap_overlay(lambda *a,**kw:token)('/explicit-fixture.bit',download=True)
        except AssertionError:pass
        else:raise AssertionError('Zero-delta explicit fixture accepted')
    assert obj.configuration_overlay_history==[token] and obj.pending is None and not obj.credits and len(obj.result['configuration_CMA_rejected'])==1
    paths=[Path(__file__),w.HERE/'m443_performance_ledger01.py',w.HERE/'m443_performance_trace01.py',w.HERE/'m441_cma_ledger15.py',w.HERE/'m441_cma_trace15.py',w.HERE/'m443_configuration01.py',w.HERE/'m443_cma_contract01.py',new_path,old_path]
    out=w.BASE/'runs/M443-performance-ledger-support-01/RESULT.json'
    result=dict(status='PASS_M443_PERFORMANCE_LEDGER_COMPONENT_FIXTURES01',explicit_fixture_only=True,actual_new_bit_application_raw_sha256=w.sha(new_path),old_m441_raw_sha256=w.sha(old_path),configuration_negative_checks=len(mutations),independent_validators_per_bit=True,original_baseline_unchanged_guard=True,unknown_allocations_never_credited=True,returned_overlay_retained_on_proof_failure=True,original_cma15_whitelist_unchanged=True,files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in paths],board_executed=False,configuration_credits_granted=0,performance_pass=False,promoted=False)
    atomic(out,w.encoded(result),immutable=True);d=w.sha(out);w.atomic=atomic
    w.sync('latest_m443_performance_ledger_support01',dict(status=result['status'],result=out.relative_to(w.ROOT).as_posix(),sha256=d),
           '## M443独立驻留配置记账组件01（2026-10-11）\n\nSHA '+d+'；旧M441原validator保持，新M443仅精确申请原proof+每次同PID/PFN1904页实际trace验证路径，'+str(len(mutations))+'明确破坏负例/原累计baseline改变和额外未知申请拒绝、返回Overlay在proof失败时保留对象；离线组件无配置记账资格或板端性能。原CMA15白名单未改，新trace仅独立instance。须先文本与视频实际PASS及性能全支持冻结后才完整请求运行。')
    print(result['status'],d,len(mutations))


if __name__=='__main__':main()
