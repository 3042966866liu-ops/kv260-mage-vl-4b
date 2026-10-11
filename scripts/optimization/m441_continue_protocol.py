"""One finite offline continuation: waits for original RTL job, never board."""
import argparse
import ast
import json
import os
import subprocess
import sys
import time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

RUN=BASE/'runs/M441-protocol-continuation-01'
PREP=RUN/'PREPARATION.json'
FINAL=RUN/'RESULT.json'
FULL=BASE/'runs/M441-offline-continuation-01/RESULT.json'

def decision(status):
    return status=='PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON'

def prepare():
    assert not RUN.exists()
    assert all(decision(s)==v for s,v in [('PASS_M441_COMPLETE_LONG_CHAIN_RTL_COMPARISON',True),('STOP_M441_OFFLINE_CONTINUATION',False),('PASS',False),('',False)])
    RUN.mkdir(parents=True)
    tests=[]
    out=ROOT/'tmp/m441_record_pipeline_02'
    before={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    for label,args,expected,marker in [('core_check',['Check'],0,'BLOCKED_BEFORE_TOOL'),
                                     ('core_disabled',['Run'],1,'Default disabled: --enable required'),
                                     ('core_missing_full',['Run','--enable'],1,'Missing prerequisite:')]:
        p=subprocess.run([sys.executable,'-B',str(HERE/'m441_core_ooc.py'),*args],capture_output=True)
        atomic(RUN/(label+'.stdout.txt'),p.stdout,immutable=True);atomic(RUN/(label+'.stderr.txt'),p.stderr,immutable=True)
        tests.append(dict(name=label,original_rc=p.returncode,pass_gate=p.returncode==expected and marker in (p.stdout+p.stderr).decode('utf-8-sig')))
    assert all(x['pass_gate'] for x in tests)
    assert before=={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    assert not (out/'core_ooc_console.log').exists()
    names=('m441_continue_protocol.py','m441_core_ooc.py','m441_collect_core_ooc.py',
           'm441_protocol_control.py','m441_collect_max_protocol.py','m441_protocol_evidence.py',
           'm357_uvm_log_evidence.py','m351_workflow.py')
    files=[]
    for name in names:
        p=HERE/name;ast.parse(p.read_text(encoding='utf-8-sig'),feature_version=(3,10))
        files.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    refs=[]
    for name in ('M441-offline-continuation-01/PREPARATION.json','M441-record-pipeline-core-OOC-preparation-01/RESULT.json',
                 'M441-protocol-control-preparation-01/RESULT.json','M441-max-protocol-preparation-01/RESULT.json'):
        p=BASE/'runs'/name;r=json.loads(p.read_bytes());assert r['status'].startswith('PREPARED_')
        refs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    proof=dict(status='PREPARED_M441_FINITE_PROTOCOL_CONTINUATION',files=files,refs=refs,
        decision_negative_cases=3,actual_core_guards=tests,source_inputs_unchanged=True,
        wait_budget_s=72*3600,child_budget_s=12*3600,process_kill_allowed=False,
        stages=['existing_full_RTL_result','same_constraint_core_OOC','maximum_compile','maximum_backpressure','expected_timeout'],
        recurring_automation=False,board=False,full_shell=False,performance=False,promoted=False)
    atomic(PREP,encoded(proof),immutable=True)
    sync('latest_m441_protocol_continuation_preparation',dict(status=proof['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),
         f'## M441 有限后续离线控制准备（2026-10-07）\n\nSHA {sha(PREP)}；真实核心控制默认关闭/缺失前级均拒绝且源输入未变。已有完整RTL结果成功才进入同约束核OOC，严格收集同步后再最大FIFO/背压/timeout。失败/预算到期保存停止，不重跑、不kill，不整壳/上板/温度，非循环自动任务。')
    print(proof['status'],sha(PREP),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('Prepare','Run'));ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Prepare':prepare();return
    assert a.enable and not FINAL.exists() and not (RUN/'START.json').exists(),'Default disabled or existing run: read/collect only'
    p=json.loads(PREP.read_bytes())
    def frozen():
        for row in p['files']+p['refs']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
    frozen()
    from m441_protocol_control import synchronized
    synchronized(PREP,'PREPARED_M441_FINITE_PROTOCOL_CONTINUATION','latest_m441_protocol_continuation_preparation')
    started=time.time();events=[]
    atomic(RUN/'START.json',encoded(dict(pid=os.getpid(),epoch=started,preparation_sha256=sha(PREP))),immutable=True)
    def event(stage,**data):
        row=dict(epoch=time.time(),stage=stage,**data);events.append(row);atomic(RUN/'PROGRESS.json',encoded(events));print(json.dumps(row),flush=True)
    def call(tag,script,args):
        frozen();log=RUN/(tag+'.log');assert not log.exists()
        with log.open('xb') as f:
            child=subprocess.Popen([sys.executable,'-B',str(HERE/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            event(tag,status='RUNNING',pid=child.pid);deadline=time.monotonic()+p['child_budget_s']
            while child.poll() is None:
                if time.monotonic()>deadline:raise TimeoutError(f'{tag} budget expired; retain child pid {child.pid}, no kill')
                time.sleep(5)
        atomic(RUN/(tag+'_exit.json'),encoded(dict(original_rc=child.returncode)),immutable=True)
        event(tag,status='RETURNED',original_rc=child.returncode)
        return child.returncode
    errors=[]
    try:
        event('existing_full_RTL_result',status='WAITING_NO_NEW_TOOL')
        deadline=time.monotonic()+p['wait_budget_s']
        while not FULL.exists():
            frozen()
            if time.monotonic()>deadline:raise TimeoutError('Existing RTL result wait expired; retain all original jobs')
            time.sleep(15)
        r=json.loads(FULL.read_bytes())
        assert decision(r['status']),r['status']
        synchronized(FULL,r['status'],'latest_m441_offline_continuation_result')
        tool_rc=call('core_OOC','m441_core_ooc.py',['Run','--enable'])
        assert (ROOT/'tmp/m441_record_pipeline_02/core_ooc_exit.json').exists(),'No saved core tool receipt; stop, no rerun'
        collect_rc=call('collect_core_OOC','m441_collect_core_ooc.py',[])
        assert tool_rc==collect_rc==0,'Core tool/collector failed; stop at saved evidence'
        for mode in ('compile','max','timeout'):
            tool_rc=call('protocol_'+mode,'m441_protocol_control.py',[mode,'--run'])
            # Expected watchdog failure returns gate_rc=1; collect original
            # result before judging it. No failed stage is restarted here.
            collect_rc=call('collect_'+mode,'m441_collect_max_protocol.py',[mode])
            assert collect_rc==0 and tool_rc==(1 if mode=='timeout' else 0),'Protocol gate failed; stop at saved evidence'
        status='PASS_M441_OFFLINE_CORE_AND_MAXIMUM_PROTOCOL'
    except Exception as exc:
        errors.append(repr(exc));status='STOP_M441_PROTOCOL_CONTINUATION'
    result=dict(status=status,errors=errors,events=events,elapsed_s=time.time()-started,preparation_sha256=sha(PREP),
        board=False,full_shell=False,performance=False,promoted=False,processes_killed=False,
        next='Review all saved offline gates before separately preparing full shell; no board automatically unlocked.' if not errors else 'Read the saved failed stage; no rerun or larger gate.')
    atomic(FINAL,encoded(result),immutable=True)
    report='# M441 有限离线后续控制\n\n'+status+'\n\n'+repr(errors)+'\n\n'+result['next']+'\n'
    atomic(RUN/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_protocol_continuation_result',dict(status=status,result=FINAL.relative_to(ROOT).as_posix(),sha256=sha(FINAL),board=False),
         f'## M441 有限后续离线控制闭合（2026-10-07）\n\nSHA {sha(FINAL)}；{status}。原退出码、各级收集同步保留，0进程kill/整壳/上板；非实测请求提速。下一步 {result["next"]}')
    print(status,sha(FINAL),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
