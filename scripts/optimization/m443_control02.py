"""Single finite revision02 HLS tool. Identities computed before launch."""
import json
import subprocess
import time
from pathlib import Path
from m441_host_io08 import atomic
from m351_workflow import ROOT,BASE,encoded,sha,sync
from m441_supervisor04 import boot,process,classify

out=ROOT/'tmp/m443_pair_pipeline_02'
run=BASE/'runs/M443-pair-pipeline-hls-02'
prep=BASE/'runs/M443-pair-pipeline-preparation-02/RESULT.json'
p=json.loads(prep.read_bytes())
assert all(sha(ROOT/r['path'])==r['sha256'] for r in p['files'])
prep_sha=sha(prep);control_sha=sha(Path(__file__))
assert all(prep_sha in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
assert not run.exists() and not (out/'hls_console.log').exists() and not (ROOT/'tmp/m443_hls_project_02').exists()
run.mkdir(parents=True)
command=['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(out/'run_m443_hls.tcl'),'--log',str(out/'m443_hls')]
start=time.monotonic();start_boot=boot();budget=7200;retained=False
with (out/'hls_console.log').open('xb') as log:
    child=subprocess.Popen(command,cwd=ROOT/'tmp',stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    identity=process(child.pid);born=identity.get('creation_FILETIME')
    active=dict(status='RUNNING_M443_HLS_RESOURCE_REVISION02',pid=child.pid,creation_FILETIME=born,preparation_sha256=prep_sha,controller_sha256=control_sha,command=command,wall_budget_s=budget)
    atomic(run/'ACTIVE.json',encoded(active),immutable=True)
    sync('latest_m443_hls_active02',dict(status=active['status'],result=(run/'ACTIVE.json').relative_to(ROOT).as_posix(),sha256=sha(run/'ACTIVE.json'),board=False),f'## M443资源本级HLS02启动（2026-10-10）\n\nSHA {sha(run / "ACTIVE.json")}；PID{child.pid}，2h有限预算，原01冻结，超限保留不kill，不扩大RTL/上板。')
    print(json.dumps(active),flush=True)
    while child.poll() is None:
        state=process(child.pid,born);current=boot()
        atomic(run/'PROGRESS.json',encoded(dict(status=classify(start_boot,current,state),process=state,elapsed_s=time.monotonic()-start,budget_s=budget)))
        if time.monotonic()-start>budget:retained=True;break
        time.sleep(10)
    receipt=dict(original_rc=None if retained else child.returncode,elapsed_s=time.monotonic()-start,budget_exceeded=retained,process_retained=retained,process_killed=False,preparation_sha256=prep_sha,console_sha256=sha(out/'hls_console.log'))
    atomic(run/'EXIT.json',encoded(receipt),immutable=True)
print(json.dumps(receipt),flush=True)
raise SystemExit(1 if retained or receipt['original_rc'] else 0)
