"""Independent M455 saved-fixture lower gate. No model constructors or inference.

Seven original capacity owners are genuinely constructed and bound before any
submission. Partial construction and uncertain device access retain this scope.
"""
import argparse,base64,hashlib,json,os,subprocess,sys,time,traceback,zlib
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True

SIZES=(6963200,)*4+(389152,2621440,2621440)
BUILD=0x4D343535
STABLE=Path('/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m175_m120_fixed_text_candidate')
STABLE_SHA='406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())

class Lifecycle:
    """Honest new ownership state, independent of any previous runtime."""
    def __init__(self):
        self.programming=False;self.programmed=False;self.initialized=False
        self.active=False;self.completed=False;self.ever=False;self.latched=False
        self.restoring=False
    def unsafe(self):
        return bool(self.programming or self.restoring or self.latched or self.active
                    or (self.programmed and not self.initialized))
    def admit_seven(self,ledger,runtime):
        ledger.verify_full(runtime)
        if not self.programmed or self.programming or self.ever or self.active:
            raise RuntimeError('Seven actual idle bindings required')
        self.initialized=True
    def before_submit(self):
        if self.unsafe() or not self.initialized:raise RuntimeError('Unresolved ownership')
        self.active=True;self.ever=True;self.completed=False
    def after_submit(self,snapshot,predicate):
        if not predicate(snapshot) or snapshot.get('ap_return')!=BUILD:
            raise RuntimeError('Actual completed DMA state required')
        self.active=False;self.completed=True

def persist(p,v):
    raw=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode();part=p.with_suffix('.partial')
    with part.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    assert not p.exists();os.rename(part,p)

def emit(p):
    raw=p.read_bytes();assert 0<len(raw)<=4<<20
    encoded=zlib.compress(raw,9)
    print('M523_SHAPE_RAW_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M523_SHAPE_Z_SHA256='+hashlib.sha256(encoded).hexdigest(),flush=True)
    parts=[encoded[i:i+480] for i in range(0,len(encoded),480)]
    for i,b in enumerate(parts):
        print('M523_SHAPE_Z_PART='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)

