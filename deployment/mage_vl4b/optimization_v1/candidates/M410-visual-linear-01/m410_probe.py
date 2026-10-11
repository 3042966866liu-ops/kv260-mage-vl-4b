"""Unchanged parallel Build: one visual descriptor/chain, full saved-wire comparison."""
import argparse,fcntl,json,os,subprocess,sys,threading,time,traceback
from pathlib import Path
import numpy as np
from measurement import sha256,write_json
from owned_buffer_release import OwnedBufferRelease
from board_safety import safe_to_release
from m341_build_id_gate import verify_self,service_stopped,STABLE,STABLE_SHA,ROOT
from m120_board_common import KERNEL_NAME,DMA_NAME
from m357_completion_observer import wait_observed
from m410_saved_case import load_case

HERE=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ubuntu/m410_visual_linear_01')

def meminfo():
    d={}
    for s in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
        key=s.split(':')[0]
        if key in ('CmaFree','MemAvailable','Cached'):d[key]=int(s.split()[1])*1024
    if len(d)!=3:raise RuntimeError('Actual memory counters missing')
    return d

class Owner:
    def __init__(self,base,result):
        self.base,self.result=base,result;self.kernel=self.dma=self.overlay=None
        self.expected=None;self.active=False;self.ever=False;self.completed=False;self.buffers=[]
    def safe(self):
        if self.active or self.kernel is None:return False
        s=self.base.transaction_snapshot(self.kernel,self.dma)
        if any(s.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
        if self.ever:return self.completed and safe_to_release(s) and s['ap_return']==self.expected
        return s.get('ap_ctrl')==4 and s.get('ap_return')==0 and s.get('mm2s_dmasr')==s.get('s2mm_dmasr')==0 and s.get('mm2s_error') is False and s.get('s2mm_error') is False
    def memory(self,label):
        row=dict(label=label,**meminfo(),required_cma_free_bytes=64<<20);self.result['memory'].append(row)
        if row['CmaFree']<64<<20:raise MemoryError('Allocated real CMA reserve below64MiB')
        if row['MemAvailable']<128<<20:raise MemoryError('PS memory and retained64MiB reserve insufficient')
    def allocate(self,sizes,label):
        from pynq import allocate
        for size in sizes:
            b=allocate((size,),dtype=np.uint8);self.buffers.append(b)
            row=dict(label=label,bytes=int(b.nbytes),address=int(self.base.physical_address(b)));self.result['allocations'].append(row)
            b.freebuffer=OwnedBufferRelease(b.freebuffer,self.safe,lambda row=row:self.result['releases'].append(row))
            if row['address']+size>self.base.LOW_END:raise RuntimeError('Original low DDR ABI exceeded')
        self.memory('allocated:'+label)
    def release(self):
        while self.buffers:self.buffers[-1].freebuffer();self.buffers.pop()
    def load(self,path,digest,build,label):
        if self.active or self.buffers:raise RuntimeError('Owned buffers/active DMA before Overlay change')
        r=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(path),
            '--expected-package-manifest-sha256',digest,'--result',str(EVIDENCE/self.result['gate_level']/(label+'_environment.json'))],timeout=90)
        if r.returncode:raise RuntimeError('Fixed root/XRT/TMPDIR/PATH/device/package environment rejected')
        from pynq import Overlay,Clocks
        self.overlay=Overlay(str(path/'overlay/m120_m89x2_t32.bit'),download=True)
        self.kernel,self.dma=getattr(self.overlay,KERNEL_NAME),getattr(self.overlay,DMA_NAME)
        self.expected=build;self.ever=self.completed=False
        self.result['overlay_loads'].append(dict(label=label,build_id=hex(build),bit_sha256=sha256(path/'overlay/m120_m89x2_t32.bit'),clocks_mhz={str(i):float(getattr(Clocks,'fclk'+str(i)+'_mhz')) for i in range(4)}))
    def transact(self,packet,golden,config,label):
        bank,tx,rx=self.buffers[:4],self.buffers[4],self.buffers[5]
        tx[:len(packet)]=np.frombuffer(packet,np.uint8);tx.sync_to_device();rx[:len(golden)]=0xa5;rx.sync_to_device()
        self.memory('before-submit:'+label)
        for reg,b in zip(self.base.REG_POINTERS,bank):self.base.write_u64(self.kernel,reg,self.base.physical_address(b))
        self.kernel.write(self.base.REG_CONFIG,config)
        row=dict(label=label,build_id=hex(self.expected),input_bytes=len(packet),output_bytes=len(golden),config=hex(config),packet_sha256=__import__('hashlib').sha256(packet).hexdigest(),expected_sha256=__import__('hashlib').sha256(golden).hexdigest())
        self.result['active_transaction']=row;self.active=self.ever=True;self.completed=False
        self.result['physical_transactions_started']+=1;start=time.monotonic_ns()
        self.dma.recvchannel.transfer(rx,nbytes=len(golden));self.kernel.write(self.base.REG_AP_CTRL,1);self.dma.sendchannel.transfer(tx,nbytes=len(packet))
        try:s,observed=wait_observed(lambda:self.base.transaction_snapshot(self.kernel,self.dma),start,timeout_s=10.,expected_build_id=self.expected)
        except BaseException as exc:
            row['observation_failure']=getattr(exc,'evidence',str(exc));self.result['transactions'].append(row);raise
        if not safe_to_release(s):raise RuntimeError('Completed DMA/kernel state unsafe')
        self.active=False;self.completed=True;rx.sync_from_device();raw=bytes(memoryview(rx)[:len(golden)])
        row.update(completed_snapshot=s,wait_ns=observed['wait_ns'],full_output_exact=raw==golden,output_sha256=__import__('hashlib').sha256(raw).hexdigest())
        self.result['transactions'].append(row)
        if raw!=golden:raise RuntimeError('Complete original FTZ wire output differs')
        print('M410_TRANSACTION_COMPLETE '+json.dumps(dict(label=label,full_output_exact=True,wait_ms=row['wait_ns']/1e6)),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('mode',choices=('Descriptor','Chain'));ap.add_argument('--enable-visual-linear-gate',action='store_true');ap.add_argument('--prior-sha');a=ap.parse_args()
    if not a.enable_visual_linear_gate:raise RuntimeError('Default-off visual gate')
    directory=EVIDENCE/a.mode
    if directory.exists():raise RuntimeError('Original attempt exists; Collect only')
    directory.mkdir(parents=True,mode=0o700)
    result=dict(status='FAIL_M410_'+a.mode.upper(),gate_return_code=1,gate_level=a.mode,build_id='0x4D333537',manifest_sha256=a.manifest_sha,
        errors=[],transactions=[],memory=[],allocations=[],releases=[],overlay_loads=[],physical_transactions_started=0,
        numerical_pass=False,performance_pass=False,full_model=False,video=False,promoted=False)
    owner=lock=None;stopped=threading.Event();phase=['package']
    def beat():
        while not stopped.wait(30):print('M410_HEARTBEAT '+a.mode+' '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        verify_self(HERE,a.manifest_sha);result['package_verified']=True
        if os.geteuid()!=0:raise RuntimeError('Root required')
        spec=json.loads((HERE/'BOARD_CASES.json').read_bytes())
        for row in spec['stable_sources']:
            if sha256(ROOT/row['path'])!=row['sha256']:raise RuntimeError('Frozen stable runtime source differs')
        result['stable_sources_verified']=len(spec['stable_sources'])
        closure=json.loads((HERE/'HARDWARE_CLOSURE.json').read_bytes())
        if closure['status']!='PASS_ALL_NEW_CIRCUIT_PREREQUISITES' or closure['build_id']!='0x4D333537' or not closure['original_source_closure_unchanged']:raise RuntimeError('Unchanged circuit evidence rejected')
        result['hardware_closure_sha256']=sha256(HERE/'HARDWARE_CLOSURE.json')
        if a.mode=='Chain':
            p=EVIDENCE/'Descriptor/BOARD_RESULT.json'
            if not a.prior_sha or sha256(p)!=a.prior_sha:raise RuntimeError('Prior descriptor raw identity differs')
            previous=json.loads(p.read_bytes())
            if previous['status']!='PASS_M410_DESCRIPTOR' or previous['gate_return_code']:raise RuntimeError('Prior descriptor rejected')
            result['prior_raw_sha256']=a.prior_sha
        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base
        if Path(base.__file__).resolve()!=(STABLE/'runtime/board_runtime.py').resolve():raise RuntimeError('Stable actual runtime resolution differs')
        chain,packet,golden,windows,result['saved_reference']=load_case(spec,a.mode,ROOT,base)
        zero_packet=(HERE/'build_packet.bin').read_bytes();zero_golden=(HERE/'build_golden.bin').read_bytes()
        result['initial_service']=service_stopped()
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_before=sha256(boot);cmd_before=Path('/proc/cmdline').read_text(encoding='utf-8')
        owner=Owner(base,result)
        def zero(path,digest,build,label):
            phase[0]=label;owner.load(path,digest,build,label);owner.allocate([144]*4+[len(zero_packet),len(zero_golden)],label)
            for b in owner.buffers[:4]:b[:]=0;b.sync_to_device()
            owner.transact(zero_packet,zero_golden,int(spec['build_config'],16),label);owner.release()
        def restore():
            zero(STABLE,STABLE_SHA,0x4d395832,'stable-restored-build-id');result['stable_restored']=True
        zero(Path(spec['hardware_directory']),spec['hardware_manifest_sha256'],0x4d333537,'candidate-legal-build-id')
        phase[0]='visual-'+a.mode
        owner.allocate([chain['stage_bytes_per_shard']]*4+[len(packet),len(golden)],'visual')
        for b,w in zip(owner.buffers[:4],windows):b[:len(w)]=np.frombuffer(w,np.uint8);b.sync_to_device()
        owner.transact(packet,golden,int(chain['config'],16),'visual-'+a.mode.lower());owner.release()
        result['numerical_pass']=True;restore()
        result['final_service']=service_stopped();result['boot_unchanged']=sha256(boot)==boot_before;result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==cmd_before
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected boot/cmdline changed')
        result['status']='PASS_M410_'+a.mode.upper()
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc));result['traceback']=traceback.format_exc()
        if owner is not None and owner.overlay is not None and not owner.active and (not owner.buffers or owner.safe()):
            try:owner.release();restore()
            except BaseException as error:result['errors'].append('Bounded stable restore failed: '+str(error))
    finally:
        unsafe=owner is not None and (owner.active or (bool(owner.buffers) and not owner.safe()))
        if owner is not None and owner.kernel is not None:result['final_snapshot']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
        if owner is not None and not unsafe:
            try:owner.release()
            except BaseException as exc:unsafe=True;result['errors'].append('Cleanup unresolved: '+str(exc))
        result['unsafe_dma_buffers_retained']=unsafe;result['safe_buffers_released']=not unsafe
        if unsafe:result['status']='FAIL_UNSAFE_RETAINED'
        result['gate_return_code']=0 if result['status']=='PASS_M410_'+a.mode.upper() else 1
        result['failure_diagnostics']=dict(phase=phase[0],chain=locals().get('chain',{}).get('module'),transaction=result.get('active_transaction'),snapshot=result.get('final_snapshot'),gate_return_code=result['gate_return_code'])
        write_json(directory/'BOARD_RESULT.json',result);stopped.set()
        print('M410_RESULT_SAVED '+result['status'],flush=True)
        if unsafe:
            from m410_export import emit_saved
            emit_saved(a.mode);print('M410_RETAIN_PROCESS_OVERLAY_AND_ALL_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return result['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
