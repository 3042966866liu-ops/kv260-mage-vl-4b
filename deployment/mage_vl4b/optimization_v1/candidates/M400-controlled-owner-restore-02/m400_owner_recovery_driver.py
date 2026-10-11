"""Install and trigger one cooperative original-owner recovery; never kill the owner."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
from m400_owner_readonly_probe import verify

def owner_snapshot(pid):
    p=Path('/proc')/str(pid);raw=(p/'stat').read_text();rest=raw[raw.rindex(')')+2:].split()
    fields=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
    if fields['Uid'].strip().split()[0]!='0' or fields['State'].strip()[0] not in ('S','T','t'):
        raise RuntimeError('Exact original root owner must remain in its retained loop')
    return dict(start_ticks=rest[19],command=(p/'cmdline').read_bytes().split(b'\0')[:-1])


HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m400_controlled_owner_restore_02')


def emit():
    raw=(OUT/'RESULT.json').read_bytes();n=(len(raw)+899)//900
    print('M400_RECOVER_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i in range(n):print('M400_RECOVER_CHUNK=%d/%d:%s'%(i,n,base64.b64encode(raw[i*900:(i+1)*900]).decode()),flush=True)


def process_state(pid):
    p=Path('/proc')/str(pid)
    if not p.exists():return None
    s=(p/'stat').read_text();return s[s.rindex(')')+2:].split()[0]


def main(expected):
    verify(expected)
    if os.geteuid()!=0 or OUT.exists():raise RuntimeError('Root/fresh controlled recovery required')
    pin=json.loads((HERE/'PIN.json').read_bytes());pid=pin['pid'];before=owner_snapshot(pid)
    if before['start_ticks']!=pin['start_ticks'] or [x.decode() for x in before['command']]!=pin['command']:
        raise RuntimeError('Exact original retained owner differs')
    original=Path(pin['original_package'])
    if hashlib.sha256((original/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()!=pin['original_manifest_sha256']:
        raise RuntimeError('Original package changed')
    for row in json.loads((original/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        p=original/row['path']
        if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Original payload changed')
    raw=Path(pin['original_raw'])
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=pin['original_raw_sha256']:raise RuntimeError('Original failure changed')
    # Capture the exact original process group before resuming only its Python owner.
    pgid=os.getpgid(pid)
    if pgid!=22712:raise RuntimeError('Original process group changed')
    OUT.mkdir();r=dict(status='FAIL_CONTROLLED_RECOVERY_DRIVER',gate_return_code=1,manifest_sha256=expected,
        original_owner_pid=pid,original_owner_start_ticks=pin['start_ticks'],owner_killed=False,
        original_failure_raw_sha256=pin['original_raw_sha256'],new_DMA_allocations=0,model_transactions=0)
    resumed=False;triggered=False
    try:
        os.kill(pid,signal.SIGCONT);resumed=True;time.sleep(.1)
        code='import sys;sys.path.insert(0,'+repr(str(HERE))+');import m400_owner_restore_endpoint as endpoint;endpoint.install('+repr(str(OUT))+','+repr(str(HERE))+','+repr(expected)+');sys.path.pop(0)'
        script=OUT/'install.gdb'
        script.write_text('set pagination off\nset scheduler-locking off\n'
            +'python [t for t in gdb.selected_inferior().threads() if t.ptid[1] == '+str(pid)+'][0].switch()\n'
            +'set $m400_gil = (int)PyGILState_Ensure()\n'
            +'set $m400_rc = (int)PyRun_SimpleString('+json.dumps(code)+')\n'
            +'printf "M400_ENDPOINT_PYRUN_RC=%d\\n", $m400_rc\n'
            +'call (void)PyGILState_Release($m400_gil)\ndetach\n',encoding='utf-8')
        try:
            gdb=subprocess.run(['/usr/bin/gdb','--nx','--nh','--readnever','--batch','-iex','set auto-load off',
                '-iex','set auto-solib-add off','-p',str(pid),'-x',str(script)],capture_output=True,timeout=12)
            r['gdb_return_code']=gdb.returncode;r['gdb_log']=gdb.stdout.decode(errors='replace')+gdb.stderr.decode(errors='replace')
        except subprocess.TimeoutExpired as exc:
            r['gdb_log']=(exc.output or b'').decode(errors='replace');raise
        ready=OUT/'READY.json'
        if gdb.returncode or 'M400_ENDPOINT_PYRUN_RC=0' not in r['gdb_log'] or not ready.exists():
            raise RuntimeError('Cooperative endpoint installation unproven; do not trigger')
        r['ready']=json.loads(ready.read_bytes())
        if r['ready']['owner_pid']!=pid or r['ready']['manifest_sha256']!=expected or not r['ready']['main_thread'] or r['ready']['resources_released']:
            raise RuntimeError('Endpoint owner identity differs')
        os.kill(pid,signal.SIGUSR1);triggered=True
        deadline=time.monotonic()+120;target=OUT/'OWNER_RESULT.json'
        while not target.exists() and time.monotonic()<deadline:
            print('M400_RECOVERY_HEARTBEAT waiting_original_owner_close',flush=True);time.sleep(5)
        if not target.exists():raise RuntimeError('Owner recovery budget exceeded; preserve process, no kill')
        r['owner_result']=json.loads(target.read_bytes())
        if r['owner_result']['gate_return_code']:raise RuntimeError('Original owner rejected close/restore; preserve remaining objects')
        for _ in range(50):
            state=process_state(pid)
            if state is None or state=='Z':break
            time.sleep(.1)
        else:raise RuntimeError('Owner close saved but original process did not exit; preserve')
        r['original_owner_exited']=True;r['owner_state_after_exit']=state
        # Original runner now only exports the saved failed raw. No hardware restart.
        os.killpg(pgid,signal.SIGCONT)
        time.sleep(.2)
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_RDWR)
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);r['execution_lock_released']=True
        finally:os.close(lock)
        r['original_failure_unchanged']=hashlib.sha256(raw.read_bytes()).hexdigest()==pin['original_raw_sha256']
        if not r['original_failure_unchanged']:raise RuntimeError('Saved original raw changed')
        r.update(status='PASS_CONTROLLED_OWNER_EXIT_AND_STABLE_RESTORE',gate_return_code=0)
    except BaseException:r['traceback']=traceback.format_exc()
    finally:
        r['cooperative_signal_sent']=triggered;r['exact_owner_resumed']=resumed
        state=process_state(pid);r['final_owner_state']=state
        if resumed and not triggered and state not in (None,'Z'):
            os.kill(pid,signal.SIGSTOP);r['retained_owner_stopped']=True
        # After a cooperative close has started, never stop/kill it on timeout.
        tmp=OUT/'RESULT.part';tmp.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');os.replace(tmp,OUT/'RESULT.json');emit()
    return r['gate_return_code']


if __name__=='__main__':
    if sys.argv[1:]==['Collect']:emit()
    elif len(sys.argv)==3 and sys.argv[1]=='--enable-controlled-owner-recovery':raise SystemExit(main(sys.argv[2]))
    else:raise SystemExit('Default off: controlled original-owner recovery only')
