"""Frozen finite host supervisor for one fresh M443 shell attempt. No board."""
import argparse,json,subprocess,time,os
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
from m441_supervisor04 import boot,process,classify,log_snapshot
from m441_protocol_control import synchronized
PS='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
RUN=BASE/'runs/M443-shell-supervision-03'
PREP=RUN/'PREPARATION.json'
OUT=ROOT/'tmp'
NAMES=['m443_shell_control03.py','m443_build_shell.tcl','m443_run_shell.ps1','m443_prepare_shell03.py','m441_supervisor04.py','m441_protocol_control.py','m441_host_io08.py','m351_workflow.py']

def validate():
    paths=[(BASE/'runs/M443-shell-control-preparation-03/RESULT.json','PREPARED_M443_FROZEN_SHELL_CONTROLS03','latest_m443_shell_control_preparation03'),(BASE/'runs/M443-shell-preparation-01/RESULT.json','PREPARED_FRESH_SHELL_INPUTS_AFTER_RTL_GATES','M443_shell_preparation'),(BASE/'runs/M443-pair-pipeline-core-OOC-closure-03/RESULT.json','PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING','latest_m443_pair_pipeline_core_OOC03')]
    proof=[]
    for p,status,key in paths:
        j=synchronized(p,status,key);assert j['build_id']=='0x4D343433'
        if 'checks' in j:assert all(j['checks'].values()) and j['original_rc']==0
        for row in j.get('files',j.get('evidence',[])):assert sha(ROOT/row['path'])==row['sha256']
        proof.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    p=paths[1][0];j=json.loads(p.read_bytes());m=ROOT/j['manifest_path'];assert sha(m)==j['manifest_sha256'];man=json.loads(m.read_bytes())
    assert man['unchanged_board_topology'] and man['changed_bd_fields']==['kernel.vlnv','kernel.ip_revision']
    assert man['file_count']==len(man['files']) and man['total_bytes']==sum(x['bytes'] for x in man['files'])
    for row in man['files']:assert sha(m.parent/row['path'])==row['sha256'] and (m.parent/row['path']).stat().st_size==row['bytes']
    for row in j['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    return proof

def prepare():
    assert not PREP.exists();proof=validate()
    for p in [ROOT/'tmp/m443_shell_01',OUT/'m443_shell_console.log',OUT/'m443_shell_exit.json',RUN/'START.json']:assert not p.exists(),str(p)
    j=dict(status='PREPARED_M443_FINITE_SHELL_SUPERVISION03',build_id='0x4D343433',wall_budget_s=28800,files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in NAMES],prerequisites=proof,no_restart=True,no_kill=True,board=False,promotion=False)
    atomic(PREP,encoded(j),immutable=True)
    sync('latest_m443_shell_supervision_preparation03',dict(status=j['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),'## M443有限整壳监督准备03（2026-10-11）\n\nSHA '+sha(PREP)+'；真实核心4.8ns/全部RTL及数值已闭合，独立冻结整壳输入与控制SHA。只运行一次原200/100MHz拓扑，8h预算超限保留工具及T:映射，不kill；原Vivado返回值和严格DRC/时序/route/资源/bit/HWH收集完成前禁止上板。')
    print(j['status'],sha(PREP),flush=True)

def run():
    j=synchronized(PREP,'PREPARED_M443_FINITE_SHELL_SUPERVISION03','latest_m443_shell_supervision_preparation03');validate()
    for row in j['files']+j['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (RUN/'START.json').exists() and not (RUN/'RESULT.json').exists(),'Existing attempt: Observe or Collect only'
    assert not (OUT/'m443_shell_console.log').exists() and not (OUT/'m443_shell_exit.json').exists()
    command=[PS,'-NoLogo','-NoProfile','-File',str(HERE/'m443_run_shell.ps1'),'-Run'];log=RUN/'CONTROLLER.log'
    with log.open('xb') as stream:
        child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        born=process(child.pid).get('creation_FILETIME');initial=boot();at=time.monotonic()
        start=dict(preparation_sha256=sha(PREP),command=command,process=process(child.pid,born),start_boot=initial,controller_pid=os.getpid(),wall_budget_s=j['wall_budget_s'])
        atomic(RUN/'START.json',encoded(start),immutable=True)
        sync('latest_m443_shell_supervision_start03',dict(status='RUNNING_M443_FINITE_SHELL03',result=(RUN/'START.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'START.json'),board=False),'## M443完整200/100MHz整壳启动03（2026-10-11）\n\nSHA '+sha(RUN/'START.json')+'；已通过真实417792数值、六项新RTL、核心同4.8ns布线，冻结整壳输入与控制。独立一次8h有限实现，原PS/Vivado rc和映射回收独立保存；已有START后不改、不重跑、不kill。还未上板或评价请求提速。')
        print('M443_SHELL_STARTED pid='+str(child.pid)+' birth='+str(born),flush=True)
        retained=False
        while child.poll() is None:
            state=process(child.pid,born);current=boot();elapsed=time.monotonic()-at
            atomic(RUN/'PROGRESS.json',encoded(dict(stage='RUNNING_SHELL',status=classify(initial,current,state),process=state,start_boot=initial,boot=current,elapsed_s=elapsed,native_exit_exists=(OUT/'m443_shell_exit.json').exists(),log=log_snapshot(OUT/'m443_shell_console.log'))))
            if elapsed>j['wall_budget_s']:retained=True;break
            time.sleep(5)
        rc=None if retained else child.returncode
    result=dict(status='RETAINED_M443_SHELL_TOOL_WALL_BUDGET03' if retained else ('COMPLETED_M443_SHELL_TOOL03_AWAITING_STRICT_COLLECT' if rc==0 else 'STOP_M443_SHELL_TOOL03_AT_FAILED_LEVEL'),original_host_rc=rc,elapsed_s=time.monotonic()-at,process_pid=child.pid,process_creation_FILETIME=born,process_retained=retained,process_killed=False,preparation_sha256=sha(PREP),board=False,performance=False,promotion=False,evidence=[])
    for p in [RUN/'START.json',log,OUT/'m443_shell_exit.json',OUT/'m443_shell_mapping.json',OUT/'m443_shell_console.log',OUT/'m443_shell_vivado.log']:
        if p.exists() and not retained:result['evidence'].append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    if not retained:
        if not (OUT/'m443_shell_exit.json').exists() or json.loads((OUT/'m443_shell_exit.json').read_bytes()).get('vivado_rc')!=0 or not (OUT/'m443_shell_mapping.json').exists() or not json.loads((OUT/'m443_shell_mapping.json').read_bytes()).get('removed'):
            result['status']='STOP_M443_SHELL_TOOL03_AT_FAILED_LEVEL'
    p=RUN/'RESULT.json';atomic(p,encoded(result),immutable=True)
    sync('latest_m443_shell_supervision_result03',dict(status=result['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),board=False),'## M443整壳工具原返回闭合03（2026-10-11）\n\nSHA '+sha(p)+'；'+result['status']+'，原host rc'+str(rc)+'。只保存工具原字节，未做板端/请求测试；所有资源/DRC/route/时序/bit/HWH原证据严格收集通过才解锁。超限保留工具和映射，不kill、不重跑。')
    print(result['status'],sha(p),'host_rc='+str(rc),flush=True)
    return 0 if result['status']=='COMPLETED_M443_SHELL_TOOL03_AWAITING_STRICT_COLLECT' else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Prepare','Run']);ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Prepare':prepare()
    else:assert a.enable,'Explicit --enable required';raise SystemExit(run())
