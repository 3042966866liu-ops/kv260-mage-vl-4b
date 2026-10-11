"""Finite continuation of already running offline gates into a fresh shell.
Default disabled. No board commands, restarts, repeated samples, or process kill.
"""
import argparse,json,subprocess,time,os
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_supervisor04 import boot,process,classify,log_snapshot
from m441_boundary_control07 import synchronized

PY='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
PS='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
PREVIOUS=BASE/'runs/M441-boundary-core-continuation-07'
RUN=BASE/'runs/M441-shell-continuation-07'
PREP=RUN/'PREPARATION.json'
NAMES=['m441_continue_shell07.py','m441_prepare_shell07.py','m441_prepare_shell_support07.py',
       'm441_record_hwh07.py','m441_aux_readback07.py','m441_collect_shell07.py',
       'm439_prepare_shell.py','m357_prepare_shell.py','m357_build_shell.tcl',
       'm357_run_shell.ps1','m357_collect_shell.py','m441_supervisor04.py']

def prepare():
    assert not PREP.exists()
    start=json.loads((PREVIOUS/'START.json').read_bytes())
    owner=process(start['pid']);assert owner['status']=='ALIVE'
    previous=PREVIOUS/'PREPARATION.json'
    synchronized(previous,'PREPARED_M441_FINITE_BOUNDARY_CORE07','latest_m441_boundary_core_continuation07')
    p=dict(status='PREPARED_M441_FINITE_SHELL07',owner=owner,start_boot=boot(),
      previous_preparation_sha256=sha(previous),files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in NAMES],
      maximum_wall_s=23*3600,shell_budget_s=8*3600,board=False,no_restart=True,no_kill=True)
    atomic(PREP,encoded(p),immutable=True)
    sync('latest_m441_shell_continuation07',dict(status=p['status'],sha256=sha(PREP),result=PREP.relative_to(ROOT).as_posix(),board=False),
         f'## M441 有限整壳续行07准备（2026-10-09）\n\nSHA {sha(PREP)}；等待已启动压力/超时/核心续行，完整PASS且三记录同步后才准备独立Build0x4D343431整壳。同板级拓扑/约束，最多一次整壳8h；超时保留工具及映射，不kill或重复实现。实际HWH全树及启动错误产物独立核查，未知错误拒绝。0板端/性能/晋级。')
    print(p['status'],sha(PREP),flush=True)

def run():
    p=synchronized(PREP,'PREPARED_M441_FINITE_SHELL07','latest_m441_shell_continuation07')
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert sha(PREVIOUS/'PREPARATION.json')==p['previous_preparation_sha256']
    assert not (RUN/'START.json').exists() and not (RUN/'RESULT.json').exists(),'Existing continuation: inspect only'
    atomic(RUN/'START.json',encoded(dict(pid=os.getpid(),boot=boot(),preparation_sha256=sha(PREP))),immutable=True)
    started=time.monotonic();stage='waiting_existing_core';jobs=[];errors=[]
    def state(**kw):atomic(RUN/'PROGRESS.json',encoded(dict(stage=stage,elapsed_s=time.monotonic()-started,jobs=jobs,**kw)))
    def invoke(script,args,budget,expected=0):
        nonlocal stage
        stage=script;log=RUN/(str(len(jobs))+'_'+script+'.log');state()
        if script.endswith('.ps1'):cmd=[PS,'-NoLogo','-NoProfile','-File',str(HERE/script),*args]
        else:cmd=[PY,'-B','-X','utf8',str(HERE/script),*args]
        with log.open('xb') as stream:
            child=subprocess.Popen(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            born=process(child.pid).get('creation_FILETIME');initial=boot();at=time.monotonic()
            while child.poll() is None:
                state(process=process(child.pid,born),classification=classify(initial,boot(),process(child.pid,born)),log=log_snapshot(log))
                if time.monotonic()-at>budget:
                    raise RuntimeError(f'{script}: wall budget exceeded; retained process {child.pid}, no downstream/mapping cleanup')
                time.sleep(5)
        jobs.append(dict(script=script,args=args,original_rc=child.returncode,expected_rc=expected,log=log.relative_to(ROOT).as_posix(),sha256=sha(log)));state()
        return child.returncode==expected
    try:
        previous_result=PREVIOUS/'RESULT.json'
        while not previous_result.exists():
            native=process(p['owner']['pid'],p['owner']['creation_FILETIME'])
            classification=classify(p['start_boot'],boot(),native)
            state(owner=native,classification=classification,previous_progress=json.loads((PREVIOUS/'PROGRESS.json').read_bytes()))
            if classification!='RUNNING_IDENTITY_CONFIRMED':
                time.sleep(5)
                if not previous_result.exists():raise RuntimeError('Previous owner ended without final evidence: '+classification)
            if time.monotonic()-started>13*3600+90:raise RuntimeError('Previous finite controller budget reached; retained, no shell')
            time.sleep(5)
        synchronized(previous_result,'PASS_M441_BOUNDARY_TIMEOUT_CORE07','latest_m441_boundary_core_result07')
        assert invoke('m441_prepare_shell07.py',[],600),'Shell preparer rejected'
        controls=BASE/'runs/M441-shell-control-preparation-07/RESULT.json'
        c=synchronized(controls,'PREPARED_M441_FROZEN_SHELL_CONTROLS','latest_m441_shell_control_preparation07')
        assert sha(HERE/'m441_build_shell.tcl')==c['Tcl_sha256'] and sha(HERE/'m441_run_shell.ps1')==c['controller_sha256']
        shell_ok=invoke('m441_run_shell.ps1',['-Run'],p['shell_budget_s'])
        assert (ROOT/'tmp/m441_shell_exit.json').exists(),'Missing original Vivado receipt'
        assert shell_ok,'Shell tool failed; preserve original receipt/log, do not retry'
        assert invoke('m441_record_hwh07.py',[],600),'HWH ABI rejected'
        assert invoke('m441_aux_readback07.py',['prepare'],600),'Auxiliary input classification rejected'
        readback_ok=invoke('m441_aux_readback07.py',['run','--run'],650)
        closed=invoke('m441_aux_readback07.py',['collect'],600)
        assert readback_ok and closed,'Auxiliary readback rejected'
        assert invoke('m441_collect_shell07.py',[],600),'Shell collector rejected'
        stage='complete_shell_board_pending'
    except Exception as exc:errors.append(repr(exc))
    r=dict(status='PASS_M441_FINITE_SHELL07' if not errors else 'STOP_M441_SHELL07_AT_FAILED_LEVEL',errors=errors,
      last_stage=stage,jobs=jobs,preparation_sha256=sha(PREP),elapsed_s=time.monotonic()-started,board=False,performance=False,promotion=False,no_kill=True)
    evidence=RUN/'RESULT.json';atomic(evidence,encoded(r),immutable=True)
    sync('latest_m441_shell_result07',dict(status=r['status'],sha256=sha(evidence),result=evidence.relative_to(ROOT).as_posix(),board=False),
      f'## M441 有限整壳续行07末态（2026-10-09）\n\nSHA {sha(evidence)}；{r["status"]}，末级{stage}，错误{errors}。保存原返回值和日志SHA，三记录同步。未加载板端，不证明真实长链或请求收益。'+('下一步准备原固定Build/descriptor/W4链板端门禁，不跳级。' if not errors else '停止扩大，仅处理失败当前级；保留前级通过证据。'))
    print(r['status'],sha(evidence),errors,flush=True)
    return 1 if errors else 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Prepare','Run']);ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Prepare':prepare()
    else:assert a.enable,'Default disabled';raise SystemExit(run())
