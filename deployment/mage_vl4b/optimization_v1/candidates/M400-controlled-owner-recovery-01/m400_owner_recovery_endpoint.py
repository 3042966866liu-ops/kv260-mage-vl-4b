"""Cooperative original-main-thread exit for one proven pristine source-check abort."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import traceback
from m400_live_owner_inspect import inspect_owner,GATE


def close_pristine(ns):
    proof=inspect_owner(ns)
    s=ns['layer_scope'];tail=s.tail;engine=ns['engine'];rt=ns['runtime'];r=ns['result'];policy=ns['policy']
    policy.stop_sampling()
    # This exception is restricted to the proved pre-binding source abort.
    # Original close/barrier/reference checks still execute; all other failures retain.
    s.retained=False
    try:s.close()
    except BaseException:s.retained=True;raise
    if not s.closed or not tail.closed or s.maps or s.bindings or s.observer is not None:
        raise RuntimeError('Original scope closure incomplete; retain DMA owner')
    engine.close()
    if not rt._m368_closed or r['released_buffers']!=list(reversed(r['allocated_buffers'])):
        raise RuntimeError('Original engine release order/accounting differs')
    if any(b.freebuffer.state!='released' for b in ns['allocations']):
        raise RuntimeError('Original release wrappers unresolved')
    engine.language=engine.vision=engine.tokenizer=None
    ns['registry'].restore_all(completion_proven=True,release_proven=True)
    if ns['registry'].entries:raise RuntimeError('Original patch registry not cleared')
    return dict(pristine_proof=proof,scope_closed=s.closed,tail_closed=tail.closed,
                original_engine_closed=rt._m368_closed,release_records=list(r['released_buffers']),
                release_wrapper_states=[b.freebuffer.state for b in ns['allocations']],
                patch_registry_cleared=True)


def install(out,package,manifest):
    if threading.current_thread() is not threading.main_thread():raise RuntimeError('Original main thread required')
    frames=[];f=sys._current_frames()[threading.main_thread().ident]
    while f is not None:
        if f.f_code.co_name=='main' and f.f_code.co_filename==GATE:frames.append(f)
        f=f.f_back
    if len(frames)!=1:raise RuntimeError('Unique original main frame required')
    ns=frames[0].f_locals
    proof=inspect_owner(ns)
    out=Path(out);package=Path(package)
    if signal.getsignal(signal.SIGUSR1)!=signal.SIG_DFL:
        raise RuntimeError('Refuse overriding existing signal handler')
    original=Path('/home/ubuntu/m400_tail_layer_01/B1/load-memory.json')
    original_sha='de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9'
    def save(r):
        tmp=out/'OWNER_RESULT.part';tmp.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');os.replace(tmp,out/'OWNER_RESULT.json')
    def controlled_exit(signum,frame):
        r=dict(status='FAIL_ORIGINAL_OWNER_RECOVERY',gate_return_code=1,owner_pid=os.getpid(),
               stable_overlay_restored=False,original_failure_unchanged=False,manifest_sha256=manifest)
        try:
            if signum!=signal.SIGUSR1 or threading.current_thread() is not threading.main_thread():
                raise RuntimeError('Wrong cooperative recovery thread/signal')
            if hashlib.sha256(original.read_bytes()).hexdigest()!=original_sha:
                raise RuntimeError('Original failure raw changed before recovery')
            r['owned_close']=close_pristine(ns)
            stable=ns['STABLE'];stable_sha=ns['STABLE_SHA']
            # Same original owner/root/environment, original fixed preflight program.
            checked=subprocess.run([sys.executable,'-B',str(ns['HERE']/'m120_board_env_preflight.py'),
                '--candidate',str(stable),'--expected-package-manifest-sha256',stable_sha,
                '--result',str(out/'stable_restore_environment.json')],timeout=90)
            if checked.returncode:raise RuntimeError('Stable restore environment rejected')
            r['stable_environment_sha256']=hashlib.sha256((out/'stable_restore_environment.json').read_bytes()).hexdigest()
            bit=stable/'overlay/m120_m89x2_t32.bit'
            if hashlib.sha256(bit.read_bytes()).hexdigest()!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':
                raise RuntimeError('Stable rollback bit SHA differs')
            from pynq import Overlay
            restored=Overlay(str(bit),download=True)
            from m120_board_common import KERNEL_NAME,DMA_NAME
            r['stable_snapshot']=ns['base'].transaction_snapshot(getattr(restored,KERNEL_NAME),getattr(restored,DMA_NAME))
            r['stable_bit_sha256']=hashlib.sha256(bit.read_bytes()).hexdigest()
            r['stable_overlay_restored']=True;r['stable_restore_transaction_submitted']=False
            r['stable_snapshot_lifecycle']='fresh Overlay, no transaction; not completed-DMA idle evidence'
            r['original_failure_unchanged']=hashlib.sha256(original.read_bytes()).hexdigest()==original_sha
            if not r['original_failure_unchanged']:raise RuntimeError('Original failure raw changed')
            r.update(status='PASS_CONTROLLED_ORIGINAL_OWNER_RECOVERY',gate_return_code=0)
        except BaseException:
            r['traceback']=traceback.format_exc();save(r)
            return  # retain original process on incomplete recovery
        save(r)
        # Exit by original Python stack unwinding, preserving the original failed gate rc.
        raise SystemExit(1)
    signal.signal(signal.SIGUSR1,controlled_exit)
    ready=dict(owner_pid=os.getpid(),manifest_sha256=manifest,signal='SIGUSR1',
               main_thread=True,pristine_proof=proof,resources_released=False)
    (out/'READY.json').write_text(json.dumps(ready,indent=2)+'\n',encoding='utf-8')
