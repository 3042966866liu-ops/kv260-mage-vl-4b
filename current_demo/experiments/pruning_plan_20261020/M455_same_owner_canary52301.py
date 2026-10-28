"""One real frozen Build-only transaction before the first borrowed vision call.

No allocation, configuration load, release or signal. Real caller predicates,
MMIO completion and complete golden bytes are mandatory. The seed is logged
separately from model requests and excluded from their timed work.
"""
import hashlib
import numpy as np
from M455_request_guard52301 import BorrowedPolicyBridge
from M455_adaptive_guard52301 import completed

def run_same_owner_canary(*,runtime,guard,ledger,base,packet,golden,weights,config,
                         identities,check_resources,wait_observed,result):
    def exact(raw,key):
        if not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=identities[key]:raise ValueError('Frozen same-owner canary payload differs: '+key)
    exact(packet,'packet');exact(golden,'golden')
    if len(weights)!=4 or len(identities['weights'])!=4:raise ValueError('Four exact original ports required')
    for raw,digest in zip(weights,identities['weights']):
        if not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Frozen canary port differs')
    if type(config)is not int or config!=0x10201:raise ValueError('Only original M455 Build-only config admitted')
    if (not callable(check_resources) or not callable(wait_observed) or guard.request is not None
        or guard.ever or guard.state.ever or guard.active or not guard.safe()):raise RuntimeError('Exactly one initial known-idle real-owner seed only')
    ledger.verify_full(runtime);check_resources()
    buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
    if len(buffers)!=7 or not 0<len(packet)<=buffers[4].nbytes or not 0<len(golden)<=buffers[5].nbytes:raise ValueError('Original seven capacity owners required')
    if any(not 0<len(raw)<=b.nbytes for raw,b in zip(weights,buffers[:4])):raise ValueError('Frozen canary port geometry differs')
    policy=BorrowedPolicyBridge(guard,ledger,runtime,check_resources)
    row=dict(scope='same_PID_same_owner_initial_build_only_canary',config=hex(config),input_bytes=len(packet),output_bytes=len(golden),
        packet_sha256=identities['packet'],golden_sha256=identities['golden'],physical_calls=0,completed=False,
        model_forward=False,inside_request_timing=False,old_completed_state_reused=False)
    result.setdefault('initialization_transactions',[]).append(row)
    guard.begin('same_owner_initial_build_only_canary',1)
    boundary=guard.request;boundary['manual_physical_calls']=0
    try:
        for raw,b in zip(weights,buffers[:4]):b[:len(raw)]=np.frombuffer(raw,np.uint8);b.sync_to_device()
        runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
        runtime.output_buffer[:len(golden)]=0xa5;runtime.output_buffer.sync_to_device()
        for register,b in zip(base.REG_POINTERS,buffers[:4]):base.write_u64(runtime.kernel,register,base.physical_address(b))
        runtime.kernel.write(base.REG_CONFIG,config);check_resources()
        # This transition is recorded immediately before the actual receive.
        # Any exception through completion leaves the shared state unknown.
        policy.active=True;policy.ever=True;policy.completed=False
        row['physical_calls']=1;boundary['manual_physical_calls']=1
        runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden))
        runtime.kernel.write(base.REG_AP_CTRL,1)
        runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet))
        observed,detail=wait_observed()
        if not completed(observed):raise RuntimeError('Actual same-owner M455 completion absent; retain all owners')
        policy.active=False;policy.completed=True
        runtime.output_buffer.sync_from_device();actual=bytes(memoryview(runtime.output_buffer)[:len(golden)])
        row.update(completed=True,snapshot=observed,observation=detail,output_sha256=hashlib.sha256(actual).hexdigest(),full_output_equal=actual==golden)
        if actual!=golden:raise RuntimeError('Frozen same-owner canary full output mismatch')
        guard.end();return row
    except BaseException:
        if guard.request is not None and guard.safe():guard.end()
        raise
    finally:
        # The raw canary writes registers and ports. No stale staged-language
        # configuration may survive into the first model request.
        runtime._programmed_config=None;runtime._programmed_weight_addresses=None
