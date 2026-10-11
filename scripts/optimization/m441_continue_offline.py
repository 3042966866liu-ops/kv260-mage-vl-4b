"""One-shot continuation of the frozen M441 RTL level; never board or rerun.

The existing gate_up Zero controllers are owned by PID plus exact creation
FILETIME. Future tools use the already reviewed controller and immutable inputs.
This is an ordinary finite local job, not a recurring automation.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

PY=Path('C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
PS=PY.parents[1]/'native/powershell/pwsh.exe'
HERE=ROOT/'scripts/optimization'
RUN=BASE/'runs/M441-offline-continuation-01'
PREP=RUN/'PREPARATION.json'
FAMILIES=('gate_up','mlp_down','q')
FINAL=RUN/'RESULT.json'
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
kernel.OpenProcess.restype=wintypes.HANDLE
kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
kernel.GetProcessTimes.restype=wintypes.BOOL
kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
kernel.GetExitCodeProcess.restype=wintypes.BOOL
kernel.CloseHandle.argtypes=[wintypes.HANDLE]
kernel.CloseHandle.restype=wintypes.BOOL


def opened(pid,expected=None):
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return None,None
        raise ctypes.WinError(ctypes.get_last_error())
    values=[wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle,*[ctypes.byref(v) for v in values]):
        error=ctypes.get_last_error();kernel.CloseHandle(handle);raise ctypes.WinError(error)
    born=(values[0].dwHighDateTime<<32)|values[0].dwLowDateTime
    if expected is not None and born!=expected:
        kernel.CloseHandle(handle);raise RuntimeError('PID reused; no process operation permitted')
    return handle,born


def exit_code(handle):
    code=wintypes.DWORD()
    if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
    return code.value


def decision(a,b,mode):
    if any(r.get('status')!='PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL' for r in (a,b)):
        return False,'Incomplete numerical/protocol evidence'
    ac=a.get('done',{}).get('cycles');bc=b.get('done',{}).get('cycles')
    if type(ac) is not int or type(bc) is not int or min(ac,bc)<=0:
        return False,'Missing valid full transaction cycles'
    if mode=='zero':return (bc<=ac,'Zero cycle regression' if bc>ac else 'No Zero regression')
    return (bc<ac,'No Random cycle improvement' if bc>=ac else 'Random cycle improvement')


def selftest():
    def r(n):return dict(status='PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL',done=dict(cycles=n))
    cases=[(r(100),r(99),'zero',True),(r(100),r(100),'zero',True),
           (r(100),r(101),'zero',False),(r(100),r(99),'random',True),
           (r(100),r(100),'random',False),(r(100),r(101),'random',False),
           (r(100),dict(status='FAIL'),'zero',False),(r(100),r(0),'zero',False),
           (r(100),dict(status='PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL'),'random',False)]
    for a,b,mode,expected in cases:assert decision(a,b,mode)[0] is expected
    assert PY.is_file() and PS.is_file()
    proof=dict(status='PASS_M441_OFFLINE_CONTINUATION_PREDICATE',checks=len(cases),
               source_sha256=sha(Path(__file__)),scope='Decision and fixed runtime paths only; no tool launch, no RTL proof')
    atomic(RUN/'SELFTEST02.json',encoded(proof),immutable=True)
    print(proof['status'],len(cases),flush=True)


def prepare():
    assert not PREP.exists() and not FINAL.exists()
    test=RUN/'SELFTEST02.json';t=json.loads(test.read_bytes())
    assert t['source_sha256']==sha(Path(__file__)) and t['checks']==9
    refs=[]
    for name in ('m441_continue_offline.py','m441_run_long_rtl02.ps1','m441_prepare_long_rtl.py',
                 'm441_collect_long_rtl.py','m351_workflow.py','m438_prepare.py','m439_prepare_rtl.py',
                 'm356_collect_rtl.py','m357_uvm_log_evidence.py'):
        p=HERE/name;refs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    owners=[]
    for variant,pid in (('B',21472),('A',17752)):
        handle,born=opened(pid);assert handle is not None
        try:assert exit_code(handle)==259
        finally:kernel.CloseHandle(handle)
        sim=ROOT/f'tmp/m441_long_{variant}_gate_up_02/verilog'
        assert (sim/'zero.args').is_file() and not (sim/'zero_exit.json').exists()
        compiled=BASE/f'runs/M441-long-{variant}-gate_up-compile-02/RESULT.json'
        assert json.loads(compiled.read_bytes())['status']=='PASS_M441_COMPLETE_RTL_COMPILED'
        owners.append(dict(variant=variant,pid=pid,creation_FILETIME=born,
                           compiled_sha256=sha(compiled),args_sha256=sha(sim/'zero.args')))
    plan=ROOT/'tmp/m441_record_pipeline_01/PLAN.json'
    p=json.loads(plan.read_bytes());assert p['RTL_budget_cycles_per_full_chain']==30000000
    data=dict(status='PREPARED_M441_FINITE_OFFLINE_CONTINUATION',files=refs,owners=owners,
              plan_sha256=sha(plan),families=list(FAMILIES),modes=['zero','random'],
              maximum_supervisor_wall_seconds=72*3600,no_process_kill=True,
              no_recurring_automation=True,board=False,full_shell=False,temperature=False,
              next='Collect existing Zero once; stop on failure/regression; then fixed Random and remaining complete chains, no new samples.')
    atomic(PREP,encoded(data),immutable=True)
    sync('latest_m441_offline_continuation',dict(status=data['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),
         f'## M441 有界离线继续控制准备（2026-10-07）\n\nSHA {sha(PREP)}；当前A/B完整gate_up Zero作业按PID＋创建FILETIME绑定，0新运行。固定三链/Zero＋seed356Random，完成一次严格收集/原判据继续或停；原日志/源与M439 FAIL保持。控制仅本地RTL，72h监督预算到期只保存未完成、不终止进程，不整壳/上板/温度。')
    print(data['status'],sha(PREP),flush=True)


def main():
    mode=sys.argv[1]
    if mode=='SelfTest':selftest();return
    if mode=='Prepare':prepare();return
    assert mode=='Run' and not FINAL.exists() and not (RUN/'START.json').exists()
    p=json.loads(PREP.read_bytes())
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    assert sha(ROOT/'tmp/m441_record_pipeline_01/PLAN.json')==p['plan_sha256']
    for doc in ('CURRENT_STATE.md','docsMILESTONES.md'):assert sha(PREP) in (ROOT/doc).read_text(encoding='utf-8-sig')
    assert json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())['latest_m441_offline_continuation']['sha256']==sha(PREP)
    started=time.time();deadline=time.monotonic()+p['maximum_supervisor_wall_seconds']
    atomic(RUN/'START.json',encoded(dict(started_epoch=started,pid=os.getpid(),preparation_sha256=sha(PREP))),immutable=True)
    events=[];comparisons=[]
    def save(event):
        events.append(dict(epoch=time.time(),**event));atomic(RUN/'PROGRESS.json',encoded(events))
        print(json.dumps(event),flush=True)
    def bound():
        if time.monotonic()>deadline:raise TimeoutError('Supervisor budget: preserve any active processes; do not terminate')
    def call(tag,args,allow_failure=False):
        for frozen in p['files']:assert sha(ROOT/frozen['path'])==frozen['sha256'],frozen['path']
        log=RUN/(tag+'.log');assert not log.exists(),tag
        with log.open('wb') as stream:
            child=subprocess.Popen(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            save(dict(stage=tag,pid=child.pid,status='RUNNING'))
            while child.poll() is None:bound();time.sleep(5)
        atomic(RUN/(tag+'_exit.json'),encoded(dict(original_rc=child.returncode)),immutable=True)
        save(dict(stage=tag,status='RETURNED',original_rc=child.returncode))
        if child.returncode and not allow_failure:raise RuntimeError(f'{tag}: original rc {child.returncode}; preserve logs, no rerun')
    def collect(variant,family,phase,require_pass=True):
        ev=BASE/f'runs/M441-long-{variant}-{family}-{phase}-02/RESULT.json'
        if not ev.exists():call(f'collect_{variant}_{family}_{phase}',[str(PY),'-B',str(HERE/'m441_collect_long_rtl.py'),variant,family,phase,'02'],allow_failure=True)
        result=json.loads(ev.read_bytes())
        for doc in ('CURRENT_STATE.md','docsMILESTONES.md'):assert sha(ev) in (ROOT/doc).read_text(encoding='utf-8-sig')
        key=f'latest_m441_long_{variant}_{family}_{phase}02'
        assert json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())[key]['sha256']==sha(ev)
        if require_pass:assert result['status'].startswith('PASS_M441_'),result['status']
        return result
    def run_tool(variant,family,phase):
        call(f'tool_{variant}_{family}_{phase}',[str(PS),'-NoProfile','-File',str(HERE/'m441_run_long_rtl02.ps1'),
                                               '-Variant',variant,'-Family',family,'-Mode',phase.capitalize()])
    def comparison(family,phase,results):
        ok,reason=decision(results['A'],results['B'],phase)
        ac=(results['A'].get('done') or {}).get('cycles');bc=(results['B'].get('done') or {}).get('cycles')
        reduction=(ac-bc)*100/ac if type(ac) is int and type(bc) is int and ac>0 else None
        row=dict(family=family,mode=phase,A_cycles=ac,B_cycles=bc,cycle_reduction_pct=reduction,pass_gate=ok,reason=reason)
        comparisons.append(row);save(dict(stage='comparison',**row))
        if not ok:raise RuntimeError(f'{family}/{phase}: {reason}; close frozen RTL benefit gate, no extra run')
    try:
        handles=[];original_controller_codes=[]
        try:
            for owner in p['owners']:
                sim=ROOT/f"tmp/m441_long_{owner['variant']}_gate_up_02/verilog"
                assert sha(sim/'zero.args')==owner['args_sha256']
                assert sha(BASE/f"runs/M441-long-{owner['variant']}-gate_up-compile-02/RESULT.json")==owner['compiled_sha256']
                handle,_=opened(owner['pid'],owner['creation_FILETIME'])
                if handle is None:
                    assert (sim/'zero_exit.json').is_file() and (sim/'zero_result').is_dir(),'Original controller disappeared without saved result'
                else:handles.append((owner,handle))
            save(dict(stage='existing_gate_up_zero',status='WAITING_SAVED_ORIGINAL_CONTROLLERS'))
            while any(exit_code(h)==259 for _,h in handles):bound();time.sleep(5)
            for owner,h in handles:
                rc=exit_code(h);original_controller_codes.append(rc)
                save(dict(stage='original_controller_return',variant=owner['variant'],original_controller_rc=rc))
        finally:
            for _,h in handles:kernel.CloseHandle(h)
        initial={v:collect(v,'gate_up','zero',require_pass=False) for v in ('A','B')}
        assert not any(original_controller_codes),'Original controller failed; results collected, stop before later tools'
        comparison('gate_up','zero',initial)
        for family in FAMILIES:
            if family!='gate_up':
                for variant in ('A','B'):
                    call(f'prepare_{variant}_{family}',[str(PY),'-B',str(HERE/'m441_prepare_long_rtl.py'),variant,family])
                    run_tool(variant,family,'compile');collect(variant,family,'compile')
                results={}
                for variant in ('A','B'):run_tool(variant,family,'zero');results[variant]=collect(variant,family,'zero')
                comparison(family,'zero',results)
            results={}
            for variant in ('A','B'):run_tool(variant,family,'random');results[variant]=collect(variant,family,'random')
            comparison(family,'random',results)
        final=dict(status='PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON',errors=[])
    except Exception as exc:
        final=dict(status='STOP_M441_OFFLINE_CONTINUATION',errors=[repr(exc)])
    final.update(preparation_sha256=sha(PREP),comparisons=comparisons,events=events,elapsed_wall_s=time.time()-started,
                 board=False,full_shell=False,full_model=False,performance=False,promoted=False,processes_killed=False,
                 next='Read original RTL results and cycle comparison; maximum occupancy/backpressure/timeout still required before implementation.' if not final['errors'] else 'Read saved failure at this level; no tool restart, extra sample or board work.')
    atomic(FINAL,encoded(final),immutable=True)
    report='# M441 完整长链RTL离线裁决\n\n'+final['status']+'\n\n仅RTL模型周期，非实板DDR或完整请求收益。\n\n'
    for row in comparisons:
        reduction='未记录' if row['cycle_reduction_pct'] is None else f"{row['cycle_reduction_pct']:.6f}%"
        report+=f"- {row['family']}/{row['mode']}: A {row['A_cycles']} / B {row['B_cycles']} cycles，{reduction}，{row['reason']}。\n"
    report+='\n错误/停止原因：'+repr(final['errors'])+'\n\n'+final['next']+'\n'
    atomic(RUN/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_offline_continuation_result',dict(status=final['status'],result=FINAL.relative_to(ROOT).as_posix(),sha256=sha(FINAL),board=False),
         f"## M441 有界离线继续控制闭合（2026-10-07）\n\nSHA {sha(FINAL)}；{final['status']}，{len(comparisons)}项完整链周期裁决。全部原rc/日志保留，仅RTL、0上板/整壳/完整请求新收益；失败停本级不补测/重跑。下一步 {final['next']}")
    print(final['status'],sha(FINAL),flush=True)
    if final['errors']:raise SystemExit(1)


if __name__=='__main__':main()
