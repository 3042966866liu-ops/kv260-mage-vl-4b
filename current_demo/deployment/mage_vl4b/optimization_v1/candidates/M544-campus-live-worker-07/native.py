"""Current22 complete fixed V2 request and first-token comparison. Explicit full constructor.

Seven original capacity owners are genuinely constructed and bound before any
submission. Partial construction and uncertain device access retain this scope.
"""
import argparse,importlib.util,threading,base64,hashlib,json,os,subprocess,sys,time,traceback,zlib
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

def metadata_reference(path=Path('/usr/local/share/pynq-venv/lib/python3.10/site-packages/pynq/pl_server/global_pl_state.json')):
    if not path.exists():
        return dict(global_state_absent=True)
    value = read(path)
    bit = Path(value['bitfile_name'])
    assert bit.is_absolute() and bit.is_file(), 'PYNQ cache references a missing bitfile; stop before Overlay'
    assert hashlib.sha1(bit.read_bytes()).hexdigest() == value['bitfile_hash'], 'PYNQ cached bitfile hash differs'
    return dict(global_state_absent=False, global_state_sha256=sha(path), bitfile=str(bit), bitfile_sha256=sha(bit))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('mode',choices=('Request',))
    ap.add_argument('--enable-saved-fixture-gate',action='store_true');ap.add_argument('--prior-sha');ap.add_argument('--component-manifest-sha',required=True);ap.add_argument('--demo-manifest-sha',required=True);args=ap.parse_args()
    if not args.enable_saved_fixture_gate:raise RuntimeError('Disabled by default')
    own=Path(__file__).resolve().parent
    assert sha(own/'PACKAGE_MANIFEST.json')==args.demo_manifest_sha
    component=Path('/dev/shm/m523_PS3072_ttft_package01');here=Path('/dev/shm/m523_M455_twentytwo_local_package322');sys.path[:0]=[str(own),str(component),str(here),str(here/'runtime')]
    from m341_build_id_gate import verify_self,service_stopped
    from m455_configuration_retry02 import Configuration,read_counts
    from m455_board_clocks03 import ClockGuard,validate_operating
    from m455_completion_observer import wait_observed
    from b0_owners523 import Owners
    from owned_buffer_release import OwnedBufferRelease
    from b0_transaction_guard523 import finalize_guard
    from board_safety import safe_to_release
    from memory_lifecycle import memory_snapshot
    import board_runtime as base
    import numpy as np
    session=os.environ['CAMPUS_SESSION_ID'];assert len(session)==32 and all(c in '0123456789abcdef' for c in session)
    root=Path('/home/ubuntu/tellme_results/m544_live_sessions')/session;out=root/args.mode
    assert not out.exists();out.mkdir(parents=True,mode=0o700)
    state=Lifecycle();ledger=configuration=clocks=runtime=overlay=lock=constructor=assembly=engine=request_context=None
    result=dict(status='FAIL_M455_COMPLETE_ENGINE_'+args.mode.upper(),primary_rc=1,mode=args.mode,
        manifest_sha256=args.manifest_sha,transactions=[],errors=[],models=0,model_forwards=0,
        build_id='0x4D343535',unsafe_retained=False,seven_owner_sizes=list(SIZES),memory=[],
        software_delta_manifest_sha256=args.demo_manifest_sha,software_delta_native_sha256=sha(__file__),
        full_model=False,task_quality=False,performance_pass=False)
    def snap():
        actual=runtime if runtime is not None else constructor.runtime
        return base.transaction_snapshot(actual.kernel,actual.dma)
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
        verify_self(component,args.component_manifest_sha);verify_self(here,args.manifest_sha);assert os.geteuid()==0
        plan=read(here/'PLAN.json');assert plan['scope']=='M455_TWENTYTWO_SAVED_44_CHAIN_AND_22_LOCAL_LAYER_ONLY'
        cp=read(component/'CONSTRUCTOR_PLAN.json');assert sha(component/'CSIM_RESULT.json')==cp['CSim_sha256']
        assert read(component/'CSIM_RESULT.json')['status']=='PASS_M455_ADAPTIVE_SIX_VECTOR_CSIM_ONLY'
        csim=here/'NUMERICAL_44_RESULT.json';assert sha(csim)==plan['CSim44_sha256']
        assert read(csim)['status']=='PASS_ORIGINAL_TWENTYTWO_44_FAMILY_NUMERICAL_CSIM_NOT_BOARD'
        assert read(csim)['original_launcher_rc']==0 and len(read(csim)['cases'])==44
        five=here/'NUMERICAL_5_RESULT.json';assert sha(five)==plan['CSim5_sha256']
        assert read(five)['status']=='PASS_FIVE_ACTUAL_A53_PACKET_NUMERICAL_CSIM_NOT_BOARD' and read(five)['original_rc']==0
        for row in plan['hardware_evidence']:
            assert sha(here/row['path'])==row['sha256']
        request_plan=read(component/'REQUEST_PLAN.json')
        repaired=Path(request_plan['CMA_retry_gate_path']);assert sha(repaired)==request_plan['CMA_retry_gate_sha256']==sha(component/'CMA_RETRY_BUILD_RESULT.json')
        rg=read(repaired);assert rg['primary_rc']==0 and rg['safe_cleanup_complete'] and not rg['unsafe_retained']
        assert rg['clock_initial']==rg['clock_final'] and rg['releases']==list(reversed(rg['allocations']))
        result['configuration_retry_BuildID_sha256']=sha(repaired)

        # User's actual-input limit is enforced before Overlay/owner/model construction.
        assert len(request_plan['token_ids'])==128 and (len(request_plan['token_ids'])+31)//32==4
        assert request_plan['token_ids'].count(151655)==98 and request_plan['generation_cap']==32
        assert sha(component/'TASK_CONTRACT.json')==request_plan['task_contract_sha256']
        task_contract=read(component/'TASK_CONTRACT.json')
        assert task_contract['token_ids']==request_plan['token_ids'] and task_contract['generation_cap_tokens']==32
        assert request_plan['hardware_layout']['build_id']=='0x4D343535'
        assert request_plan['hardware_layout']['visual_PL_layers']==list(range(13,24))
        assert request_plan['hardware_layout']['logical_visual_chains']==286
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==request_plan['expected_boot']
        prior_layer=Path('/dev/shm/m544_freshboot_current22_evidence05/Layer/BOARD_RESULT.json')
        assert sha(prior_layer)==request_plan['actual_layer_sha256'];prior=read(prior_layer)
        assert prior['primary_rc']==0 and prior['safe_cleanup_complete'] and not prior['unsafe_retained'] and prior['status']=='PASS_M455_TWENTYTWO_SAVED_LAYER' and prior['local_PS']['local_layers_completed']==22
        recovery=read(component/'RECOVERY_EXIT_RESULT.json')
        assert sha(component/'RECOVERY_EXIT_RESULT.json')==request_plan['recovery_exit_sha256']
        assert recovery['execution_lock_available'] and recovery['primary_rc']==0
        assert request_plan['candidate_hardware_layout']==dict(visual_PL_layers=list(range(13,24)),logical_visual_chains=286)
        assert request_plan['new_full_model_forwards_budget']==6 and not request_plan['full_feature_gate_pass']
        for mode in ('BuildID','Descriptor','Chain'):
            gate=Path('/dev/shm/m523_PS3072_minimal_evidence01')/mode/'BOARD_RESULT.json'
            lower_result=read(gate)
            assert lower_result['primary_rc']==0 and lower_result['safe_cleanup_complete'] and not lower_result['unsafe_retained']
        assert read(Path('/dev/shm/m523_PS3072_ttft_import01/Import/BOARD_RESULT.json'))['primary_rc']==0
        assets=Path(request_plan['assets_root']);verify_self(assets,request_plan['assets_manifest_sha256'])
        asset_plan=read(assets/'PLAN.json')
        release=Path('/home/ubuntu/tellme_release_install_20260926')
        for row in cp['asset_metadata']:
            path=release/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
        spec=importlib.util.spec_from_file_location('_m523_real_ctor_loader',component/'m455_private_runtime_loader01.py')
        loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
        factory=loader.load_private(component/'private_runtime',cp['private_manifest_sha256'],namespace='_m455_gateup_native_20261024_02')
        from M455_owned_constructor52301 import OwnedConstructor
        result.update(scope='Real original full M238 constructor, zero DMA/model',CSim_sha256=cp['CSim_sha256'])
        result['initial_service']=service_stopped()
        import fcntl
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg')
        protected=dict(boot=sha(boot),cmdline=Path('/proc/cmdline').read_text(),stable_bit=sha(STABLE/'overlay/m120_m89x2_t32.bit'))
        assert protected['stable_bit']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'
        result['protected_initial']=protected
        result['metadata_reference_preflight']=metadata_reference()
        environment(here,args.manifest_sha,'candidate')
        from pynq import Overlay,Clocks,allocate
        clocks=ClockGuard(Clocks);result['clock_initial']=clocks.snapshot()
        configuration=Configuration(here/'CONFIGURATION_APPLICATION.json',args.manifest_sha,out)
        cache_admitted=False
        def eligible():
            nonlocal cache_admitted
            assert state.programmed and not configuration.unknown and not state.ever
            validate_operating(clocks.snapshot());i=len(ledger.buffers)
            if i==0 and not cache_admitted:
                s=snap();assert s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0
                assert all(s[k]=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
                assert all(int((runtime if runtime is not None else constructor.runtime).dma.mmio.read(o))==0 for o in (0x18,0x1c,0x28,0x48,0x4c,0x58))
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
        import pynq
        def admit_overlay():
            assert os.geteuid()==0 and not state.programmed and not state.programming and not ledger.buffers
            subprocess.run(['sudo','-n','true'],check=True,timeout=5)
        constructor=OwnedConstructor(factory,pynq,np,ledger,state,configuration,clocks,result,admit_overlay)
        # Keep native safety helper objects strongly referenced. Ordinary
        # release runtime slots must match the original M455 engine bootstrap.
        closure=read(component/'SOURCE_CLOSURE.json')
        for row in closure['files']:
            f=release/row['path'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
        assert sha(release/'INSTALL_PACKAGE_MANIFEST.json')=='fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e'
        prior=read(component/'PRIOR_IMPORT_AUDIT.json')
        sys.path[:0]=[str(release/d) for d in closure['module_dirs']]
        for name in ('board_runtime','contract_runtime','reserved_ddr_pool','m230_prefill_runtime','m231_prefill_runtime','m236_prefill_runtime','m238_prefill_runtime'):
            sys.modules.pop(name,None)
        import torch,transformers,tokenizers
        for name in ('torch','transformers','tokenizers'):
            module=sys.modules[name];expected=prior['imports'][name]
            assert str(Path(module.__file__).resolve())==expected['path'] and module.__version__==expected['version'] and sha(module.__file__)==expected['init_sha256']
        torch.set_num_threads(4);torch.set_num_interop_threads(1)
        import m276_video_runtime as video,m243_video_server as language_module,m222_video_server as vision_module,video_server
        for name in ('m276_video_runtime','m243_video_server','m222_video_server','m241_video_language_runtime','m273_latest_vision_runtime'):
            path=Path(sys.modules[name].__file__).resolve();expected=release/closure['modules'][name]
            assert path==expected.resolve(),name
        from M455_engine_assembly52301 import EngineAssembly
        base=factory['base']
        config=video_server.make_config(release/'deployment/mage_vl4b/m181_m120_video_board_candidate',STABLE,
            release/'external_assets/weights',release/'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        def admit_engine():
            assert not state.programmed and not state.programming and not ledger.buffers and not configuration.unknown
        assembly=EngineAssembly(engine_class=video.M276ShortPromptBinaryRuntime,language_module=language_module,vision_module=vision_module,
            constructor=constructor,candidate_bit=here/'overlay/m120_m89x2_t32.bit',expected_original_bit=STABLE/'overlay/m120_m89x2_t32.bit',admit=admit_engine,result=result)
        heartbeat_stop=threading.Event()
        def heartbeat():
            while not heartbeat_stop.wait(30):print('M523_COMPLETE_CONSTRUCTOR_HEARTBEAT full_engine_load_no_forward',flush=True)
        threading.Thread(target=heartbeat,daemon=True).start()
        began=time.monotonic_ns()
        try:engine=assembly.load(config)
        finally:heartbeat_stop.set()
        runtime=constructor.runtime;overlay=runtime.overlay
        assert state.initialized and constructor.returned and assembly.returned and not state.unsafe() and safe()
        assert len(runtime.language_contract.chains)==154 and len(runtime.head_contract.chains)==8
        assert engine.board is runtime and engine.language.runtime is runtime
        assert type(engine.vision).__name__=='M273LatestPSVisionRuntime' and type(engine.language).__name__=='M241VideoLanguageModel'
        result.update(real_complete_engine_constructor_wall_ns=time.monotonic_ns()-began,language_chains=154,head_chains=8,
            actual_full_engine_constructed=True,full_model_constructed=True,actual_board_constructor_returned=constructor.returned,
            engine_class=type(engine).__name__,vision_class=type(engine.vision).__name__,language_class=type(engine.language).__name__,
            model_forwards=0,original_runtime_evidence=runtime.evidence())
        # This is a new complete request process, not a repeat constructor-only gate.
        sys.path[:0]=[str(component),str(assets/'reference')]+[row['directory'] for row in asset_plan['visual_reused_packages']]
        from board_demo_trial import FixedDemoTrial
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from compact_log_output import LogBudget
        import board_demo_trial as timing_module
        budget=LogBudget(out,timing_module.save,result,limit=read(own/'DEMO_BOARD_PLAN.json')['diagnostic_limit_bytes'])
        timing_module.save=budget.save

        def wait_canary():return wait_observed(snap,time.monotonic_ns(),expected_build_id=BUILD,timeout_s=10)
        request_context=FixedDemoTrial(component=component,here=here,engine=engine,runtime=runtime,factory=factory,ledger=ledger,state=state,
            clocks=clocks,result=result,out=out,snapshot=snap,safe=safe,wait_observed=wait_canary)
        request_context.run()
        count_plan=read(own/'DEMO_BOARD_PLAN.json');expected_max=count_plan['new_full_forwards_budget']
        assert expected_max==1+count_plan['persistent_worker']['max_live_jobs']
        assert 1<=result['model_forwards']==result['total_prefills_returned']==result['first_token_samples_returned']<=expected_max
        assert result['warmup_correct'] and result['model_forwards']==1+result['live_jobs_returned']
        assert result['input_T32_blocks']==4 and result['decode_calls']==0
        result.update(status='COMPLETE_M544_LIVE_WORKER_NORMAL_STOP_PENDING_AUDIT',primary_rc=0)

    except BaseException:
        if runtime is None and constructor is not None and constructor.runtime is not None:
            runtime=constructor.runtime
        result['errors'].append(traceback.format_exc())
    finally:
        def finish():
            try:
                if state.unsafe() or (configuration and configuration.unknown):raise RuntimeError('Unknown/partial owner retained')
                if request_context is not None:request_context.close()
                if constructor is not None and constructor.returned:
                    def assert_safe():
                        if not safe():raise RuntimeError('Actual constructor idle unproven')
                    if assembly is not None and assembly.board_returned:assembly.restore_bindings(assert_safe)
                    constructor.restore_patches(assert_safe)
                if ledger is not None:ledger.release_all()
                if engine is not None and engine.vision is not None:engine.vision.close()
                if state.programmed:
                    environment(STABLE,STABLE_SHA,'restore')
                    state.restoring=True
                    from b0_configuration_retry02 import Configuration as StableConfiguration
                    restore_dir=out/'stable_configuration';restore_dir.mkdir()
                    stable_configuration=StableConfiguration(here/'STABLE_CONFIGURATION_APPLICATION.json',STABLE_SHA,restore_dir)
                    stable=stable_configuration.load(STABLE/'overlay/m120_m89x2_t32.bit',Overlay)
                    runtime.kernel=stable.mage_m120_m89x2_0;runtime.dma=stable.axi_dma_prefill
                    s=snap();assert s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0
                    assert all(s[k]=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
                    clocks.normalize();state.restoring=False;result['stable_restored_snapshot']=s
                    result['stable_configuration_record']=stable_configuration.record
                if clocks is not None:
                    clocks.restore();result['clock_final']=clocks.snapshot();assert result['clock_final']==result['clock_initial']
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
