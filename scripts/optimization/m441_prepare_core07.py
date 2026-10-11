"""Adapt core admission to independently frozen protocol04/06, unchanged core."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    original=HERE/'m441_core_ooc.py';s=original.read_text(encoding='utf-8-sig')
    start=s.index('def ready():');end=s.index('\n\ndef prepare',start)
    s=s[:start]+'''def ready():
    from m441_boundary_control07 import prerequisites,require_validation
    prerequisites();require_validation('max')
    path=BASE/'runs/M441-boundary-timeout-07/RESULT.json'
    r=synchronized(path,'PASS_M441_BOUNDARY_EXPECTED_TIMEOUT','latest_m441_boundary07_timeout')
    assert r['original_rc']==0 and r['gate_rc']==1 and all(r['checks'].values())
    header=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json'
    h=json.loads(header.read_bytes());assert not h['missing_headers'] and h['source_sha256']=='de023abc5b849a56048d5e71bcefc67be1564fe150174607fdc89792905dbe6a'
    for row in h['recursive_inputs']:assert sha(ROOT/row['path'])==row['sha256']
    return path
'''+s[end:]
    # Remove obsolete preparation mutation entry; frozen original inputs reused.
    start=s.index('def prepare():');end=s.index('\n\ndef main',start);s=s[:start]+s[end:]
    s=s.replace("choices=('Prepare','Check','Run')","choices=('Check','Run')").replace("    if a.mode=='Prepare':prepare();return\n",'')
    s=s.replace('import subprocess','import subprocess\nimport time\nfrom m441_supervisor04 import boot,process as identity,classify,log_snapshot')
    anchor='    full=ready()\n'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''    policy=BASE/'runs/M441-core-admission07/RESULT.json'
    pol=synchronized(policy,'PREPARED_M441_CORE_ADMISSION07','latest_m441_core_admission07')
    for row in pol['files']:assert sha(ROOT/row['path'])==row['sha256']
''')
    s=s.replace('        rc=process.wait()', '''        born=identity(process.pid).get('creation_FILETIME');initial=boot();started=time.monotonic();next_live=0
        while process.poll() is None:
            if time.monotonic()>=next_live:
                state=identity(process.pid,born);current=boot()
                atomic(OUT/'core_ooc_LIVE.json',encoded(dict(status=classify(initial,current,state),process=state,start_boot=initial,boot=current,elapsed_s=time.monotonic()-started,log=log_snapshot(OUT/'core_ooc_console.log'))))
                next_live=time.monotonic()+30
            if time.monotonic()-started>8*3600:
                atomic(OUT/'core_ooc_exit.json',encoded(dict(hls_rc=None,wall_budget=True,process_retained=True,pid=process.pid,creation_FILETIME=born)),immutable=True)
                raise RuntimeError('Core wall budget: process retained, no shell allowed')
            time.sleep(1)
        rc=process.returncode''')
    atomic(HERE/'m441_core_ooc07.py',s.encode(),immutable=True)
    collector=(HERE/'m441_collect_core_ooc.py').read_text(encoding='utf-8-sig')
    collector=collector.replace('Maximum descriptor/FIFO/backpressure/timeout RTL gate with unchanged arithmetic; only then full-shell and original COM3 hardware gate order.', 'Independent maximum FIFO/backpressure/timeout already closed; next full shell and original COM3 hardware gate order.')
    atomic(HERE/'m441_collect_core_ooc07.py',collector.encode(),immutable=True)
    compile(s,'core_ooc06','exec');compile(collector,'collect_core_ooc06','exec')
    old=BASE/'runs/M441-record-pipeline-core-OOC-preparation-01/RESULT.json';p=json.loads(old.read_bytes())
    for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
    assert p['target_period_ns']==4.8 and p['original_constraint']['sha256']=='63ea420c7cd5b85ab6b683b1f04e1509facc1a68929ecc2c9896eeb8b79288b4'
    files=['m441_core_ooc07.py','m441_collect_core_ooc07.py','m441_boundary_control07.py','m441_supervisor04.py']
    r=dict(status='PREPARED_M441_CORE_ADMISSION07',original_preparation_sha256=sha(old),unchanged_implementation_inputs=True,
        default_disabled=True,prerequisites='Full real CSim + missing0 headers + W2/W4 complete Zero + independent max FIFO/backpressure and same-snapshot expected timeout synchronized before tool',
        previous_six_random_not_claimed=True,target_period_ns=4.8,wall_budget_s=8*3600,no_kill=True,board=False,implementation_started=False,
        files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in files])
    ev=BASE/'runs/M441-core-admission07/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_core_admission07',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
         f'## M441 同约束核实现独立准入07（2026-10-09）\n\nSHA {sha(ev)}；不改原188份实现输入及4.8ns/XDC，原六Random失败保留；独立最大FIFO压力/同快照timeout三记录通过才执行。8h有界保留进程，仅准备0实现/板端。')
    print(r['status'],sha(ev),flush=True)

if __name__=='__main__':main()
