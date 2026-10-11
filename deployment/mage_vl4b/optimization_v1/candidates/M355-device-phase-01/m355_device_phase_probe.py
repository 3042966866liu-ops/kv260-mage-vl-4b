"""Four original chains, one transaction each; independent timing diagnostic."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
sys.dont_write_bytecode=True
import numpy as np
from completion_observer import wait_observed, ObservationFailure
from board_safety import safe_to_release
from measurement import sha256,write_json
from m341_build_id_gate import verify_self,service_stopped,STABLE,STABLE_SHA,ROOT
from m120_board_common import KERNEL_NAME,DMA_NAME
from owned_buffer_release import OwnedBufferRelease

HERE=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ubuntu/m355_device_phase_evidence_01')


def cma_free():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('CmaFree:'):return int(line.split()[1])*1024
    raise RuntimeError('CmaFree unavailable')


def require_memory(result,label):
    value=cma_free()
    result['memory'].append(dict(label=label,cma_free_bytes=value,required_bytes=64<<20))
    if value<64<<20:raise MemoryError('Actual allocated/staged diagnostic CMA reserve below 64MiB: '+str(value))


def identity(path):
    a=path.lstat()
    import stat
    if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1:raise RuntimeError('Plain sole-linked source required')
    return (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_mode,a.st_nlink)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('manifest_sha');parser.add_argument('--enable-device-phase-probe',action='store_true')
    args=parser.parse_args()
    if not args.enable_device_phase_probe:raise RuntimeError('Default disabled')
    if EVIDENCE.exists():raise RuntimeError('Existing evidence; collect only')
    EVIDENCE.mkdir(mode=0o700)
    result=dict(status='FAIL_DEVICE_PHASE_DIAGNOSTIC',gate_level='stable-chain-phase-diagnostic',build_id='0x4D395832',
        errors=[],transactions=[],memory=[],allocated_buffers=[],released_buffers=[],overlay_loaded=False,
        full_model_run=False,ps_preread_started=False,performance_pass=False,promoted=False,gate_return_code=1,
        kernel_start_writes_completed=0)
    buffers=[];kernel=dma=base=lock=None;active=False;ever_started=False;last_completed=False
    stopped=threading.Event();phase=['package'];start=time.monotonic()
    def beat():
        while not stopped.wait(30):print('M355_HEARTBEAT phase='+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    def release_safe():
        if active or base is None or kernel is None:return False
        snap=base.transaction_snapshot(kernel,dma)
        if ever_started:
            return last_completed and safe_to_release(snap) and snap.get('ap_return')==base.BUILD_ID and all(snap.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
        return (snap.get('ap_ctrl')==4 and snap.get('ap_return')==0 and snap.get('mm2s_dmasr')==snap.get('s2mm_dmasr')==0
            and snap.get('mm2s_error') is False and snap.get('s2mm_error') is False
            and all(snap.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error')))
    try:
        verify_self(HERE,args.manifest_sha);result['manifest_sha256']=args.manifest_sha
        if os.geteuid()!=0:raise RuntimeError('Root required')
        spec=json.loads((HERE/'CASE_CONTRACT.json').read_text(encoding='utf-8'))
        result['contract_sha256']=sha256(HERE/'CASE_CONTRACT.json')
        for name,source in spec['stable_sources'].items():
            if sha256(ROOT/source['path'])!=source['sha256']:raise RuntimeError('Frozen source mismatch: '+name)
        result['initial_service']=service_stopped()
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_before=sha256(boot);cmd_before=Path('/proc/cmdline').read_text()
        closure=json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if closure['status']!='PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED' or closure['errors']:raise RuntimeError('Hardware prerequisite rejected')
        sys.path.insert(0,str(STABLE/'runtime'))
        import board_runtime as base
        if Path(base.__file__).resolve()!=(STABLE/'runtime/board_runtime.py').resolve():raise RuntimeError('Unexpected imported board runtime')
        phase[0]='fixed-environment'
        env=EVIDENCE/'environment.json'
        checked=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),
            '--expected-package-manifest-sha256',STABLE_SHA,'--result',str(env)],timeout=90)
        if checked.returncode:raise RuntimeError('Fixed environment failed; no Overlay')
        result['environment_sha256']=sha256(env)
        from pynq import Overlay,allocate
        overlay=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
        kernel,dma=getattr(overlay,KERNEL_NAME),getattr(overlay,DMA_NAME);result['overlay_loaded']=True
        cases=spec['cases']
        maxima=[max(c['window_bytes_per_port'] for c in cases)]*4+[max(c['chain']['input_bytes'] for c in cases),max(c['chain']['output_bytes'] for c in cases)]
        for size in maxima:
            buffer=allocate((size,),dtype=np.uint8);buffers.append(buffer)
            row=dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)))
            result['allocated_buffers'].append(row)
            original=buffer.freebuffer
            buffer.freebuffer=OwnedBufferRelease(original,release_safe,lambda row=row:result['released_buffers'].append(row))
            if row['address']+size>base.LOW_END:raise RuntimeError('DMA outside original low DDR')
        require_memory(result,'after-all-six-real-diagnostic-allocations')
        bank,input_buffer,output_buffer=buffers[:4],buffers[4],buffers[5]
        layout_path=ROOT/spec['layout_path']
        if sha256(layout_path)!=spec['layout_sha256']:raise RuntimeError('Layout identity differs')
        for case in cases:
            chain=case['chain'];label=str(chain['layer'])+':'+chain['family'];phase[0]='stage:'+label
            print('M355_CHAIN_STAGE '+label,flush=True)
            require_memory(result,'before-stage:'+label)
            for shard,(buffer,expected) in enumerate(zip(bank,case['windows'])):
                path=layout_path.parent/expected['file'];before=identity(path)
                if before[2]!=expected['file_bytes']:raise RuntimeError('Shard size differs')
                with path.open('rb',buffering=0) as stream:
                    stream.seek(case['base_words']*16)
                    raw=stream.read(case['window_bytes_per_port'])
                if identity(path)!=before or len(raw)!=case['window_bytes_per_port'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:
                    raise RuntimeError('Original window identity/bytes differ')
                buffer[:len(raw)]=np.frombuffer(raw,np.uint8);buffer.sync_to_device();del raw
            values=(np.arange(32*chain['groups']*64,dtype=np.int32)%31-15).astype(np.float32)
            values=(values*np.float32(0.002)).reshape(32,chain['groups']*64)
            packet=base.pack_chain_input(chain,values,case['base_words'],activation_scale_shift=0)
            if hashlib.sha256(packet).hexdigest()!=case['packet_sha256']:raise RuntimeError('Frozen packet differs')
            input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);input_buffer.sync_to_device()
            output_buffer[:chain['output_bytes']]=0xA5;output_buffer.sync_to_device()
            require_memory(result,'before-transaction:'+label)
            for register,buffer in zip(base.REG_POINTERS,bank):base.write_u64(kernel,register,base.physical_address(buffer))
            kernel.write(base.REG_CONFIG,int(chain['config_u32'],16))
            phase[0]='transaction:'+label
            transaction=dict(label=label,chain_index=chain['chain_index'],chain_sha256=case['chain_sha256'],input_bytes=len(packet),
                output_bytes=chain['output_bytes'],bank_addresses=[base.physical_address(b) for b in bank])
            result['active_transaction']=transaction
            active=ever_started=True;last_completed=False;submitted=time.monotonic_ns();initial={};submission={}
            dma.recvchannel.transfer(output_buffer,nbytes=chain['output_bytes'])
            before=time.monotonic_ns();status=int(dma.mmio.read(base.DMA_S2MM_DMASR));after=time.monotonic_ns()
            submission['s2mm_after_transfer']=dict(status=status,before_ns=before,after_ns=after)
            if not status&3 and not status&0x770:initial['s2mm']=dict(before_ns=before,after_ns=after)
            before=time.monotonic_ns();kernel.write(base.REG_AP_CTRL,1);after=time.monotonic_ns()
            submission['ap_start_write']=dict(before_ns=before,after_ns=after)
            result['kernel_start_writes_completed']+=1
            dma.sendchannel.transfer(input_buffer,nbytes=len(packet))
            before=time.monotonic_ns();status=int(dma.mmio.read(base.DMA_MM2S_DMASR));after=time.monotonic_ns()
            submission['mm2s_after_transfer']=dict(status=status,before_ns=before,after_ns=after)
            if not status&3 and not status&0x770:initial['mm2s']=dict(before_ns=before,after_ns=after)
            try:
                snapshot,observed=wait_observed(lambda:base.transaction_snapshot(kernel,dma),submitted,initial_busy=initial)
            except ObservationFailure as exc:
                transaction['observation_failure']=exc.evidence;result['transactions'].append(transaction);raise
            if not safe_to_release(snapshot):raise RuntimeError('Completed state unsafe')
            active=False;last_completed=True
            transaction.update(observation=observed,submission_dma_observations=submission)
            output_buffer.sync_from_device()
            output=bytes(memoryview(output_buffer)[:chain['output_bytes']])
            transaction.update(output_sha256=hashlib.sha256(output).hexdigest(),expected_sha256=case['expected_ftz_sha256'])
            transaction['full_output_exact']=transaction['output_sha256']==case['expected_ftz_sha256']
            result['transactions'].append(transaction)
            if not transaction['full_output_exact']:raise RuntimeError('Independent full-output SHA differs')
            print('M355_CHAIN_DONE '+json.dumps(dict(label=label,wait_ms=observed['wait_ns']/1e6,unresolved=observed['dma_timing_unresolved'],exact=True)),flush=True)
        result['boot_unchanged']=sha256(boot)==boot_before;result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmd_before
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
        result['status']='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()
    finally:
        unsafe=bool(buffers) and not release_safe()
        if kernel is not None and base is not None:result['final_snapshot']=base.transaction_snapshot(kernel,dma)
        if not unsafe:
            try:
                for buffer in reversed(buffers):buffer.freebuffer()
            except BaseException as exc:
                unsafe=True;result['errors'].append('Cleanup retained: '+str(exc))
        result['unsafe_buffers_retained']=unsafe;result['safe_buffers_released']=not unsafe
        result['physical_transactions_started']=result['kernel_start_writes_completed']
        result['elapsed_s_diagnostic_not_performance']=time.monotonic()-start
        if unsafe:result['status']='FAIL_UNSAFE_RETAINED'
        result['gate_return_code']=0 if result['status']=='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC' else 1
        write_json(EVIDENCE/'device-phase.json',result);stopped.set()
        print('M355_RESULT_SAVED status='+result['status'],flush=True)
        if unsafe:
            from m355_export_result import emit_saved
            emit_saved()
            print('M355_RETAIN_PROCESS_AND_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return result['gate_return_code']


if __name__=='__main__':raise SystemExit(main())
