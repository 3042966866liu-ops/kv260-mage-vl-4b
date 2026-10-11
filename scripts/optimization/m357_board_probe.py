"""New circuit lower gates and balanced original-Q comparison; disabled by default.

All staging/verification precedes the timed DMA submission. An unresolved active
transaction retains its process, lock, overlay and every owned buffer.
"""
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
import numpy as np
from board_safety import safe_to_release
from owned_buffer_release import OwnedBufferRelease
from measurement import sha256,write_json
from m341_build_id_gate import verify_self,service_stopped,STABLE,STABLE_SHA,ROOT
from m120_board_common import KERNEL_NAME,DMA_NAME
from m357_completion_observer import wait_observed,ObservationFailure

HERE=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ubuntu/m357_board_evidence_01')
NEW_BUILD=0x4d333537
OLD_BUILD=0x4d395832
MODES=('BuildID','Descriptor','Chain','Compare')

def meminfo():
    wanted={'CmaFree','MemAvailable','Cached'};data={}
    for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
        key=line.split(':')[0]
        if key in wanted:data[key]=int(line.split()[1])*1024
    if len(data)!=3:raise RuntimeError('Actual memory counters unavailable')
    return data

def identity(path):
    import stat
    a=path.lstat()
    if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1:raise RuntimeError('Plain sole-linked file required')
    return (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_mode,a.st_nlink)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('mode',choices=MODES)
    ap.add_argument('--enable-candidate-gate',action='store_true');ap.add_argument('--prior-sha')
    args=ap.parse_args()
    if not args.enable_candidate_gate:raise RuntimeError('Default disabled')
    directory=EVIDENCE/args.mode
    if directory.exists():raise RuntimeError('Original result/attempt exists; collect only')
    directory.mkdir(parents=True,mode=0o700)
    result=dict(status='FAIL_M357_'+args.mode.upper(),gate_level=args.mode,build_id='0x4D333537',
        manifest_sha256=args.manifest_sha,package_verified=False,
        errors=[],transactions=[],memory=[],allocations=[],releases=[],overlay_loads=[],
        numerical_pass=False,chain_performance_pass=False,full_model=False,video=False,promoted=False,gate_return_code=1)
    buffers=[];kernel=dma=overlay=base=lock=None
    result['physical_transactions_started']=0
    active=False;ever_started=False;last_completed=False;expected_build=None
    stopped=threading.Event();phase=['package']
    def beat():
        while not stopped.wait(30):print('M357_HEARTBEAT mode='+args.mode+' phase='+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    def release_safe():
        if active or base is None or kernel is None:return False
        snap=base.transaction_snapshot(kernel,dma)
        if any(snap.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
        if ever_started:return last_completed and safe_to_release(snap) and snap['ap_return']==expected_build
        # Known lifecycle: this process has submitted no DMA or kernel transaction.
        return snap.get('ap_ctrl')==4 and snap.get('ap_return')==0 and snap.get('mm2s_dmasr')==snap.get('s2mm_dmasr')==0 and snap.get('mm2s_error') is False and snap.get('s2mm_error') is False
    def release_all():
        while buffers:
            buffers[-1].freebuffer()
            buffers.pop()
    def require_memory(label):
        row=dict(label=label,**meminfo(),required_cma_free_bytes=64<<20);result['memory'].append(row)
        if row['CmaFree']<64<<20:raise MemoryError('Real allocated diagnostic reserve below64MiB: '+str(row['CmaFree']))
    def load(variant,label):
        nonlocal kernel,dma,overlay,expected_build,ever_started,last_completed
        if active or buffers:raise RuntimeError('Live storage before Overlay change')
        target=STABLE if variant=='A' else HERE
        digest=STABLE_SHA if variant=='A' else args.manifest_sha
        checked=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),
            '--candidate',str(target),'--expected-package-manifest-sha256',digest,'--result',str(directory/(label+'_environment.json'))],timeout=90)
        if checked.returncode:raise RuntimeError('Fixed environment rejected; no Overlay')
        from pynq import Overlay,Clocks
        phase[0]='load:'+variant
        overlay=Overlay(str(target/'overlay/m120_m89x2_t32.bit'),download=True)
        kernel,dma=getattr(overlay,KERNEL_NAME),getattr(overlay,DMA_NAME)
        expected_build=OLD_BUILD if variant=='A' else NEW_BUILD
        ever_started=last_completed=False
        clocks={str(i):float(getattr(Clocks,'fclk'+str(i)+'_mhz')) for i in range(4)}
        result['overlay_loads'].append(dict(variant=variant,label=label,bit_sha256=sha256(target/'overlay/m120_m89x2_t32.bit'),clocks_mhz=clocks))
    def allocate_owned(sizes,label):
        from pynq import allocate
        for size in sizes:
            buffer=allocate((size,),dtype=np.uint8);buffers.append(buffer)
            row=dict(label=label,bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)))
            result['allocations'].append(row)
            buffer.freebuffer=OwnedBufferRelease(buffer.freebuffer,release_safe,lambda row=row:result['releases'].append(row))
            if row['address']+size>base.LOW_END:raise RuntimeError('Buffer outside original low DDR ABI')
        require_memory('allocated:'+label)
    def transact(packet,golden,config,label,variant):
        nonlocal active,ever_started,last_completed
        bank,tx,rx=buffers[:4],buffers[4],buffers[5]
        tx[:len(packet)]=np.frombuffer(packet,np.uint8);tx.sync_to_device()
        rx[:len(golden)]=0xa5;rx.sync_to_device()
        require_memory('before-submit:'+label)
        for reg,buffer in zip(base.REG_POINTERS,bank):base.write_u64(kernel,reg,base.physical_address(buffer))
        kernel.write(base.REG_CONFIG,config)
        row=dict(label=label,variant=variant,input_bytes=len(packet),output_bytes=len(golden),
            config=hex(config),packet_sha256=hashlib.sha256(packet).hexdigest(),expected_sha256=hashlib.sha256(golden).hexdigest(),
            weight_addresses=[int(base.physical_address(b)) for b in bank])
        result['active_transaction']=row
        active=ever_started=True;last_completed=False;phase[0]='transaction:'+label
        submitted=time.monotonic_ns()
        result['physical_transactions_started']+=1
        dma.recvchannel.transfer(rx,nbytes=len(golden))
        kernel.write(base.REG_AP_CTRL,1)
        dma.sendchannel.transfer(tx,nbytes=len(packet))
        try:
            snap,observed=wait_observed(lambda:base.transaction_snapshot(kernel,dma),submitted,timeout_s=10.0,expected_build_id=expected_build)
        except ObservationFailure as exc:
            row['observation_failure']=exc.evidence;result['transactions'].append(row);raise
        if not safe_to_release(snap):raise RuntimeError('Completed kernel/DMA state unsafe')
        active=False;last_completed=True
        row.update(observation=observed,wait_ns=observed['wait_ns'])
        rx.sync_from_device();raw=bytes(memoryview(rx)[:len(golden)])
        row.update(full_output_exact=raw==golden,output_sha256=hashlib.sha256(raw).hexdigest(),completed_snapshot=snap)
        result['transactions'].append(row)
        if not row['full_output_exact']:raise RuntimeError('Complete wire output differs')
        print('M357_TRANSACTION_DONE '+json.dumps(dict(label=label,variant=variant,wait_ms=row['wait_ns']/1e6,exact=True)),flush=True)
    def zero(variant,label):
        load(variant,label);allocate_owned([144]*4+[len(zero_packet),len(zero_golden)],label)
        for buffer in buffers[:4]:buffer[:]=0;buffer.sync_to_device()
        transact(zero_packet,zero_golden,int(spec['build_config'],16),label,variant);release_all()
    try:
        verify_self(HERE,args.manifest_sha);result['package_verified']=True
        if os.geteuid()!=0:raise RuntimeError('Root required')
        closure=json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if closure['status']!='PASS_ALL_NEW_CIRCUIT_PREREQUISITES':raise RuntimeError('New circuit prerequisites incomplete')
        if args.mode!='BuildID':
            prior_mode=MODES[MODES.index(args.mode)-1];prior=EVIDENCE/prior_mode/'BOARD_RESULT.json'
            if not args.prior_sha or sha256(prior)!=args.prior_sha:raise RuntimeError('Prior gate raw SHA differs')
            prior_data=json.loads(prior.read_text(encoding='utf-8'))
            if prior_data['status']!='PASS_M357_'+prior_mode.upper() or prior_data['gate_return_code']!=0:raise RuntimeError('Prior lower gate rejected')
            result['prior_raw_sha256']=args.prior_sha
        spec=json.loads((HERE/'BOARD_CASES.json').read_text(encoding='utf-8'))
        for row in spec['files']:
            if sha256(HERE/row['path'])!=row['sha256']:raise RuntimeError('Frozen fixture differs')
        for name,row in spec['stable_sources'].items():
            if sha256(ROOT/row['path'])!=row['sha256']:raise RuntimeError('Stable installed source differs: '+name)
        result['initial_service']=service_stopped()
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_before=sha256(boot);cmd_before=Path('/proc/cmdline').read_text(encoding='utf-8')
        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base
        if Path(base.__file__).resolve()!=(STABLE/'runtime/board_runtime.py').resolve():raise RuntimeError('Unexpected stable runtime import')
        zero_packet=(HERE/'build_packet.bin').read_bytes();zero_golden=(HERE/'build_golden.bin').read_bytes()
        if args.mode=='BuildID':zero('B','candidate-build-id')
        else:
            case=spec['original_q_case'];chain=spec['single_descriptor_chain'] if args.mode=='Descriptor' else case['chain']
            prefix='descriptor' if args.mode=='Descriptor' else 'q'
            packet=(HERE/(prefix+'_packet.bin')).read_bytes();golden=(HERE/(prefix+'_golden.bin')).read_bytes()
            values=(np.arange(32*chain['groups']*64,dtype=np.int32)%31-15).astype(np.float32)
            values=(values*np.float32(0.002)).reshape(32,chain['groups']*64)
            if base.pack_chain_input(chain,values,case['base_words'],activation_scale_shift=0)!=packet:raise RuntimeError('Original M238 packing differs')
            layout=ROOT/spec['layout_path']
            if sha256(layout)!=spec['layout_sha256']:raise RuntimeError('Original layout differs')
            variants='ABBABAAB' if args.mode=='Compare' else 'B'
            result['balanced_orders']=['A-B-B-A','B-A-A-B'] if args.mode=='Compare' else []
            result['cache_policy']='Natural current cache; no cache clearing/eviction. File staging/complete SHA outside timed submission-to-completion interval.'
            for index,variant in enumerate(variants):
                label=args.mode.lower()+'-'+str(index)+'-'+variant
                load(variant,label);allocate_owned([case['window_bytes_per_port']]*4+[len(packet),len(golden)],label)
                phase[0]='stage:'+label
                for buffer,window in zip(buffers[:4],case['windows']):
                    path=layout.parent/window['file'];before=identity(path)
                    if before[2]!=window['file_bytes']:raise RuntimeError('Original shard size differs')
                    with path.open('rb',buffering=0) as stream:
                        stream.seek(case['base_words']*16);raw=stream.read(case['window_bytes_per_port'])
                    if identity(path)!=before or len(raw)!=case['window_bytes_per_port'] or hashlib.sha256(raw).hexdigest()!=window['sha256']:raise RuntimeError('Frozen weight window differs')
                    buffer[:len(raw)]=np.frombuffer(raw,np.uint8);buffer.sync_to_device();del raw
                transact(packet,golden,int(chain['config_u32'],16),label,variant);release_all()
            result['numerical_pass']=True
            if args.mode=='Compare':
                import statistics
                rows=result['transactions'];a=[r['wait_ns'] for r in rows if r['variant']=='A'];b=[r['wait_ns'] for r in rows if r['variant']=='B']
                clocks=result['overlay_loads'];same_clocks=all(r['clocks_mhz']==clocks[0]['clocks_mhz'] for r in clocks)
                blocks=[]
                for i in (0,4):
                    block=rows[i:i+4];av=statistics.median(r['wait_ns'] for r in block if r['variant']=='A');bv=statistics.median(r['wait_ns'] for r in block if r['variant']=='B')
                    blocks.append(dict(original_median_ns=av,candidate_median_ns=bv,gain_ns=av-bv))
                ma,mb=statistics.median(a),statistics.median(b)
                result['comparison']=dict(original_ns=a,candidate_ns=b,original_median_ns=ma,candidate_median_ns=mb,
                    gain_fraction=(ma-mb)/ma,balanced_blocks=blocks,same_observed_ps_clocks=same_clocks,
                    boundary='Before S2MM submit through latched AP_DONE plus both DMA idle; staging, packing, output sync/hash and Overlay load excluded',pure_compute=False)
                result['chain_performance_pass']=same_clocks and all(r['gain_ns']>0 for r in blocks) and mb<min(a) and max(b)<min(a)
                if not result['chain_performance_pass']:raise RuntimeError('No separated and consistent balanced single-chain benefit; do not enter full model')
        phase[0]='restore-stable';zero('A','stable-restored-build-id')
        result['stable_restored']=True
        result['final_service']=service_stopped();result['boot_unchanged']=sha256(boot)==boot_before;result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==cmd_before
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected boot identity changed')
        result['status']='PASS_M357_'+args.mode.upper()
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()
        # One bounded rollback only after a proven completed/no-submission
        # lifecycle; an unresolved physical transaction never loads an Overlay.
        if overlay is not None and not active and (not buffers or release_safe()):
            try:
                release_all()
                phase[0]='failure-restore-stable'
                zero('A','failure-stable-restored-build-id')
                result['stable_restored']=True
            except BaseException as restore_error:
                result['errors'].append('Bounded stable restore failed: '+str(restore_error))
    finally:
        unsafe=active or (bool(buffers) and not release_safe())
        if kernel is not None and base is not None:result['final_snapshot']=base.transaction_snapshot(kernel,dma)
        if not unsafe:
            try:release_all()
            except BaseException as exc:unsafe=True;result['errors'].append('Cleanup unresolved: '+str(exc))
        result['unsafe_dma_buffers_retained']=unsafe;result['safe_buffers_released']=not unsafe
        if unsafe:result['status']='FAIL_UNSAFE_RETAINED'
        result['gate_return_code']=0 if result['status']=='PASS_M357_'+args.mode.upper() else 1
        if result['gate_return_code']:
            transaction=result.get('active_transaction',{})
            snap=result.get('final_snapshot',{})
            result['failure_diagnostics']=dict(mode=args.mode,phase=phase[0],
                chain_identity='minimal-zero' if args.mode=='BuildID' else 'original-layer0:q',
                transaction_label=transaction.get('label'),config=transaction.get('config'),
                input_bytes=transaction.get('input_bytes'),output_bytes=transaction.get('output_bytes'),
                ap_ctrl=snap.get('ap_ctrl'),ap_return=snap.get('ap_return'),
                mm2s_dmasr=snap.get('mm2s_dmasr'),s2mm_dmasr=snap.get('s2mm_dmasr'),
                gate_return_code=1,unsafe_dma_buffers_retained=unsafe)
            print('M357_FAILURE_STATUS '+json.dumps(result['failure_diagnostics']),flush=True)
        write_json(directory/'BOARD_RESULT.json',result);stopped.set()
        print('M357_RESULT_SAVED status='+result['status'],flush=True)
        if unsafe:
            from m357_export_result import emit_saved
            emit_saved(args.mode)
            print('M357_RETAIN_PROCESS_OVERLAY_AND_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return result['gate_return_code']

if __name__=='__main__':raise SystemExit(main())
