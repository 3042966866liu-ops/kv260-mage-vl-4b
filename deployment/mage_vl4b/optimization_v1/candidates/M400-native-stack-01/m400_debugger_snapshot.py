"""Read saved probe artifacts and native stacks. GDB function calls are forbidden."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from m400_owner_readonly_probe import verify,owner_snapshot

OUT=Path('/home/ubuntu/m400_debugger_snapshot_01')


def emit():
    raw=(OUT/'RESULT.json').read_bytes();n=(len(raw)+899)//900
    print('M400_STACK_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i in range(n):print('M400_STACK_CHUNK=%d/%d:%s'%(i,n,base64.b64encode(raw[i*900:(i+1)*900]).decode()),flush=True)


def main(expected):
    verify(expected)
    if os.geteuid()!=0 or OUT.exists():raise RuntimeError('Root/fresh native-stack snapshot required')
    before=owner_snapshot(22715)
    if before['start_ticks']!='1935627':raise RuntimeError('Owner start identity differs')
    OUT.mkdir();r=dict(status='FAIL_NATIVE_STACK_SNAPSHOT',gate_return_code=1,manifest_sha256=expected,
        original_owner_pid=22715,resources_released=False,new_overlay_loads=0,new_DMA_allocations=0,
        function_calls_forbidden=True,owner_resumed=False,readnever_backtrace_may_be_incomplete=True)
    try:
        prior=Path('/home/ubuntu/m400_live_owner_inspect_01')
        r['saved_files']={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                          for p in prior.iterdir() if p.is_file()}
        target=prior/'PYTHON_OWNER.json'
        r['saved_python_owner']=json.loads(target.read_bytes()) if target.exists() else None
        r['gdb_version']=subprocess.run(['/usr/bin/gdb','--version'],capture_output=True,timeout=3).stdout.decode(errors='replace')
        with (OUT/'native_stack.log').open('wb') as log:
            try:
                gdb=subprocess.run(['/usr/bin/gdb','--nx','--nh','--readnever','--batch',
                    '-iex','set auto-load off','-p','22715','-ex','set may-call-functions off',
                    '-ex','info threads','-ex','thread apply all bt 10','-ex','detach'],
                    stdout=log,stderr=subprocess.STDOUT,timeout=15)
                r['gdb_return_code']=gdb.returncode
            except subprocess.TimeoutExpired:r['gdb_timeout']=True
        r['gdb_log']=(OUT/'native_stack.log').read_text(encoding='utf-8',errors='replace')
        if r.get('gdb_return_code')!=0:raise RuntimeError('Native-stack read did not complete')
        r.update(status='PASS_READONLY_NATIVE_STACK_SNAPSHOT',gate_return_code=0)
    except BaseException:r['traceback']=traceback.format_exc()
    finally:
        after=owner_snapshot(22715)
        r['owner_after']={**after,'command':[x.decode() for x in after['command']]}
        r['proc_status']=Path('/proc/22715/status').read_text(encoding='utf-8')
        if after['start_ticks']!='1935627':r.update(status='FAIL_OWNER_IDENTITY',gate_return_code=1)
        tmp=OUT/'RESULT.part';tmp.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');os.replace(tmp,OUT/'RESULT.json');emit()
    return r['gate_return_code']


if __name__=='__main__':
    if sys.argv[1:]==['Collect']:emit()
    elif len(sys.argv)==3 and sys.argv[1]=='--enable-native-stack-snapshot':raise SystemExit(main(sys.argv[2]))
    else:raise SystemExit('Default off: native stack snapshot only')
