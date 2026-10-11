"""Prepare or explicitly run same-constraint core implementation, never board."""
import argparse
import json
import subprocess
import time
from m441_supervisor04 import boot,process as identity,classify,log_snapshot
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_protocol_control import synchronized

OUT=ROOT/'tmp/m441_record_pipeline_02'
PROJECT=ROOT/'tmp/m441_hls_project_02'
PREP=BASE/'runs/M441-record-pipeline-core-OOC-preparation-01/RESULT.json'

def ready():
    from m441_boundary_control07 import prerequisites,require_validation
    prerequisites();require_validation('max')
    path=BASE/'runs/M441-boundary-timeout-07/RESULT.json'
    r=synchronized(path,'PASS_M441_BOUNDARY_EXPECTED_TIMEOUT','latest_m441_boundary07_timeout')
    assert r['original_rc']==0 and r['gate_rc']==1 and all(r['checks'].values())
    header=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json'
    h=json.loads(header.read_bytes());assert not h['missing_headers'] and h['source_sha256']=='de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a'
    for row in h['recursive_inputs']:assert sha(ROOT/row['path'])==row['sha256']
    return path




def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('Check','Run'));ap.add_argument('--enable',action='store_true');a=ap.parse_args()
    if a.mode=='Check':
        try:print('READY',sha(ready()))
        except (AssertionError,RuntimeError,KeyError,OSError) as exc:print('BLOCKED_BEFORE_TOOL',str(exc))
        return
    assert a.enable,'Default disabled: --enable required'
    full=ready()
    policy=BASE/'runs/M441-core-admission07/RESULT.json'
    pol=synchronized(policy,'PREPARED_M441_CORE_ADMISSION07','latest_m441_core_admission07')
    for row in pol['files']:assert sha(ROOT/row['path'])==row['sha256']
    p=synchronized(PREP,'PREPARED_M441_SAME_CONSTRAINT_CORE_OOC','latest_m441_core_OOC_preparation')
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert not (OUT/'core_ooc_console.log').exists() and not (OUT/'core_ooc_exit.json').exists(),'Existing attempt: collect only'
    assert not any(x.suffix in {'.rpt','.xml','.zip','.xpr','.dcp'} for x in (PROJECT/'hls/impl').rglob('*') if x.is_file())
    command=['D:/AMDDesignTools/2026.1/Vitis/bin/vitis-run.bat','--mode','hls','--tcl',str(OUT/'run_core_ooc.tcl'),'--log',str(OUT/'m441_core_ooc')]
    atomic(OUT/'core_ooc_start.json',encoded(dict(preparation_sha256=sha(PREP),full_chain_sha256=sha(full))),immutable=True)
    with (OUT/'core_ooc_console.log').open('xb') as stream:
        process=subprocess.Popen(command,cwd=ROOT/'tmp',stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        print('M441_CORE_OOC_STARTED pid='+str(process.pid),flush=True)
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
    print('M441_CORE_OOC_RETURN rc='+str(rc),flush=True)
    raise SystemExit(rc)

if __name__=='__main__':main()
