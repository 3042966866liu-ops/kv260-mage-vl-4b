"""Finite authorized continuation: existing pressure owner -> timeout -> core.
No board, full shell, rerun, restart, kill, or changes to DUT/constraints.
"""
import argparse,json,subprocess,time,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_supervisor04 import boot,process,classify,log_snapshot
from m441_boundary_control07 import synchronized,OUT,require_validation
PY='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
RUN=BASE/'runs/M441-boundary-core-continuation-07'
PREP=RUN/'PREPARATION.json'

def prepare():
    assert not PREP.exists()
    live=json.loads((OUT/'verilog/max_LIVE.json').read_bytes());owner=live['process']
    assert owner['status']=='ALIVE' and process(owner['pid'],owner['creation_FILETIME'])['status']=='ALIVE'
    refs={}
    for key in ['latest_m441_boundary_control07','latest_m441_core_admission07','latest_m441_boundary07_compile']:
        b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())[key]
        synchronized(ROOT/b['result'],b['status'],key);refs[key]=b['sha256']
    names=['m441_continue_boundary_core07.py','m441_boundary_control07.py','m441_collect_boundary07.py','m441_core_ooc07.py','m441_collect_core_ooc07.py','m441_supervisor04.py','m441_boundary_evidence06.py']
    r=dict(status='PREPARED_M441_FINITE_BOUNDARY_CORE07',owner=owner,start_boot=boot(),refs=refs,
        files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in names],
        maximum_wall_s=13*3600,board=False,full_shell=False,no_restart=True,no_kill=True)
    atomic(PREP,encoded(r),immutable=True)
    sync('latest_m441_boundary_core_continuation07',dict(status=r['status'],sha256=sha(PREP),result=PREP.relative_to(ROOT).as_posix(),board=False),
         f'## M441 有限压力至核实现续行07（2026-10-09）\n\nSHA {sha(PREP)}；绑定已启动压力进程/PID出生时间，原压力只等待和收集；PASS后三记录闭合同快照timeout，再同约束核心实现。最多13h，无重启/重跑/kill/整壳/板端；失败停当前级保存末态。')
    print(r['status'],sha(PREP),flush=True)

def run():
    p=synchronized(PREP,'PREPARED_M441_FINITE_BOUNDARY_CORE07','latest_m441_boundary_core_continuation07')
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (RUN/'START.json').exists() and not (RUN/'RESULT.json').exists(),'Existing continuation, collect only'
    atomic(RUN/'START.json',encoded(dict(preparation_sha256=sha(PREP),pid=__import__('os').getpid(),boot=boot())),immutable=True)
    jobs=[];errors=[];started=time.monotonic();stage='existing_pressure';owner=p['owner']
    def state(**kw):atomic(RUN/'PROGRESS.json',encoded(dict(stage=stage,elapsed_s=time.monotonic()-started,jobs=jobs,**kw)))
    def invoke(script,args,expected=0):
        nonlocal stage
        stage=script+' '+','.join(args);log=RUN/(str(len(jobs))+'_'+script+'.log');state()
        with log.open('xb') as stream:
            child=subprocess.Popen([PY,'-B','-X','utf8',str(HERE/script),*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            born=process(child.pid).get('creation_FILETIME');initial=boot()
            while child.poll() is None:
                state(process=process(child.pid,born),boot=boot(),log=log_snapshot(log))
                if time.monotonic()-started>p['maximum_wall_s']:raise RuntimeError('Continuation wall budget; child retained '+str(child.pid))
                time.sleep(5)
        jobs.append(dict(script=script,args=args,original_rc=child.returncode,expected_rc=expected,log=log.relative_to(ROOT).as_posix(),sha256=sha(log)))
        state();return child.returncode==expected
    try:
        while True:
            receipt=OUT/'verilog/max_exit.json';native=process(owner['pid'],owner['creation_FILETIME'])
            classification=classify(p['start_boot'],boot(),native)
            state(owner=native,classification=classification,log=log_snapshot(OUT/'verilog/max.log'))
            if receipt.exists() and classification in ('PROCESS_RETURNED','INTERRUPTED_PROCESS_MISSING'):
                # Controller writes receipt before copying TV; await its final saved directory.
                if (OUT/'verilog/max_result').exists():break
            if classification not in ('RUNNING_IDENTITY_CONFIRMED','PROCESS_RETURNED','INTERRUPTED_PROCESS_MISSING'):
                raise RuntimeError(classification)
            if classification!='RUNNING_IDENTITY_CONFIRMED' and not receipt.exists():
                time.sleep(5)
                if not receipt.exists():raise RuntimeError('Owner ended without saved receipt')
            if time.monotonic()-started>4*3600+90:raise RuntimeError('Existing pressure wall budget, retained no restart')
            time.sleep(5)
        assert invoke('m441_collect_boundary07.py',['max']),'Pressure collector rejected'
        require_validation('max')
        # Gate rc1 is mandatory for this one expected failure; collect original regardless.
        ok=invoke('m441_boundary_control07.py',['timeout','--run'],1)
        closed=invoke('m441_collect_boundary07.py',['timeout'])
        assert ok and closed,'Expected timeout closure failed'
        import m441_core_ooc07
        m441_core_ooc07.ready()
        tool_ok=invoke('m441_core_ooc07.py',['Run','--enable'])
        core_closed=invoke('m441_collect_core_ooc07.py',[])
        assert tool_ok and core_closed,'Core implementation rejected'
        stage='complete_core_no_shell'
    except Exception as exc:errors.append(repr(exc))
    r=dict(status='PASS_M441_BOUNDARY_TIMEOUT_CORE07' if not errors else 'STOP_M441_BOUNDARY_CORE07_AT_FAILED_LEVEL',
        errors=errors,last_stage=stage,jobs=jobs,preparation_sha256=sha(PREP),board=False,full_shell=False,performance=False,no_kill=True,elapsed_s=time.monotonic()-started)
    ev=RUN/'RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_boundary_core_result07',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
         f'## M441 有限压力/timeout/核心续行07末态（2026-10-09）\n\nSHA {sha(ev)}；{r["status"]}，末级{stage}，错误{errors}；原子保存三记录，0整壳/板端/性能，失败只调试当前级，不重跑前级。')
    print(r['status'],sha(ev),errors,flush=True)
    return 1 if errors else 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Prepare','Run']);ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Prepare':prepare()
    else:assert a.enable,'Default disabled';sys.exit(run())