def retain():
    print('M523_M455_P1_RETAIN_PROCESS_LOCK_OVERLAY_ALL_OWNERS',flush=True)
    while True:
        try:time.sleep(30)
        except BaseException:pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('mode',choices=('BuildID','Descriptor','Chain'))
    ap.add_argument('--enable-saved-fixture-gate',action='store_true');ap.add_argument('--prior-sha');args=ap.parse_args()
    if not args.enable_saved_fixture_gate:raise RuntimeError('Disabled by default')
    here=Path(__file__).resolve().parent;sys.path[:0]=[str(here),str(here/'runtime')]
    from m341_build_id_gate import verify_self,service_stopped
    from m455_configuration01 import Configuration,read_counts
    from m455_board_clocks03 import ClockGuard,validate_operating
    from m455_completion_observer import wait_observed
    from b0_owners523 import Owners
    from owned_buffer_release import OwnedBufferRelease
    from b0_transaction_guard523 import finalize_guard
    from board_safety import safe_to_release
    from memory_lifecycle import memory_snapshot
    import board_runtime as base
    import numpy as np
    root=Path('/dev/shm/m523_M455_P1_shape01_evidence');out=root/args.mode
    assert not out.exists();out.mkdir(parents=True,mode=0o700)
    state=Lifecycle();ledger=configuration=clocks=runtime=overlay=lock=None
    result=dict(status='FAIL_M455_P1_SAVED_'+args.mode.upper(),primary_rc=1,mode=args.mode,
        manifest_sha256=args.manifest_sha,transactions=[],errors=[],models=0,model_forwards=0,
        build_id='0x4D343535',unsafe_retained=False,seven_owner_sizes=list(SIZES),memory=[],
        full_model=False,task_quality=False,performance_pass=False)
    def snap():return base.transaction_snapshot(runtime.kernel,runtime.dma)
    def safe():
        if state.unsafe() or runtime is None or (ledger and ledger.allocating_unknown):return False
        s=snap()
        if any(s.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
        if state.ever:return state.completed and safe_to_release(s) and s['ap_return']==BUILD
        return s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0
    def must_retain():
        return bool(state.unsafe() or (configuration and configuration.unknown)
            or (ledger and (ledger.allocating_unknown or any(h.state!='released' for h in ledger.hooks)))
            or (clocks and clocks.changed))
    def environment(target,digest,label):
        subprocess.run(['sudo','-n','true'],check=True,timeout=5)
        subprocess.run([sys.executable,'-B',str(here/'m120_board_env_preflight.py'),
            '--candidate',str(target),'--expected-package-manifest-sha256',digest,
            '--result',str(out/(label+'_environment.json'))],check=True,timeout=90)
    try:
        verify_self(here,args.manifest_sha);assert os.geteuid()==0
        plan=read(here/'PLAN.json');assert plan['scope']=='M455_P1_SAVED_FIXTURE_LOWER_ONLY'
        csim=here/'P1_CSIM_RESULT.json';assert sha(csim)==plan['CSim_sha256']
        assert read(csim)['status']=='PASS_M455_P1_NEW_FIXTURE_NUMERIC_CSIM_ONLY'
        for row in plan['hardware_evidence']:
            assert sha(here/row['path'])==row['sha256']
        if args.mode!='BuildID':
            prior_mode=('BuildID','Descriptor')[('Descriptor','Chain').index(args.mode)]
            prior=root/prior_mode/'BOARD_RESULT.json';v=read(prior)
            assert args.prior_sha and sha(prior)==args.prior_sha
            assert v['status']=='PASS_M455_P1_SAVED_'+prior_mode.upper() and v['primary_rc']==0
            assert v['safe_cleanup_complete'] and not v['unsafe_retained']
            result['prior_sha256']=args.prior_sha
        result['initial_service']=service_stopped()
        import fcntl
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg')
        protected=dict(boot=sha(boot),cmdline=Path('/proc/cmdline').read_text(),stable_bit=sha(STABLE/'overlay/m120_m89x2_t32.bit'))
        assert protected['stable_bit']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'
        result['protected_initial']=protected
        environment(here,args.manifest_sha,'candidate')
        from pynq import Overlay,Clocks,allocate
        clocks=ClockGuard(Clocks);result['clock_initial']=clocks.snapshot()
        configuration=Configuration(here/'CONFIGURATION_APPLICATION.json',args.manifest_sha,out)
        state.programming=True
        overlay=configuration.load(here/'overlay/m120_m89x2_t32.bit',Overlay)
        state.programmed=True;state.programming=False
        runtime=SimpleNamespace(kernel=overlay.mage_m120_m89x2_0,dma=overlay.axi_dma_prefill,
            maximum_weight_window_bytes=SIZES[0])
        clocks.normalize();result['configuration_record']=configuration.record
        cache_admitted=False
        def eligible():
            nonlocal cache_admitted
            assert state.programmed and not configuration.unknown and not state.ever
            validate_operating(clocks.snapshot());i=len(ledger.buffers)
            if i==0 and not cache_admitted:
                s=snap();assert s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0
                assert all(s[k]=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
                assert all(int(runtime.dma.mmio.read(o))==0 for o in (0x18,0x1c,0x28,0x48,0x4c,0x58))
                floor=sum((n+4095)//4096*4096 for n in SIZES)+(64<<20)
                before=memory_snapshot();counts=read_counts();reclaimed=0
                if before['system_bytes']['CmaFree']<floor:
                    os.sync()
                    with open('/proc/sys/vm/drop_caches','w') as f:f.write('1\n');f.flush()
                    reclaimed=1
                after=memory_snapshot();assert read_counts()==counts
                result['cache_admission']=dict(before=before,after=after,reclaim_calls=reclaimed,floor=floor)
                if after['system_bytes']['CmaFree']<floor:raise MemoryError('Seven owners plus original margin unavailable')
                cache_admitted=True
            observed=memory_snapshot();need=(SIZES[i]+4095)//4096*4096
            result['memory'].append(dict(index=i,required_bytes=need,snapshot=observed))
            if observed['system_bytes']['CmaFree']<need:raise MemoryError('Unchanged per-owner CmaFree precheck')
        ledger=Owners(allocate,np.uint8,base.physical_address,eligible,safe,OwnedBufferRelease,result)
        for n in SIZES:ledger.allocate((n,),dtype=np.uint8)
        runtime.staged_buffers=ledger.buffers[:4]
        runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt=ledger.buffers[4:]
        state.admit_seven(ledger,runtime)
        for case in plan['cases'][args.mode]:
            packet=(here/case['packet']).read_bytes();golden=(here/case['golden']).read_bytes()
            assert 0<len(packet)<=SIZES[4] and 0<len(golden)<=SIZES[5]
            stage_start=time.monotonic_ns()
            for b,name in zip(runtime.staged_buffers,case['weights']):
                raw=(here/name).read_bytes();assert len(raw)<=SIZES[0]
                b[:len(raw)]=np.frombuffer(raw,np.uint8);b.sync_to_device()
            runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
            for reg,b in zip(base.REG_POINTERS,runtime.staged_buffers):base.write_u64(runtime.kernel,reg,base.physical_address(b))
            runtime.kernel.write(base.REG_CONFIG,int(case['config'],0));validate_operating(clocks.snapshot())
            row=dict(name=case['name'],input_bytes=len(packet),output_bytes=len(golden),config=case['config'],
                packet_sha256=hashlib.sha256(packet).hexdigest(),golden_sha256=hashlib.sha256(golden).hexdigest(),
                staging_ns=time.monotonic_ns()-stage_start)
            result['transactions'].append(row);state.before_submit();submitted=time.monotonic_ns()
            runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden))
            runtime.kernel.write(base.REG_AP_CTRL,1)
            runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet))
            observed,detail=wait_observed(snap,submitted,expected_build_id=BUILD,timeout_s=10)
            state.after_submit(observed,safe_to_release)
            runtime.output_buffer.sync_from_device();actual=bytes(memoryview(runtime.output_buffer)[:len(golden)])
            row.update(snapshot=observed,observation=detail,output_sha256=hashlib.sha256(actual).hexdigest(),full_output_equal=actual==golden)
            with (out/(case['name']+'_output.bin')).open('xb') as f:f.write(actual);f.flush();os.fsync(f.fileno())
            if actual!=golden:raise RuntimeError('Complete saved golden mismatch')
        result.update(status='PASS_M455_P1_SAVED_'+args.mode.upper(),primary_rc=0)
    except BaseException:result['errors'].append(traceback.format_exc())
    finally:
        def finish():
            try:
                if state.unsafe() or (configuration and configuration.unknown):raise RuntimeError('Unknown/partial owner retained')
                if ledger is not None:ledger.release_all()
                if state.programmed:
                    environment(STABLE,STABLE_SHA,'restore')
                    state.restoring=True
                    from b0_configuration523 import Configuration as StableConfiguration
                    restore_dir=out/'stable_configuration';restore_dir.mkdir()
                    stable_configuration=StableConfiguration(here/'STABLE_CONFIGURATION_APPLICATION.json',STABLE_SHA,restore_dir)
                    stable=stable_configuration.load(STABLE/'overlay/m120_m89x2_t32.bit',Overlay)
                    runtime.kernel=stable.mage_m120_m89x2_0;runtime.dma=stable.axi_dma_prefill
                    s=snap();assert s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0
                    assert all(s[k]=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
                    clocks.normalize();state.restoring=False;result['stable_restored_snapshot']=s
                    result['stable_configuration_record']=stable_configuration.record
                if clocks is not None:clocks.restore();assert clocks.snapshot()==result['clock_initial']
                if 'protected_initial' in result:
                    assert dict(boot=sha(boot),cmdline=Path('/proc/cmdline').read_text(),stable_bit=sha(STABLE/'overlay/m120_m89x2_t32.bit'))==protected
                result['safe_cleanup_complete']=True
                result['final_service']=service_stopped()
            except BaseException:
                state.latched=True;result.update(status='FAIL_M455_P1_RETAINED',primary_rc=1,unsafe_retained=True)
                result['errors'].append(traceback.format_exc())
            if runtime is not None:
                try:result['final_snapshot']=snap()
                except BaseException:
                    state.latched=True;result.update(status='FAIL_M455_P1_RETAINED',unsafe_retained=True,primary_rc=1)
            persist(out/'BOARD_RESULT.json',result);emit(out/'BOARD_RESULT.json')
            if must_retain():retain()
            if lock is not None:os.close(lock)
        finalize_guard(finish,must_retain,retain)
    return result['primary_rc']

if __name__=='__main__':raise SystemExit(main())
