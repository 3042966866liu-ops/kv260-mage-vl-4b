"""Bounded GDB capability test against an owned CPU sentinel, never the FPGA owner."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

OUT=Path('/home/ubuntu/m400_gdb_cpu_sentinel_01')
HERE=Path(__file__).resolve().parent
SENTINEL='''import json,os,signal,threading,time
from pathlib import Path
from owned_buffer_release import OwnedBufferRelease
def main():
    stop=threading.Event()
    worker=threading.Thread(target=lambda:stop.wait(),name='CPU-sentinel-worker')
    worker.start()
    class Owner:
        def __init__(self):
            self.closed=False;self.releases=[];self.counts=[0]*7
            def make(i):
                def backend():self.counts[i]+=1
                return OwnedBufferRelease(backend,lambda:stop.is_set() and not worker.is_alive(),lambda:self.releases.append(i))
            self.buffers=[make(i) for i in range(7)]
        def close(self):
            if threading.current_thread() is not threading.main_thread():raise RuntimeError('Wrong original thread')
            stop.set();worker.join(1)
            if worker.is_alive():raise RuntimeError('Worker not drained')
            for b in reversed(self.buffers):b()
            for b in self.buffers:b()
            if self.counts!=[1]*7 or self.releases!=list(range(6,-1,-1)):raise RuntimeError('Ownership release differs')
            self.closed=True
    owner=Owner()
    Path(__file__).with_suffix('.ready').write_text(str(os.getpid()),encoding='utf-8')
    while True:time.sleep(.1)
main()
'''


def emit(path):
    raw=path.read_bytes();count=(len(raw)+899)//900
    print('M400_SENTINEL_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i in range(count):
        print('M400_SENTINEL_CHUNK=%d/%d:%s'%(i,count,base64.b64encode(raw[i*900:(i+1)*900]).decode()),flush=True)


def verify(expected):
    manifest=HERE/'PACKAGE_MANIFEST.json'
    if len(expected)!=64 or hashlib.sha256(manifest.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Sentinel manifest differs')
    m=json.loads(manifest.read_bytes())
    allowed={'m400_gdb_cpu_sentinel.py','owned_buffer_release.py','run_m400_cpu_sentinel.sh'}
    if {f['path'] for f in m['files']}!=allowed or m['file_count']!=len(allowed):
        raise RuntimeError('Sentinel whitelist differs')
    if {p.name for p in HERE.iterdir()}!=allowed|{'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Sentinel directory closure differs')
    for f in m['files']:
        p=HERE/f['path']
        if p.is_symlink() or p.stat().st_size!=f['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
            raise RuntimeError('Sentinel payload differs')
    if sum(f['bytes'] for f in m['files'])!=m['total_bytes']:
        raise RuntimeError('Sentinel byte count differs')


def main(expected):
    verify(expected)
    if os.geteuid()!=0 or OUT.exists():raise RuntimeError('Root/fresh sentinel directory required')
    OUT.mkdir()
    dummy=OUT/'cpu_sentinel.py';dummy.write_text(SENTINEL,encoding='utf-8')
    result=dict(status='FAIL_CPU_SENTINEL_GDB',gate_return_code=1,original_board_owner_attached=False,
                new_overlay_loads=0,new_DMA_allocations=0,CPU_sentinel_only=True,manifest_sha256=expected)
    child=None
    try:
        env=dict(os.environ,PYTHONPATH=str(HERE),PYTHONDONTWRITEBYTECODE='1')
        with (OUT/'sentinel.log').open('wb') as cpu_log:
            child=subprocess.Popen([sys.executable,'-B',str(dummy)],stdout=cpu_log,stderr=subprocess.STDOUT,env=env)
        deadline=time.monotonic()+3
        while not dummy.with_suffix('.ready').exists() and time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError('CPU sentinel exited before attach')
            time.sleep(.05)
        if not dummy.with_suffix('.ready').exists():raise RuntimeError('CPU sentinel readiness absent')
        if int(dummy.with_suffix('.ready').read_text())!=child.pid:
            raise RuntimeError('Sentinel readiness identity differs')
        result['sentinel_argv']=[sys.executable,'-B',str(dummy)]
        injected='''import sys,threading,json,os
from pathlib import Path
frames=[]
f=sys._current_frames()[threading.main_thread().ident]
while f is not None:
    if f.f_code.co_name=='main' and f.f_code.co_filename==%r:frames.append(f)
    f=f.f_back
if len(frames)!=1:raise RuntimeError('Unique original CPU owner frame absent')
owner=frames[0].f_locals['owner']
owner.close()
Path(%r).write_text(json.dumps(dict(pid=os.getpid(),closed=owner.closed,counts=owner.counts,releases=owner.releases,thread=threading.current_thread().name)),encoding='utf-8')
'''%(str(dummy),str(OUT/'owner_close.json'))
        code='exec('+repr(injected)+')'
        script=OUT/'inject.gdb'
        script.write_text('set pagination off\nset scheduler-locking off\n'
                          +'python [t for t in gdb.selected_inferior().threads() if t.ptid[1] == '+str(child.pid)+'][0].switch()\n'
                          +'set $m400_gil = (int)PyGILState_Ensure()\n'
                          +'set $m400_rc = (int)PyRun_SimpleString('+json.dumps(code)+')\n'
                          +'printf "M400_SENTINEL_PYRUN_RC=%d\\n", $m400_rc\n'
                          +'call (void)PyGILState_Release($m400_gil)\ndetach\n',encoding='utf-8')
        gdb=subprocess.run(['/usr/bin/gdb','--nx','--nh','--batch','-p',str(child.pid),'-x',str(script)],
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=12)
        (OUT/'gdb.log').write_bytes(gdb.stdout)
        result['gdb_return_code']=gdb.returncode
        result['gdb_log']=gdb.stdout.decode('utf-8',errors='replace')
        if gdb.returncode or b'M400_SENTINEL_PYRUN_RC=0' not in gdb.stdout or not (OUT/'owner_close.json').exists():
            raise RuntimeError('GDB injection unproven; never attach FPGA owner')
        proof=json.loads((OUT/'owner_close.json').read_text(encoding='utf-8'))
        if proof!=dict(pid=child.pid,closed=True,counts=[1]*7,releases=list(range(6,-1,-1)),thread='MainThread'):
            raise RuntimeError('CPU owner/thread/release proof differs')
        result.update(status='PASS_CPU_SENTINEL_ORIGINAL_OWNER_CLOSE',gate_return_code=0,proof=proof,
                      sentinel_pid=child.pid,owner_thread=True,worker_drained=True,seven_fake_releases_once=True)
    except BaseException:
        result['traceback']=traceback.format_exc()
    finally:
        if child is not None:
            result['sentinel_pid']=child.pid
            # This process owns only ordinary CPU test objects, never PYNQ/DMA.
            if child.poll() is None:child.terminate()
            try:result['sentinel_exit_code']=child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill();result['sentinel_exit_code']=child.wait(timeout=2)
        out=OUT/'RESULT.json';partial=OUT/'RESULT.part'
        partial.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');os.replace(partial,out)
        emit(out)
    return result['gate_return_code']


if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='Collect':
        emit(OUT/'RESULT.json')
    elif len(sys.argv)==3 and sys.argv[1]=='--enable-cpu-sentinel':
        raise SystemExit(main(sys.argv[2]))
    else:raise SystemExit('Default off: explicit CPU-only sentinel flag and manifest required')
