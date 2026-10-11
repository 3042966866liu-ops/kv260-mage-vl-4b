"""Independent full real numerical gate for the resource-admitted M443 revision."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync
from m441_supervisor04 import boot, process, classify

OUT = ROOT/'tmp/m443_full_numeric_03'
PROJECT = ROOT/'tmp/m443_full_csim_project_03'
PREP = BASE/'runs/M443-full-numeric-preparation-03/RESULT.json'
RUN = BASE/'runs/M443-full-numeric-csim-03'

def synchronized(path):
    digest=sha(path)
    assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))

def prepare():
    assert not OUT.exists() and not PROJECT.exists() and not PREP.exists()
    guard=BASE/'runs/M443-pair-pipeline-resource-guard-03/RESULT.json'
    synchronized(guard)
    g=json.loads(guard.read_bytes())
    assert g['status']=='PASS_M443_HLS_RESOURCE_AND_MAC_GUARD03' and all(g['checks'].values())
    old=BASE/'runs/M441-full-numeric-preparation-01/RESULT.json'
    p=json.loads(old.read_bytes())
    old_pass=BASE/'runs/M441-full-numeric-csim-01/RESULT.json'
    assert json.loads(old_pass.read_bytes())['status']=='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'
    source_p=BASE/'runs/M443-pair-pipeline-preparation-03/RESULT.json'
    s=json.loads(source_p.read_bytes())
    cases=[]
    for case in p['cases']:
        src=ROOT/case['fixture_path']; assert sha(src)==case['fixture_sha256']
        dest=OUT/src.name; atomic(dest,src.read_bytes(),immutable=True)
        row=dict(case);row.update(fixture_path=dest.relative_to(ROOT).as_posix(),fixture_sha256=sha(dest))
        cases.append(row)
    source_root=ROOT/'tmp/m443_pair_pipeline_03'
    for row in s['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256']
        if src.suffix in ('.cpp','.hpp','.h'):
            atomic(OUT/'source'/src.relative_to(source_root),src.read_bytes(),immutable=True)
    tb=HERE/'m441_full_chain_tb.cpp'
    text=tb.read_text(encoding='utf-8')
    assert text.count('0x4D343431')==1
    atomic(OUT/'m443_full_chain_tb.cpp',text.replace('0x4D343431','0x4D343433').encode('utf-8'),immutable=True)
    tcl=f'''set root {{{OUT.as_posix()}}}
set project {{{PROJECT.as_posix()}}}
if {{[file exists $project]}} {{error "Existing CSim: collect only"}}
set ::env(M441_FULL_FIXTURE_ROOT) $root
open_project $project
set_top m89x_runtime_kernel
add_files [file join $root source hls mage_prefill_m89x_runtime mage_prefill_m89x_runtime.cpp]
add_files -tb [file join $root m443_full_chain_tb.cpp] -cflags "-I[file join $root source hls mage_prefill_m89x_runtime]"
open_solution hls -flow_target vivado
set_part {{xck26-sfvc784-2LV-c}}
create_clock -period 4.8 -name default
set_clock_uncertainty 1.3
config_compile -pipeline_loops 0
csim_design -clean -O
exit
'''
    atomic(OUT/'run.tcl',tcl.encode('utf-8'),immutable=True)
    r=dict(status='PREPARED_M443_FULL_REAL_NUMERIC03',build_id='0x4D343433',source_sha256=g['source_sha256'],guard_sha256=sha(guard),original_fixture_preparation_sha256=sha(old),original_numeric_PASS_sha256=sha(old_pass),original_tb_sha256=sha(tb),testbench_only_change='expected BuildID',cases=cases,reference_recomputed=False,board=False,files=[dict(path=q.relative_to(ROOT).as_posix(),sha256=sha(q),bytes=q.stat().st_size) for q in sorted(OUT.rglob('*')) if q.is_file()])
    atomic(PREP,encoded(r),immutable=True)
    sync('latest_m443_full_numeric_preparation03',dict(status=r['status'],result=PREP.relative_to(ROOT).as_posix(),sha256=sha(PREP),board=False),f'## M443完整真实数值准备03（2026-10-10）\n\nSHA {sha(PREP)}；仅复用原完整gate_up/down/Q输入、真实权重和逐位参考，417792输出，不重算参考。资源门禁原SHA核对；独立工具/输出，不重跑M441。下一步完整CSim，非RTL或板端性能。')
    print(r['status'],sha(PREP),flush=True)

def collect():
    p=json.loads(PREP.read_bytes());assert all(sha(ROOT/r['path'])==r['sha256'] for r in p['files'])
    exit_path=RUN/'EXIT.json';receipt=json.loads(exit_path.read_bytes())
    assert not receipt['process_retained'] and not receipt['budget_exceeded']
    log=PROJECT/'hls/csim/report/m89x_runtime_kernel_csim.log'
    text=log.read_text(encoding='utf-8-sig') if log.exists() else ''
    found=re.findall(r'^M441_FULL_CHAIN_PASS ordinal=(\d+) output_words=(\d+)\s*$',text,re.M)
    expected=[(str(c['ordinal']),str(c['chain']['output_bytes']//8)) for c in p['cases']]
    checks=dict(original_rc=receipt['original_rc']==0,all_real_full_cases=found==expected,total_output_words='M441_FULL_TOTAL_OUTPUT_WORDS=417792' in text,numeric_marker='M441_FULL_REAL_WEIGHT_NUMERICAL_PASS' in text,completion='CSim done with 0 errors' in text,source_and_fixture_SHA=True,no_mismatch='M441 full output mismatch' not in text and 'M441 wrong status' not in text)
    r=dict(status=('PASS' if all(checks.values()) else 'FAIL')+'_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03',build_id='0x4D343433',checks=checks,original_rc=receipt['original_rc'],cases=found,output_words=417792 if checks['total_output_words'] else None,preparation_sha256=sha(PREP),exit_sha256=sha(exit_path),log_sha256=sha(log) if log.exists() else None,console_sha256=sha(OUT/'console.log'),all_data_keep_strb_TLAST_status_stream_consumption_checked=all(checks.values()),CSim_streams_unbounded=True,bounded_RTL=False,board=False,performance=False)
    dest=RUN/'RESULT.json';atomic(dest,encoded(r),immutable=True)
    sync('latest_m443_full_numeric_csim03',dict(status=r['status'],result=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),board=False),f'## M443完整真实权重CSim03（2026-10-10）\n\nSHA {sha(dest)}；{r["status"]}，原rc{r["original_rc"]}；原完整三family/417792输出/sideband/Build/流消耗判据。CSim队列无界，尚未RTL背压/实际时序/上板。失败保留且仅本级。')
    print(r['status'],sha(dest),checks,flush=True)
    return 0 if all(checks.values()) else 1

def run():
    synchronized(PREP);p=json.loads(PREP.read_bytes())
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in p['files'])
    prep_sha=sha(PREP);controller_sha=sha(Path(__file__))
    assert not RUN.exists() and not PROJECT.exists() and not (OUT/'console.log').exists()
    RUN.mkdir(parents=True)
    cmd=['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(OUT/'run.tcl'),'--log',str(OUT/'vitis')]
    start=time.monotonic();start_boot=boot();budget=7200;retained=False
    with (OUT/'console.log').open('xb') as log:
        child=subprocess.Popen(cmd,cwd=ROOT/'tmp',stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        identity=process(child.pid);born=identity.get('creation_FILETIME')
        active=dict(status='RUNNING_M443_FULL_NUMERIC03',pid=child.pid,creation_FILETIME=born,preparation_sha256=prep_sha,controller_sha256=controller_sha,command=cmd,wall_budget_s=budget)
        atomic(RUN/'ACTIVE.json',encoded(active),immutable=True)
        sync('latest_m443_full_numeric_active03',dict(status=active['status'],result=(RUN/'ACTIVE.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'ACTIVE.json'),board=False),f'## M443完整数值CSim03启动（2026-10-10）\n\nSHA {sha(RUN / "ACTIVE.json")}；PID{child.pid}，2h有限预算，超限保留工具不kill，已有尝试仅观察/Collect，不扩大RTL/上板。')
        print(json.dumps(active),flush=True)
        while child.poll() is None:
            state=process(child.pid,born)
            atomic(RUN/'PROGRESS.json',encoded(dict(status=classify(start_boot,boot(),state),process=state,elapsed_s=time.monotonic()-start,budget_s=budget)))
            if time.monotonic()-start>budget:retained=True;break
            time.sleep(10)
        receipt=dict(original_rc=None if retained else child.returncode,elapsed_s=time.monotonic()-start,budget_exceeded=retained,process_retained=retained,process_killed=False,preparation_sha256=prep_sha,console_sha256=sha(OUT/'console.log'))
        atomic(RUN/'EXIT.json',encoded(receipt),immutable=True)
    print(json.dumps(receipt),flush=True)
    return 1 if retained else collect()

if __name__=='__main__':
    mode=sys.argv[1:];assert mode in (['prepare'],['run'],['collect'])
    if mode==['prepare']:prepare()
    else:raise SystemExit(run() if mode==['run'] else collect())
