"""Bounded original-owner Python inspection, no release or Overlay operation."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
from m400_owner_readonly_probe import verify,owner_snapshot

HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m400_live_owner_inspect_02')


def emit():
    raw=(OUT/'RESULT.json').read_bytes();n=(len(raw)+899)//900
    print('M400_LIVE_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i in range(n):print('M400_LIVE_CHUNK=%d/%d:%s'%(i,n,base64.b64encode(raw[i*900:(i+1)*900]).decode()),flush=True)


def main(expected):
    verify(expected)
    if os.geteuid()!=0 or OUT.exists():raise RuntimeError('Root/fresh live inspection required')
    pin=json.loads((HERE/'PIN.json').read_bytes());pid=pin['pid']
    before=owner_snapshot(pid)
    if before['start_ticks']!=pin['start_ticks'] or [x.decode() for x in before['command']]!=pin['command']:
        raise RuntimeError('Original stopped owner identity differs')
    original=Path(pin['original_package'])
    if hashlib.sha256((original/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()!=pin['original_manifest_sha256']:
        raise RuntimeError('Original package manifest changed')
    for row in json.loads((original/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        p=original/row['path']
        if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Original package payload changed')
    if hashlib.sha256(Path(pin['original_raw']).read_bytes()).hexdigest()!=pin['original_raw_sha256']:
        raise RuntimeError('Original failure raw changed')
    OUT.mkdir()
    r=dict(status='FAIL_LIVE_OWNER_DRIVER',gate_return_code=1,manifest_sha256=expected,
           original_owner_pid=pid,original_owner_start_ticks=pin['start_ticks'],resources_released=False,
           new_overlay_loads=0,new_DMA_allocations=0,stable_overlay_restored=False)
    resumed=False
    try:
        # Resume only this exact retained-loop Python owner, not the stopped shell job.
        os.kill(pid,signal.SIGCONT);resumed=True
        time.sleep(.1)
        target=OUT/'PYTHON_OWNER.json'
        payload=(HERE/'m400_live_owner_inspect.py').read_text(encoding='utf-8')
        code='ns={"__name__":"m400_owner_inspection"};exec('+repr(payload)+',ns);ns["main"]('+repr(str(target))+')'
        script=OUT/'inspect.gdb'
        script.write_text('set pagination off\nset scheduler-locking off\n'
            +'python [t for t in gdb.selected_inferior().threads() if t.ptid[1] == '+str(pid)+'][0].switch()\n'
            +'echo M400_LIVE_ATTACH_COMPLETE\n\n'
            +'set $m400_gil = (int)PyGILState_Ensure()\n'
            +'echo M400_LIVE_GIL_ACQUIRED\n\n'
            +'set $m400_rc = (int)PyRun_SimpleString('+json.dumps(code)+')\n'
            +'printf "M400_LIVE_PYRUN_RC=%d\\n", $m400_rc\n'
            +'call (void)PyGILState_Release($m400_gil)\ndetach\n',encoding='utf-8')
        gdb=subprocess.run(['/usr/bin/gdb','--nx','--nh','--readnever','--batch','-iex','set auto-load off','-iex','set auto-solib-add off','-p',str(pid),'-x',str(script)],
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=12)
        (OUT/'gdb.log').write_bytes(gdb.stdout)
        r['gdb_return_code']=gdb.returncode;r['gdb_log']=gdb.stdout.decode(errors='replace')
        if gdb.returncode or b'M400_LIVE_PYRUN_RC=0' not in gdb.stdout or not target.exists():
            raise RuntimeError('Original-owner read inspection unproven')
        r['live_owner']=json.loads(target.read_bytes())
        if r['live_owner']['gate_return_code']:raise RuntimeError('Owner conditions rejected; no release')
        r.update(status='PASS_LIVE_OWNER_PRISTINE_SOURCE_ABORT',gate_return_code=0)
    except subprocess.TimeoutExpired as exc:
        r['traceback']=traceback.format_exc();r['gdb_log']=(exc.output or b'').decode(errors='replace')
    except BaseException:r['traceback']=traceback.format_exc()
    finally:
        if resumed:
            # No forward was requested; preserve the exact owner again in stopped state.
            os.kill(pid,signal.SIGSTOP)
            for _ in range(20):
                try:after=owner_snapshot(pid);break
                except RuntimeError:time.sleep(.05)
            else:raise RuntimeError('Cannot confirm retained stopped owner')
            r['owner_after']={**after,'command':[x.decode() for x in after['command']]}
        r['owner_resumed_only_for_inspection']=resumed
        if hashlib.sha256(Path(pin['original_raw']).read_bytes()).hexdigest()!=pin['original_raw_sha256']:
            r.update(status='FAIL_ORIGINAL_RAW_CHANGED',gate_return_code=1)
        tmp=OUT/'RESULT.part';tmp.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');os.replace(tmp,OUT/'RESULT.json')
        emit()
    return r['gate_return_code']


if __name__=='__main__':
    if sys.argv[1:]==['Collect']:emit()
    elif len(sys.argv)==3 and sys.argv[1]=='--enable-read-only-owner-inspection':raise SystemExit(main(sys.argv[2]))
    else:raise SystemExit('Default off: exact read-only owner inspection flag required')
