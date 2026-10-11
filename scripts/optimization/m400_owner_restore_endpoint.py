"""Restore and exit only after proven original release; never call close/free again."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import traceback

GATE='/home/ubuntu/m400_tail_layer_candidate_01/m400_tail_layer_gate.py'
PARTIAL=Path('/home/ubuntu/m400_controlled_owner_recovery_01/RESULT.json')
PARTIAL_SHA='29e1ae162c6a0390abb43048fd86dcb71364d9cbf98dd9a672ca7057712799b1'


def verify_closed(ns):
    s=ns['layer_scope'];rt=ns['runtime'];e=ns['engine'];r=ns['result'];p=ns['policy']
    if not s.closed or s.retained or s.tail is not None or s.maps or s.bindings or s.observer is not None:
        raise RuntimeError('Closed scope conditions differ; no release retry')
    # Frozen M120/M276 close retains the closed board object as an attribute.
    if not rt._m368_closed or e.board is not rt or any(getattr(e,k) is not None for k in ('language','vision','tokenizer')):
        raise RuntimeError('Original engine close incomplete; no release retry')
    if len(ns['allocations'])!=7 or [b.freebuffer.state for b in ns['allocations']]!=['released']*7:
        raise RuntimeError('Original seven release wrappers unresolved')
    if r['released_buffers']!=list(reversed(r['allocated_buffers'])) or ns['registry'].entries:
        raise RuntimeError('Original release/patch ledger differs')
    if rt.logical_calls or rt.host_calls or r.get('transactions') or p.active or not p.completed or not p.ever:
        raise RuntimeError('Unexpected transaction history')
    if p.thread and p.thread.is_alive():raise RuntimeError('Observer remains alive')
    if [t.name for t in threading.enumerate()]!=['MainThread']:raise RuntimeError('Python worker remains')
    return dict(scope_closed=True,engine_closed=True,seven_original_wrappers_released=True,
                release_records=list(r['released_buffers']),patch_registry_cleared=True,no_release_retried=True)


def install(out,package,manifest):
    if threading.current_thread() is not threading.main_thread():raise RuntimeError('Original main thread required')
    frames=[];f=sys._current_frames()[threading.main_thread().ident]
    while f is not None:
        if f.f_code.co_name=='main' and f.f_code.co_filename==GATE:frames.append(f)
        f=f.f_back
    if len(frames)!=1:raise RuntimeError('Unique original main frame required')
    ns=dict(frames[0].f_globals);ns.update(frames[0].f_locals)
    proof=verify_closed(ns)
    if hashlib.sha256(PARTIAL.read_bytes()).hexdigest()!=PARTIAL_SHA:raise RuntimeError('Saved partial closure differs')
    prior=json.loads(PARTIAL.read_bytes())['owner_result']['owned_close']
    old=signal.getsignal(signal.SIGUSR1)
    if not callable(old) or old.__module__!='m400_owner_recovery_endpoint' or old.__name__!='controlled_exit':
        raise RuntimeError('Refuse replacing unrelated signal handler')
    out=Path(out)
    original=Path('/home/ubuntu/m400_tail_layer_01/B1/load-memory.json')
    original_sha='de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9'
    def save(r):
        tmp=out/'OWNER_RESULT.part';tmp.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');os.replace(tmp,out/'OWNER_RESULT.json')
    def controlled_restore(signum,frame):
        r=dict(status='FAIL_ORIGINAL_OWNER_STABLE_RESTORE',gate_return_code=1,owner_pid=os.getpid(),
               stable_overlay_restored=False,manifest_sha256=manifest,no_release_retried=True,owned_close=prior)
        try:
            if signum!=signal.SIGUSR1 or threading.current_thread() is not threading.main_thread():raise RuntimeError('Wrong original thread/signal')
            r['closed_state_rechecked']=verify_closed(ns)
            stable=ns['STABLE'];stable_sha=ns['STABLE_SHA']
            checked=subprocess.run([sys.executable,'-B',str(ns['HERE']/'m120_board_env_preflight.py'),
                '--candidate',str(stable),'--expected-package-manifest-sha256',stable_sha,
                '--result',str(out/'stable_restore_environment.json')],timeout=90)
            if checked.returncode:raise RuntimeError('Stable environment rejected')
            r['stable_environment_sha256']=hashlib.sha256((out/'stable_restore_environment.json').read_bytes()).hexdigest()
            bit=stable/'overlay/m120_m89x2_t32.bit';digest=hashlib.sha256(bit.read_bytes()).hexdigest()
            if digest!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac':raise RuntimeError('Stable bit changed')
            from pynq import Overlay
            restored=Overlay(str(bit),download=True)
            from m120_board_common import KERNEL_NAME,DMA_NAME
            r['stable_snapshot']=ns['base'].transaction_snapshot(getattr(restored,KERNEL_NAME),getattr(restored,DMA_NAME))
            r['stable_bit_sha256']=digest;r['stable_overlay_restored']=True
            r['stable_restore_transaction_submitted']=False
            r['stable_snapshot_lifecycle']='fresh Overlay, no transaction; not completed-DMA idle evidence'
            r['original_failure_unchanged']=hashlib.sha256(original.read_bytes()).hexdigest()==original_sha
            if not r['original_failure_unchanged']:raise RuntimeError('Original failure raw changed')
            r.update(status='PASS_CONTROLLED_ORIGINAL_OWNER_STABLE_RESTORE',gate_return_code=0)
        except BaseException:r['traceback']=traceback.format_exc();save(r);return
        save(r);raise SystemExit(1)
    signal.signal(signal.SIGUSR1,controlled_restore)
    (out/'READY.json').write_text(json.dumps(dict(owner_pid=os.getpid(),manifest_sha256=manifest,
        main_thread=True,resources_released=False,closed_state=proof),indent=2)+'\n',encoding='utf-8')
