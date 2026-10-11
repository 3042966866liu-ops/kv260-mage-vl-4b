"""Prepare or explicitly run same-constraint core implementation, never board."""
import argparse
import json
import subprocess
import time
from m441_supervisor04 import boot,process as identity,classify,log_snapshot
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_protocol_control import synchronized

OUT=ROOT/'tmp/m443_core_ooc_03'
PROJECT=ROOT/'tmp/m443_hls_project_03'
PREP=BASE/'runs/M443-pair-pipeline-core-OOC-preparation-03/RESULT.json'

def ready():
    path=BASE/'runs/M443-W2-W4-pair-pipeline-RTL-04/RESULT.json'
    r=json.loads(path.read_bytes());assert r['status'].startswith('PASS_') and len(r['results'])==6
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert sha(path) in (ROOT/name).read_text(encoding='utf-8-sig')
    return path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('Check','Run'));ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Check':
        try:print('READY',sha(ready()))
        except (AssertionError,RuntimeError,KeyError,OSError) as exc:print('BLOCKED_BEFORE_TOOL',str(exc))
        return
    assert a.enable,'Default disabled: --enable required'
    full=ready()
    p=synchronized(PREP,'PREPARED_M443_SAME_CONSTRAINT_CORE_OOC','latest_m443_core_OOC_preparation03')
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (OUT/'core_ooc_console.log').exists() and not (OUT/'core_ooc_exit.json').exists(),'Existing attempt: collect only'
    assert not any(x.suffix in {'.rpt','.xml','.zip','.xpr','.dcp'} for x in (PROJECT/'hls/impl').rglob('*') if x.is_file())
    command=['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(OUT/'run_core_ooc.tcl'),'--log',str(OUT/'m443_core_ooc')]
    atomic(OUT/'core_ooc_start.json',encoded(dict(preparation_sha256=sha(PREP),full_chain_sha256=sha(full))),immutable=True)
    with (OUT/'core_ooc_console.log').open('xb') as stream:
        process=subprocess.Popen(command,cwd=ROOT/'tmp',stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M443_CORE_OOC_STARTED pid='+str(process.pid),flush=True)
        born=identity(process.pid).get('creation_FILETIME');initial=boot();started=time.monotonic();next_live=0
        while process.poll() is None:
            if time.monotonic()>=next_live:
                state=identity(process.pid,born);current=boot()
                atomic(OUT/'core_ooc_LIVE.json',encoded(dict(status=classify(initial,current,state),process=state,start_boot=initial,boot=current,elapsed_s=time.monotonic()-started,log=log_snapshot(OUT/'core_ooc_console.log'))))
                next_live=time.monotonic()+30
            if time.monotonic()-started>8*3600:
                atomic(OUT/'core_ooc_exit.json',encoded(dict(hls_rc=None,wall_budget=True,process_retained=True,pid=process.pid,creation_FILETIME=born)),immutable=True)
                raise RuntimeError('Core wall budget: process retained, no shell allowed')
            time.sleep(1)
        rc=process.returncode
    atomic(OUT/'core_ooc_exit.json',encoded(dict(hls_rc=rc)),immutable=True)
    print('M443_CORE_OOC_RETURN rc='+str(rc),flush=True)
    from m443_collect_core03 import main as collect
    collect()
    raise SystemExit(rc)

if __name__=='__main__':main()
