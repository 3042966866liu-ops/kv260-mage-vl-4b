"""Default-off bounded12+13 quality only; three fixed visual calls, no language."""
import argparse,gc,hashlib,importlib.util,json,os,sys,threading,time,traceback,weakref
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m420_combination_visual_01/BOARD_RESULT.json')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_package(folder,expected):
    if digest(folder/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Manifest differs')
    m=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes());names={x['path'] for x in m['files']}
    if {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}!=names|{'PACKAGE_MANIFEST.json'} or len(names)!=m['file_count'] or sum(x['bytes'] for x in m['files'])!=m['total_bytes']:raise RuntimeError('Package closure differs')
    for x in m['files']:
        p=folder/x['path']
        if p.is_symlink() or p.stat().st_size!=x['bytes'] or digest(p)!=x['sha256']:raise RuntimeError('Payload differs')
def proc():
    result={}
    for x in Path('/proc/self/io').read_text().splitlines():
        if x.split(':')[0] in ('read_bytes','rchar'):result[x.split(':')[0]]=int(x.split()[1])
    for x in Path('/proc/meminfo').read_text().splitlines():
        if x.split(':')[0] in ('CmaFree','MemAvailable','Cached'):result[x.split(':')[0]]=int(x.split()[1])*1024
    result['VmRSS']=int(next(x.split()[1] for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')))*1024
    return result
def verify_prerequisites(plan):
    for row in plan['board_prerequisites']:
        p=Path(row['path'])
        if digest(p)!=row['sha256']:raise RuntimeError('Prerequisite SHA differs')
        r=json.loads(p.read_bytes())
        if r['status']!=row['status'] or type(r['gate_return_code']) is not int or r['gate_return_code'] or r['errors'] or not r['stable_restored'] or not r['safe_buffers_released']:raise RuntimeError('Prerequisite status/owner differs')
        if row['local_net_gain'] and not (r['numerical_pass'] and r['performance_pass']):raise RuntimeError('Local net gain missing')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('--enable-combination-quality',action='store_true');a=ap.parse_args()
    if not a.enable_combination_quality:raise RuntimeError('Default-off combination')
    if OUTPUT.parent.exists():raise RuntimeError('Saved attempt exists; Collect only')
    OUTPUT.parent.mkdir(mode=0o700);started=time.monotonic();phase=['source'];stopped=threading.Event()
    r=dict(status='FAIL_M420_COMBINATION_VISUAL',gate_level='layers12-13-full-visual-feature-quality',gate_return_code=1,manifest_sha256=a.manifest_sha,build_id='0x4D333537',errors=[],
        transactions=[],memory=[],PS_checkpoints=[],allocations=[],releases=[],overlay_loads=[],PL_rows=[],staging=[],physical_transactions_started=0,
        selected_layers=[12,13],visual_forward_calls=0,language_forward_calls=0,full_model=False,video=False,promoted=False,expanded_24_layers=False,performance_pass=False,semantic_quality_proven=False,
        numerical_pass=False,feature_quality_pass=False,bindings_restored=False,PS_owner_closed=False,unsafe_dma_buffers_retained=False,safe_buffers_released=True,stable_restored=False,DMA_allocator_restored=False,DMA_sealed_after_main=False)
    owner=runtime=targets=allocator=lock=None;sealed_ids=None;ps_ref=None;all_restored=[]
    def beat():
        while not stopped.wait(30):print('M420_HEARTBEAT '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        if os.geteuid()!=0:raise RuntimeError('Root required')
        verify_package(HERE,a.manifest_sha);plan=json.loads((HERE/'PLAN.json').read_bytes())
        if plan['selected_layers']!=[12,13]:raise RuntimeError('Bounded selection differs')
        for row in plan['reused_packages']:verify_package(Path(row['directory']),row['manifest_sha256'])
        verify_prerequisites(plan);r['prerequisites_verified']=plan['board_prerequisites'];r['package_verified']=True
        sys.path[:0]=[str(HERE)]+[x['directory'] for x in plan['reused_packages']]
        import numpy as np
        import m418_probe as lower
        from m341_build_id_gate import ROOT,STABLE,STABLE_SHA,service_stopped
        from board_safety import safe_to_release
        from m410_saved_case import load_case as load12
        from m418_saved_case import load_case as load13
        from m411_mlp_binding import stage_windows
        from m420_combination import execute
        from m414_policy import POLICY,MemoryBudget,PlannedDMA,verify_owner_buffers
        lower.EVIDENCE=OUTPUT.parent
        ids=json.loads((Path(plan['reference13_package'])/'M348_SOURCE_IDENTITIES.json').read_bytes())
        for row in ids['files']:
            p=ROOT/row['path']
            if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Frozen source identity differs')
        r['source_identities_verified']=len(ids['files'])
        from frozen_video_identity import module_paths,verify_m277_release_subset,FRAMES,ADDON,STACK_SHA
        r['release_subset']=verify_m277_release_subset(ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate');sys.path[:0]=[str(p) for p in module_paths()]
        spec=importlib.util.spec_from_file_location('m420_original_preflight',ROOT/'scripts/preflight.py');preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
        phase[0]='original35asset-preflight';checked=preflight.inspect(json.loads((ROOT/'configs/deployment.example.json').read_bytes()),port_check=True)
        r['release_preflight']={k:checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        if checked['status']!='READY_FOR_BOARD_PREFLIGHT':raise RuntimeError('Original35 checks rejected')
        import torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m273_latest_multiscale_contract import preprocess
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m408_target03 import resolve_target as target12,verify_matrices as matrices12
        from m416_target13 import resolve_target as target13,verify_matrices as matrices13
        from m414_quality import tensor,visual_quality,VisualChecks,save_features
        from m408_mlp_capture04 import compare
        from m406_vision_observer import backend_evidence
        from test_m409_ftz_reference import actual_host
        from m414_entry import run_component
        from m407_mlp_contract import metrics,local_screen
        import contract_runtime
        identities={x['path']:x['sha256'] for x in ids['files']};r['resolved_modules']={}
        for name in plan['resolved_module_names']:
            path=Path(sys.modules[name].__file__).resolve();relative=path.relative_to(ROOT).as_posix()
            if relative not in identities or digest(path)!=identities[relative]:raise RuntimeError('Actual resolved source differs:'+name)
            r['resolved_modules'][name]=dict(path=relative,sha256=identities[relative])
        r['component'],r['component_process']=run_component(ROOT,OUTPUT.parent,HERE/'test_m420_combination.py')
        print('M420_CLEAN_DYNAMIC_COMPONENT_PASS',flush=True)
        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base
        host,initial=actual_host(ROOT);cases={};refs={};specs={}
        for index,loader in ((12,load12),(13,load13)):
            s=json.loads((Path(plan['lower_packages'][str(index)])/'BOARD_CASES.json').read_bytes());specs[index]=s
            c={};w={}
            for mode in ('Descriptor','Chain'):
                chain,_,_,windows,_=loader(s,mode,ROOT,host);part=s['cases'][mode]['part'];c[part]=chain;w[part]=windows
            cases[index]=dict(chains=c,windows=w)
            refs[index]=json.loads((Path(s['reference_directory'])/'RESULT.json').read_bytes())
        frames=[]
        for name,expected in FRAMES.items():
            p=ADDON/'fixtures'/name
            if digest(p)!=expected:raise RuntimeError('Frame SHA differs')
            frames.append(np.load(p,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Ordered source stack differs')
        tensors=preprocess(np.ascontiguousarray(frames[-1:]));del frames
        expected=json.loads((HERE/'EXPECTED_VISUAL.json').read_bytes());r['preprocessed']={k:tensor(v) for k,v in sorted(tensors.items())}
        if r['preprocessed']!=expected['preprocessed']:raise RuntimeError('Fixed two-view preprocess differs')
        r['memory_before_constructor']=proc()
        if r['memory_before_constructor']['MemAvailable']<(1<<30)+(768<<20)+(64<<20):raise MemoryError('Original ordinary constructor budget unavailable')
        phase[0]='PS-constructor';vbase=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime=M273LatestPSVisionRuntime(vbase/'ps_vision_payload',vbase/'vision_layout',vbase/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');ps_ref=weakref.ref(runtime)
        targets={};r['target_resolution']={};r['target_matrices']={}
        for index,resolver,verify in ((12,target12,matrices12),(13,target13,matrices13)):
            layer,topology=resolver(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch);mat=verify(layer,M207FP32GemmW4Linear,torch)
            if topology!=refs[index]['target_resolution'] or mat!=refs[index]['target_matrices']:raise RuntimeError('Selected layer topology/weights differ')
            targets[index]=layer;r['target_resolution'][str(index)]=topology;r['target_matrices'][str(index)]=mat
        layer=None
        from m261_budgeted_w4_runtime import CACHE_NAMES,M261BudgetedFourPortW4Store
        store=targets[12].mlp.fc1.store
        if type(store) is not M261BudgetedFourPortW4Store or any(getattr(targets[i].mlp,k).store is not store or getattr(targets[i].mlp,k).name in CACHE_NAMES for i in targets for k in ('fc1','fc2')):raise RuntimeError('Uncached shared original store differs')
        r['CPU_store_before']=store.evidence();store=None;r['backend_before']=backend_evidence(torch)
        r['memory_after_constructor']=proc();r['admission_policy']=POLICY;budget=MemoryBudget(r['memory_after_constructor'],proc);r['PS_checkpoints'].append(budget.check('after-constructor'))
        import fcntl
        r['initial_service']=service_stopped();lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_before=digest(boot);cmd_before=Path('/proc/cmdline').read_text()
        def vision(mode,**kwargs):
            phase[0]=mode+'-full-visual';r['PS_checkpoints'].append(budget.check('before-'+phase[0]));r['visual_forward_calls']+=1
            with VisualChecks(runtime.vision,budget,r['PS_checkpoints'],phase) as checks:
                answer,captures,ev=execute(torch,lambda:runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions']),targets,cases,initial,host,mode,**kwargs)
            all_restored.extend([checks.restored,ev['bindings_restored'],ev['captures_restored']]);r['PS_checkpoints'].append(budget.check('after-'+phase[0]));return answer,captures,ev
        if owner is not None or allocator is not None or 'pynq' in sys.modules:raise RuntimeError('Original reference must precede resources')
        r['original_reference_before_overlay']=True
        visual_a,cap_a,_=vision('original');r['original_visual']=tensor(visual_a);r['original_captures']={str(i):{k:tensor(v) for k,v in cap_a[i].items()} for i in targets}
        if r['original_visual']!=expected['visual'] or any(r['original_captures'][str(i)]!=refs[i]['capture_tensors'] for i in targets):raise RuntimeError('Fixed original visual/captures differ')
        r['original_reference_pass']=True;print('M420_ORIGINAL_FULL_VISUAL_REFERENCE_PASS',flush=True)
        visual_s,cap_s,software=vision('software')
        r['software_visual']=tensor(visual_s);r['software_captures']={str(i):{k:tensor(v) for k,v in cap_s[i].items()} for i in targets}
        r['software_batches']=software['batches'];r['software_wire_identities']=software['software_wire_identities']
        if any(b['physical_reference_attempts']!=1 for rows in software['batches'].values() for batches in rows.values() for b in batches):raise RuntimeError('Dynamic software retry requires additional raw-attempt evidence; stop before resources')
        r['layer13_input_changed']=r['software_captures']['13']['input']!=r['original_captures']['13']['input']
        print('M420_DYNAMIC_COMBINATION_SOFTWARE_REFERENCE_PASS',flush=True)
        # The resource owner below is the already tested M414 transaction lifecycle,
        # with no fixed CMA floor and exactly the same seven DMA payload bytes.
        class WorkOwner(lower.Owner):
            def memory(self,label):
                recovery=self.expected==0x4d395832;row=budget.check(label,recovery=recovery);r['memory'].append(row)
                if sealed_ids is not None and not recovery:verify_owner_buffers(self,sealed_ids)
            def allocate(self,sizes,label):
                nonlocal allocator
                if allocator is None:
                    import pynq
                    allocator=PlannedDMA(pynq,r)
                with allocator.group(sizes,label):lower.Owner.allocate(self,sizes,label)
            def submit(self,index,part,c,start,shift,packet):
                tx=self.buffers[4];rx=self.buffers[5+(len(r['PL_rows'])%2)];tx[:len(packet)]=np.frombuffer(packet,np.uint8);tx.sync_to_device();rx[:c['output_bytes']]=0xa5;rx.sync_to_device();self.memory('MLP-before-submit')
                for reg,b in zip(base.REG_POINTERS,self.buffers[:4]):base.write_u64(self.kernel,reg,base.physical_address(b))
                self.kernel.write(base.REG_CONFIG,int(c['config'],16));self.active=self.ever=True;self.completed=False;r['physical_transactions_started']+=1
                submitted=time.monotonic_ns();r['active_transaction']=dict(layer=index,part=part,start=start,shift=shift,input_bytes=len(packet),output_bytes=c['output_bytes'],config=c['config'])
                self.dma.recvchannel.transfer(rx,nbytes=c['output_bytes']);self.kernel.write(base.REG_AP_CTRL,1);self.dma.sendchannel.transfer(tx,nbytes=len(packet))
                s,observation=lower.wait_observed(lambda:base.transaction_snapshot(self.kernel,self.dma),submitted,timeout_s=10.,expected_build_id=self.expected)
                if not safe_to_release(s):raise RuntimeError('Unproven completed transaction')
                self.active=False;self.completed=True;rx.sync_from_device();raw=bytes(memoryview(rx)[:c['output_bytes']])
                r['PL_rows'].append(dict(layer=index,part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw),completed_snapshot=s,packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()));return raw
        owner=WorkOwner(base,r);lower_case=specs[13];lower_package=Path(plan['lower_packages']['13'])
        zero_packet=(lower_package/'build_packet.bin').read_bytes();zero_raw=(lower_package/'build_golden.bin').read_bytes()
        def zero(path,sha,build,label):
            phase[0]=label;owner.load(path,sha,build,label);owner.allocate([144]*4+[len(zero_packet),len(zero_raw)],label)
            for buf in owner.buffers[:4]:buf[:]=0;buf.sync_to_device()
            owner.transact(zero_packet,zero_raw,int(lower_case['build_config'],16),label);owner.release()
        def restore():zero(STABLE,STABLE_SHA,0x4d395832,'stable-restored-build-id');r['stable_restored']=True
        zero(Path(lower_case['hardware_directory']),lower_case['hardware_manifest_sha256'],0x4d333537,'candidate-legal-build-id')
        owner.allocate([557056]*4+[163856,524288,524288],'completeMLP-seven');sealed_ids=tuple(id(b) for b in owner.buffers);verify_owner_buffers(owner,sealed_ids);r['DMA_sealed_after_main']=True
        def stage(index,part,c):
            rows=specs[index]['cases']['Chain' if part=='fc1' else 'Descriptor']['windows'];row=stage_windows(owner,part,rows,ROOT);row['layer']=index;r['staging'].append(row)
        visual_b,cap_b,pl=vision('PL',stage=stage,submit=owner.submit,expected=software['software_wire'])
        if not np.array_equal(visual_s.view(np.uint32),visual_b.view(np.uint32)) or any(not np.array_equal(cap_s[i][k].view(np.uint32),cap_b[i][k].view(np.uint32)) for i in targets for k in cap_s[i]):raise RuntimeError('Complete dynamic software/PL combination differs')
        r['candidate_visual']=tensor(visual_b);r['candidate_captures']={str(i):{k:tensor(v) for k,v in cap_b[i].items()} for i in targets};r['PL_batches']=pl['batches'];r['full_wire_reference_batches_exact']=52;r['software_PL_complete_features_exact']=True
        r['local_quality']={}
        for i in targets:
            q,passed=compare(cap_a[i],cap_b[i]);r['local_quality'][str(i)]=q
            if not passed:raise RuntimeError('Combination local quality rejected')
        r['full_visual_quality']=visual_quality(visual_a,visual_b);r['feature_quality_pass']=r['full_visual_quality']['feature_screen_pass'];r['retained_visual_features']=save_features(OUTPUT.parent,dict(original=visual_a,candidate=visual_b))
        if not r['feature_quality_pass']:raise RuntimeError('Original final feature threshold rejected')
        r['numerical_pass']=True;r['bindings_restored']=all(all_restored);r['backend_after']=backend_evidence(torch);r['CPU_store_after']=targets[12].mlp.fc1.store.evidence()
        if r['backend_before']!=r['backend_after'] or r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=208:raise RuntimeError('Original backend/store contract differs')
        if time.monotonic()-started>840:raise RuntimeError('Fixed840s quality budget expired; no extra runs')
        owner.release();sealed_ids=None;targets=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None
        if not r['bindings_restored'] or not r['PS_owner_closed']:raise RuntimeError('Owner/context release unproven')
        restore();r['boot_unchanged']=digest(boot)==boot_before;r['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmd_before;r['final_service']=service_stopped()
        if not r['boot_unchanged'] or not r['cmdline_unchanged']:raise RuntimeError('Protected system changed')
        r['status']='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY';r['gate_return_code']=0
    except BaseException as error:r['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        unsafe=owner is not None and (owner.active or (bool(owner.buffers) and not owner.safe()))
        if not unsafe:
            try:
                if owner is not None:owner.release()
                sealed_ids=None;targets=None
                if runtime is not None:runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None
                if owner is not None and owner.overlay is not None and not r['stable_restored']:restore()
            except BaseException as error:unsafe=True;r['errors'].append(dict(type='CleanupUnproven',message=str(error)))
        if allocator is not None and not unsafe:
            try:allocator.close()
            except BaseException as error:unsafe=True;r['errors'].append(dict(type='AllocatorRestoreUnproven',message=str(error)))
        r['unsafe_dma_buffers_retained']=unsafe;r['safe_buffers_released']=not unsafe
        if owner is not None and owner.kernel is not None:r['final_snapshot']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
        if unsafe:r['status']='FAIL_UNSAFE_RETAINED';r['gate_return_code']=1
        r['phase']=phase[0];r['elapsed_s_diagnostic_not_performance']=time.monotonic()-started;r['memory_after_cleanup']=proc()
        raw=(json.dumps(r,indent=2,allow_nan=False)+'\n').encode('utf-8');tmp=OUTPUT.with_suffix('.partial')
        with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,OUTPUT);stopped.set();print('M420_RESULT_SAVED '+r['status'],flush=True)
        if unsafe:
            from m420_export import emit_saved
            emit_saved();print('M420_RETAIN_OWNER_PROCESS_AND_ALL_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return r['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
