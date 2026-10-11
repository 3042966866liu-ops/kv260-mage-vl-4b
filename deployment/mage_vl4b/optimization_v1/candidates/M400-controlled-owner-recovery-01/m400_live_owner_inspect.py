"""Executed in original owner's main thread: read Python owners, never free resources."""
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

GATE='/home/ubuntu/m400_tail_layer_candidate_01/m400_tail_layer_gate.py'


def inspect_owner(ns):
    s=ns['layer_scope'];p=ns['policy'];rt=ns['runtime'];e=ns['engine'];r=ns['result']
    threads=[dict(name=t.name,ident=t.ident,alive=t.is_alive()) for t in threading.enumerate()]
    rows=[dict(bytes=int(b.nbytes),address=int(ns['base'].physical_address(b)),state=b.freebuffer.state,
               release_type=type(b.freebuffer).__name__) for b in ns['allocations']]
    proof=dict(model_logical_calls=rt.logical_calls,model_physical_calls=rt.host_calls,
        grouped_attention_calls=e.language.grouped_attention_calls,
        model_forward_calls=r['model_forward_calls'],vision_forward_calls=r.get('vision_forward_calls',0),
        transactions=r.get('transactions',[]),fpga_transactions=r['fpga_transactions'],
        blocked=r['blocked_inference_attempts'],releases=r['released_buffers'],buffers=rows,
        policy_active=p.active,policy_ever=p.ever,policy_completed=p.completed,policy_sealed=p.sealed,
        observer_alive=p.thread is not None and p.thread.is_alive(),observer_stop_reason=p.stop_reason,
        scope=dict(closed=s.closed,retained=s.retained,invoked=s.invoked,maps=list(s.maps),identities=list(s.identities),
            bindings=len(s.bindings),observer_present=s.observer is not None,family_rows=s.family_rows,
            result_present=s.result is not None,rows=s.rows),
        tail=dict(closed=s.tail.closed,retained=s.tail.retained,invoked=s.tail.invoked,bindings=len(s.tail.bindings),selected=s.tail.selected),
        original_family_bound_to_model=s.original_family.__self__ is e.language,
        current_family_same_function=s.original_family.__func__ is e.language._family.__func__,
        current_family_same_owner=e.language._family.__self__ is e.language,
        registry_entries=len(ns['registry'].entries),threads=threads,
        heartbeat_stop_set=ns['stopped'].is_set(),resident=s.resident(),safe=p.safe(),
        snapshot=ns['base'].transaction_snapshot(rt.kernel,rt.dma),
        original_scope_types=[type(s).__name__,type(s.tail).__name__],
        engine_board_same=e.board is rt,initialized=ns['initialized'],runtime_closed=rt._m368_closed)
    proof['runtime_buffers_are_original_allocations']=all(a is b for a,b in zip(
        list(rt.staged_buffers)+[rt.input_buffer,rt.output_buffer,rt.output_buffer_alt],ns['allocations']))
    # Barrier and reference check are original methods, with no resource mutation.
    s.barrier();s.check_unchanged()
    proof['original_barrier_and_reference_check_passed']=True
    checks=[rt.logical_calls==0,rt.host_calls==0,e.language.grouped_attention_calls==0,
        r['model_forward_calls']==0,r.get('vision_forward_calls',0)==0,not r.get('transactions'),
        r['fpga_transactions']==1,not r['blocked_inference_attempts'],not r['released_buffers'],
        rows==[dict(bytes=row['bytes'],address=row['address'],state='owned',release_type='OwnedBufferRelease')
               for row in r['allocated_buffers']],
        [row['bytes'] for row in rows]==[6963200]*4+[389152,2621440,2621440],
        not p.active,p.ever,p.completed,p.sealed,not proof['observer_alive'],p.stop_reason is None,
        not s.closed,s.retained,s.invoked,not s.maps,not s.identities,not s.bindings,
        s.observer is None,not s.family_rows,s.result is None,not s.rows,
        not s.tail.closed,not s.tail.retained,not s.tail.invoked,not s.tail.bindings,not s.tail.selected,
        proof['original_family_bound_to_model'],proof['current_family_same_function'],proof['current_family_same_owner'],
        len(rows)==7,all(t['name']=='MainThread' for t in threads),ns['stopped'].is_set(),
        proof['resident'],proof['safe'],proof['engine_board_same'],proof['initialized'],not proof['runtime_closed'],
        proof['runtime_buffers_are_original_allocations']]
    if not all(checks):raise RuntimeError('Pristine source-abort owner conditions differ: '+json.dumps(proof))
    proof['pristine_source_abort_conditions_passed']=True
    return proof


def main(out):
    result=dict(status='FAIL_LIVE_OWNER_INSPECTION',owner_pid=os.getpid(),resources_released=False,
                stable_overlay_restored=False,gate_return_code=1)
    try:
        if threading.current_thread() is not threading.main_thread():raise RuntimeError('Original main thread required')
        f=sys._current_frames()[threading.main_thread().ident];frames=[]
        while f is not None:
            if f.f_code.co_name=='main' and f.f_code.co_filename==GATE:frames.append(f)
            f=f.f_back
        if len(frames)!=1:raise RuntimeError('Unique original retained main frame absent')
        result['proof']=inspect_owner(frames[0].f_locals)
        result.update(status='PASS_LIVE_PRISTINE_SOURCE_ABORT_OWNER_INSPECTION',gate_return_code=0)
    except BaseException:
        import traceback
        result['traceback']=traceback.format_exc()
    p=Path(out);tmp=p.with_suffix('.part')
    tmp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');os.replace(tmp,p)
