"""Only missing W4 numerical Zero pair; bounded, observed, no pressure/board."""
import argparse
import json
import os
import subprocess
import sys
import time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_supervisor04 import boot,process,classify,log_snapshot,selftest

RUN=BASE/'runs/M441-independent-protocol-04'
WORK=BASE/'runs/M441-W4-zero-continuation-05'
PY='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
PS='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'

POLICY=BASE/'runs/M441-W4-compile-recovery-05/RESULT.json'

def verified():
    policy=json.loads(POLICY.read_bytes())
    for f in policy['new_files']:assert sha(ROOT/f['path'])==f['sha256']
    prep=RUN/'PREPARATION.json';p=json.loads(prep.read_bytes())
    assert p['status']=='PREPARED_M441_SEPARATE_NUMERIC_BOUNDARY_BOARD_PROTOCOL04'
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert b['latest_m441_independent_protocol04']['sha256']==sha(prep)
    assert all(sha(prep) in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    for f in p['files']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
    return p

def synced(path):
    d=sha(path);b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert any(isinstance(v,dict) and v.get('sha256')==d for v in b.values())
    assert all(d in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    return json.loads(path.read_bytes())

def run():
    p=verified();assert not WORK.exists(),'Existing run: Reconcile/read only, never restart'
    started=time.time();started_boot=boot();own=process(os.getpid());assert own['status']=='ALIVE'
    atomic(WORK/'START.json',encoded(dict(epoch=started,host=started_boot,supervisor=own,preparation_sha256=sha(RUN/'PREPARATION.json'))),immutable=True)
    jobs=[];events=[];held=[]
    def save(stage,status,**more):
        events.append(dict(epoch=time.time(),stage=stage,status=status,**more));atomic(WORK/'PROGRESS.json',encoded(events));print(stage,status,flush=True)
    def observe():
        state=dict(epoch=time.time(),host=boot(),supervisor=process(own['pid'],own['creation_FILETIME']),jobs=[])
        for job in jobs:
            identity=process(job['pid'],job['creation_FILETIME'])
            state['jobs'].append(dict(stage=job['stage'],pid=job['pid'],identity=identity,
                observed_status=classify(started_boot,state['host'],identity),
                native=log_snapshot(ROOT/job['native_log']) if job.get('native_log') else None))
        atomic(WORK/'LIVE.json',encoded(state));return state
    def launch(stage,args,native=None):
        verified();log=WORK/(stage+'.log');assert not log.exists()
        stream=log.open('xb')
        try:child=subprocess.Popen(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        finally:stream.close()
        ident=process(child.pid);assert ident['status']=='ALIVE'
        job=dict(stage=stage,pid=child.pid,creation_FILETIME=ident['creation_FILETIME'],epoch=time.time(),native_log=native)
        jobs.append(job);save(stage,'RUNNING',owner=job);observe();return child,job
    def wait(child,job):
        last=0
        while child.poll() is None:
            if time.time()-last>=30:observe();last=time.time()
            if time.time()-job['epoch']>p['child_wall_budget_s']:
                held.append(job);save(job['stage'],'WALL_BUDGET_PROCESS_RETAINED',owner=job);observe()
                raise TimeoutError('No kill/free/restart; inspect retained owner')
            time.sleep(2)
        receipt=dict(original_rc=child.returncode,epoch=time.time(),owner=job,host=boot(),failure_native=log_snapshot(ROOT/job['native_log']) if job.get('native_log') else None)
        atomic(WORK/(job['stage']+'_exit.json'),encoded(receipt),immutable=True)
        save(job['stage'],'RETURNED',original_rc=child.returncode);observe();return child.returncode
    def call(stage,args,native=None):
        child,job=launch(stage,args,native);return wait(child,job)
    def collect(v,mode):
        rc=call('collect_'+v+'_'+mode,[PY,'-B',str(HERE/'m441_collect_long_rtl05.py'),v,'mlp_down',mode,'05'])
        ev=BASE/f'runs/M441-long-{v}-mlp_down-{mode}-05/RESULT.json'
        if not ev.exists():raise RuntimeError('Collection failed; inspect original saved bytes only, rc='+str(rc))
        r=synced(ev);assert rc==0 and r['status'].startswith('PASS_'),r['status'];return r
    try:
        for v in ('A','B'):
            assert call('prepare_'+v,[PY,'-B',str(HERE/'m441_prepare_long_rtl05.py'),v,'mlp_down'])==0
            prep=BASE/f'runs/M441-long-{v}-mlp_down-RTL-preparation-05/RESULT.json';r=synced(prep)
            assert r['cycle_budget']==12000000 and r['observer_revision']=='05'
            monitor=ROOT/f'tmp/m441_long_{v}_mlp_down_05/verilog/m441_monitor.sv'
            assert 'cyc>12000000' in monitor.read_text(encoding='utf-8-sig') and 'cyc>80000000' not in monitor.read_text(encoding='utf-8-sig')
            native=f'tmp/m441_long_{v}_mlp_down_05/verilog/compile_console.log'
            rc=call('compile_'+v,[PS,'-NoProfile','-File',str(HERE/'m441_run_long_rtl05.ps1'),'-Variant',v,'-Family','mlp_down','-Mode','Compile','-Enable'],native)
            collect(v,'compile');assert rc==0
        live=[]
        for v in ('A','B'):
            child,job=launch('zero_'+v,[PS,'-NoProfile','-File',str(HERE/'m441_run_long_rtl05.ps1'),'-Variant',v,'-Family','mlp_down','-Mode','Zero','-Enable'],f'tmp/m441_long_{v}_mlp_down_05/verilog/zero.log')
            live.append((v,child,job))
        started_proof=WORK/'RUNNING.json'
        atomic(started_proof,encoded(dict(status='RUNNING_M441_MLPDOWN_ZERO04_ONLY',jobs=[x[2] for x in live],host=boot(),board=False,pressure_started=False)),immutable=True)
        sync('latest_m441_W4_zero05_running',dict(status='RUNNING_M441_MLPDOWN_ZERO04_ONLY',sha256=sha(started_proof),result=started_proof.relative_to(ROOT).as_posix(),board=False),
            '## M441 W4 mlp_down完整Zero04实际启动（2026-10-08）\n\nSHA '+sha(started_proof)+'；A/B同输入与冻结DUT，各一次完整长链，两个身份已绑定；仅数值及正常协议，固定12M/8h，每30s原子保存进度/主机启动/PID身份/失败末段。gate_up Zero复用，0压力/时序/整壳/上板。完成后严格回收同步；失败不kill、不重跑。')
        answers={}
        for v,child,job in live:
            rc=wait(child,job)
            # Always collect saved failure; never repeat hardware/tool to repair collection.
            answers[v]=collect(v,'zero');assert rc==0
        a,b=answers['A']['done']['cycles'],answers['B']['done']['cycles']
        final=dict(status='PASS_M441_W4_MLPDOWN_FULL_ZERO04' if b<=a else 'STOP_M441_W4_MLPDOWN_ZERO04_CYCLE_REGRESSION',
            errors=[] if b<=a else ['No extra sample after cycle regression'],A_cycles=a,B_cycles=b,
            cycle_reduction_pct=100*(a-b)/a,
            complete_numerical_pair=all(x['status']=='PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL' for x in answers.values()))
    except Exception as exc:
        final=dict(status='STOP_M441_W4_ZERO04_AT_FAILED_LEVEL',errors=[repr(exc)])
    final.update(preparation_sha256=sha(RUN/'PREPARATION.json'),elapsed_s=time.time()-started,
        board=False,pressure_started=False,OOC_started=False,shell_started=False,processes_killed=False,
        retained_process_owners=held,last_live_sha256=sha(WORK/'LIVE.json') if (WORK/'LIVE.json').exists() else None,
        next='Read full W4 result; implement and validate the separately frozen bounded-boundary fixture before any later tool.')
    ev=WORK/'RESULT.json';atomic(ev,encoded(final),immutable=True)
    sync('latest_m441_W4_zero05_result',dict(status=final['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
        '## M441 W4 Zero04有限阶段闭合（2026-10-08）\n\nSHA '+sha(ev)+'；'+final['status']+'；原rc/进度/失败末态保留，0压力/OOC/整壳/板端/kill。完整输出证据逐项同步，不能解释成六组Random或板端提速；下一步按独立04协议核对本级结果。')
    print(final['status'],sha(ev),flush=True)
    if final['errors']:raise SystemExit(1)

def reconcile():
    start=json.loads((WORK/'START.json').read_bytes());now=boot()
    p=process(start['supervisor']['pid'],start['supervisor']['creation_FILETIME'])
    status=classify(start['host'],now,p)
    r=dict(status=status,host=now,supervisor=p,started_SHA=sha(WORK/'START.json'),board=False,restarted=False)
    atomic(WORK/'RECONCILIATION.json',encoded(r))
    print(json.dumps(r),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Run','Reconcile','SelfTest']);ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='SelfTest':print(json.dumps(selftest()));
    elif a.mode=='Reconcile':reconcile()
    elif a.enable:run()
    else:ap.error('Default disabled; explicit --enable required')
