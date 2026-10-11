"""Default-off complete late11 visual PL numerical gate; one visual, no language.

Saved exact software wire/boundary/features are reused without visual replay.
No performance adjudication; retain owner on unsafe DMA and restore stable.
"""
import argparse,gc,hashlib,importlib.util,json,os,sys,threading,time,traceback,weakref
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m430_late11_visual_warm_01/BOARD_RESULT.json')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,raw):
    if path.exists():raise RuntimeError('Immutable artifact exists; collect only')
    tmp=path.with_suffix(path.suffix+'.partial')
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def array_file(path,value):
    import io,numpy as np
    b=io.BytesIO();np.save(b,value,allow_pickle=False);save(path,b.getvalue())
    return dict(path=path.name,bytes=path.stat().st_size,sha256=digest(path))
def package(folder,expected):
    if digest(folder/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Manifest differs')
    manifest=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes());names={r['path'] for r in manifest['files']}
    if {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}!=names|{'PACKAGE_MANIFEST.json'} or len(names)!=manifest['file_count'] or sum(r['bytes'] for r in manifest['files'])!=manifest['total_bytes']:raise RuntimeError('Exact package closure differs')
    for row in manifest['files']:
        p=folder/row['path']
        if p.is_symlink() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Payload differs')
def proc():
    row={}
    for x in Path('/proc/meminfo').read_text().splitlines():
        if x.split(':')[0] in ('CmaFree','MemAvailable','Cached'):row[x.split(':')[0]]=int(x.split()[1])*1024
    row['VmRSS']=int(next(x.split()[1] for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')))*1024
    return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('--enable-visual-performance',action='store_true');args=ap.parse_args()
    if not args.enable_visual_performance:raise RuntimeError('Software range disabled by default')
    if OUTPUT.parent.exists():raise RuntimeError('Saved attempt exists; Collect only')
    if os.geteuid()!=0:raise RuntimeError('Same-terminal root required')
    OUTPUT.parent.mkdir(mode=0o700);started=time.monotonic();phase=['source'];stop=threading.Event()
    result=dict(status='FAIL_M430_COMPLETE_VISUAL_WARM',gate_level='late11-complete-visual-controlled-warm-performance',gate_return_code=1,
        manifest_sha256=args.manifest_sha,selected_layers=list(range(13,24)),errors=[],memory=[],boundary_comparison=[],
        overlay_loaded=False,dma_allocations=0,fpga_transactions=0,visual_forward_calls=0,language_forward_calls=0,
        temperature_measurement_enabled=False,performance_pass=False,formal_promotion_allowed=False,
        feature_screen_pass=False,feature_pass_ranges=[],ranges=[],original_visual_forward_calls=0,task_screen_pass=False,task_screen_recorded=False,
        numerical_hardware_proven=False,bindings_restored=False,visual_owner_closed=False)
    runtime=targets=scope=store=None;owner_ref=None;scopes=[];lock=None
    owner=allocator=None;sealed_ids=None;restore=None;unsafe=False
    result.update(build_id='0x4D333537',transactions=[],PS_checkpoints=[],allocations=[],releases=[],overlay_loads=[],PL_rows=[],staging=[],physical_transactions_started=0,
        unsafe_dma_buffers_retained=False,safe_buffers_released=True,stable_restored=False,DMA_allocator_restored=False,DMA_sealed_after_main=False)
    def beat():
        while not stop.wait(30):print('M430_HEARTBEAT '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        package(HERE,args.manifest_sha);plan=json.loads((HERE/'PLAN.json').read_bytes())
        if plan['selected_layers']!=result['selected_layers'] or not plan['candidate_PL_enabled'] or plan['temperature_measurement_enabled']:raise RuntimeError('Frozen software scope differs')
        for row in plan['reused_packages']:package(Path(row['directory']),row['manifest_sha256'])
        for row in plan['prerequisites']:
            if digest(Path(row['path']))!=row['sha256']:raise RuntimeError('Prerequisite bytes differ')
        sys.path[:0]=[str(HERE)]+[x['directory'] for x in plan['reused_packages']]
        from frozen_video_identity import RELEASE,module_paths,verify_m277_release_subset,FRAMES,ADDON,STACK_SHA
        source=json.loads((HERE/'SOURCE_IDENTITIES.json').read_bytes())
        for row in source['files']:
            p=RELEASE/row['path']
            if p.is_symlink() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Frozen source identity differs')
        result['source_identities_verified']=len(source['files'])
        result['release_subset']=verify_m277_release_subset(RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0]=[str(p) for p in module_paths()]
        spec=importlib.util.spec_from_file_location('m426_release_preflight',RELEASE/'scripts/preflight.py');preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
        phase[0]='original35asset-preflight';checked=preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_bytes()),port_check=True)
        result['release_preflight']={k:checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        if checked['status']!='READY_FOR_BOARD_PREFLIGHT':raise RuntimeError('Original35 checks rejected')
        import numpy as np,torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m273_latest_multiscale_contract import preprocess
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m426_range02 import resolve,prefix_evidence
        from m430_timed_scope import TimedPLRangeScope as PLRangeScope,LightBatchCheck as SavedWireCheck,SELECTED
        from m428_saved_features import load_features,read_owned
        import m418_probe as lower
        from m341_build_id_gate import ROOT as BOARD_ROOT,STABLE,STABLE_SHA,service_stopped
        from board_safety import safe_to_release
        from m414_policy import PlannedDMA,verify_owner_buffers
        lower.EVIDENCE=OUTPUT.parent
        if BOARD_ROOT!=RELEASE:raise RuntimeError('Frozen resource owner release root differs')
        from m427_saved_baseline import source as baseline_source,feature as baseline_feature,boundary as baseline_boundary
        from m414_quality import tensor,visual_quality
        from m414_policy import MemoryBudget
        from m407_mlp_contract import chain_for,metrics
        from m410_saved_case import read_exact
        from m406_vision_observer import backend_evidence
        from test_m409_ftz_reference import actual_host
        import contract_runtime
        identities={x['path']:x['sha256'] for x in source['files']};result['resolved_modules']={}
        for name in plan['resolved_module_names']:
            p=Path(sys.modules[name].__file__).resolve();rel=p.relative_to(RELEASE).as_posix()
            if identities.get(rel)!=digest(p):raise RuntimeError('Actual resolved source differs:'+name)
            result['resolved_modules'][name]=dict(path=rel,sha256=identities[rel])
        saved_arrays,saved_identities=load_features(plan)
        task=json.loads(read_owned(Path(plan['M428_result_path']),plan['M428_raw_bytes'],plan['M428_raw_sha256']))
        if task['status']!='PASS_M428_SAVED_FEATURE_DECISION_CONSISTENCY' or type(task['gate_return_code']) is not int or task['gate_return_code'] or task['errors'] or not task['safe_buffers_released'] or not task['stable_overlay_reloaded'] or task['vision_forward_calls'] or task['temperature_measurement_enabled']:raise RuntimeError('Saved task/lifecycle prerequisite differs')
        candidate_source=json.loads(read_owned(Path(plan['feature_directories']['candidate'])/'BOARD_RESULT.json',plan['M427_raw_bytes'],plan['M427_raw_sha256']))
        accepted=next(x for x in candidate_source['ranges'] if x['name']=='late_13_23')
        result['saved_feature_identities']=saved_identities;result['software_reference_source_sha256']=plan['M427_raw_sha256'];result['task_source_sha256']=plan['M428_raw_sha256']
        SavedWireCheck(accepted['reference_batches'],lambda *unused:None)
        performance_protocol=json.loads((HERE/'PROTOCOL.json').read_bytes())
        if digest(HERE/'PROTOCOL.json')!=plan['protocol_sha256']:raise RuntimeError('Frozen timing protocol differs')
        if digest(Path(plan['numerical_result_path']))!=plan['numerical_result_sha256']:raise RuntimeError('Complete numerical evidence differs')
        prior_numeric=json.loads(Path(plan['numerical_result_path']).read_bytes())
        if prior_numeric['status']!='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL' or prior_numeric['gate_return_code'] or prior_numeric['errors'] or not prior_numeric['stable_restored'] or not prior_numeric['safe_buffers_released'] or prior_numeric['matched_wire_batches']!=286:raise RuntimeError('Complete numerical/lifecycle evidence required')
        result['numerical_source_sha256']=plan['numerical_result_sha256']
        lower_package=Path(plan['lower_directory'])
        if digest(lower_package/'HARDWARE_CLOSURE.json')!=plan['hardware_closure_sha256'] or digest(lower_package/'BOARD_CASES.json')!=plan['board_case_sha256']:raise RuntimeError('Reused hardware/ABI closure differs')
        closure=json.loads((lower_package/'HARDWARE_CLOSURE.json').read_bytes())
        if closure['status']!='PASS_ALL_NEW_CIRCUIT_PREREQUISITES' or closure['build_id']!='0x4D333537' or not closure['stable_rollback_intact'] or not closure['original_source_closure_unchanged']:raise RuntimeError('Reused numerical/header/RTL prerequisites rejected')
        result['hardware_closure_sha256']=plan['hardware_closure_sha256']
        bootstrap_path=Path(plan['isolated_bootstrap_result_path'])
        if digest(bootstrap_path)!=plan['isolated_bootstrap_source_sha256']:raise RuntimeError('Saved CPU bootstrap receipt differs')
        bootstrap_prior=json.loads(bootstrap_path.read_bytes())
        if bootstrap_prior['status']!='PASS_M430_ISOLATED_CPU_BOOTSTRAP_ONLY' or bootstrap_prior['gate_return_code'] or bootstrap_prior['errors']:raise RuntimeError('Same-level CPU bootstrap not passed')
        result['isolated_bootstrap_source_sha256']=plan['isolated_bootstrap_source_sha256']
        import subprocess
        child=subprocess.run([sys.executable,'-I','-B',str(HERE/'m430_component_entry.py'),str(RELEASE)],capture_output=True,timeout=180)
        save(OUTPUT.parent/'component_stdout.bin',child.stdout);save(OUTPUT.parent/'component_stderr.bin',child.stderr)
        if child.returncode:raise RuntimeError('CPU-only frozen scope component rejected before Overlay')
        boots=[x.split('=',1)[1] for x in child.stdout.decode('utf-8').splitlines() if x.startswith('M430_BOOTSTRAP=')]
        if len(boots)!=1:raise RuntimeError('Unique frozen backend receipt required')
        result['component_bootstrap']=json.loads(boots[0])
        if result['component_bootstrap']!=bootstrap_prior['bootstrap']:raise RuntimeError('CPU isolated backend differs from passed small gate')
        lines=[x.split('=',1)[1] for x in child.stdout.decode('utf-8').splitlines() if x.startswith('M430_COMPONENT=')]
        if len(lines)!=1:raise RuntimeError('Isolated component receipt differs')
        result['component']=json.loads(lines[0])
        if result['component']['complete_wire_batches']!=286 or not result['component']['restored'] or len(result['component']['negative_checks'])!=20:raise RuntimeError('Complete scope component required')
        if len(result['component']['timed_light_negative_checks'])!=8:raise RuntimeError('Timed scope/geometry component required')
        result['CPU_component_before_Overlay']=True
        print('M430_CPU_COMPONENT_PASS_BEFORE_RESOURCES',flush=True)
        # Acquire execution lock before constructing an actual runtime; no PL imports.
        import fcntl
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=Path('/boot/firmware/boot.scr.uimg');boot_sha=digest(boot);cmdline=Path('/proc/cmdline').read_text()
        frames=[]
        for name,expected in FRAMES.items():
            p=ADDON/'fixtures'/name
            if digest(p)!=expected:raise RuntimeError('Frame SHA differs')
            frames.append(np.load(p,allow_pickle=False))
        stack=np.ascontiguousarray(np.stack(frames))
        if stack.shape!=(4,448,448,3) or stack.dtype!=np.uint8 or hashlib.sha256(stack.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Ordered frame stack differs')
        tensors=preprocess(np.ascontiguousarray(stack[-1:]));del frames,stack
        expected=json.loads((HERE/'EXPECTED_VISUAL.json').read_bytes());result['preprocessed']={k:tensor(v) for k,v in sorted(tensors.items())}
        if result['preprocessed']!=expected['preprocessed']:raise RuntimeError('Frozen last-frame two-view preprocess differs')
        result['memory_before_constructor']=proc()
        if result['memory_before_constructor']['MemAvailable']<(1<<30)+(768<<20)+(64<<20):raise MemoryError('Ordinary constructor/reference budget unavailable')
        phase[0]='PS-constructor';vbase=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime=M273LatestPSVisionRuntime(vbase/'ps_vision_payload',vbase/'vision_layout',vbase/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');owner_ref=weakref.ref(runtime)
        result['prefix_topology']=prefix_evidence(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,M207FP32GemmW4Linear,torch)
        targets,result['targets']=resolve(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,M207FP32GemmW4Linear,torch)
        store=runtime.store;result['backend_before']=backend_evidence(torch);result['CPU_store_before']=store.evidence()
        result['memory_after_constructor']=proc();budget=MemoryBudget(result['memory_after_constructor'],proc)
        def checkpoint(label):
            if time.monotonic()-started>plan['budget_seconds']:raise RuntimeError('Frozen software budget exhausted; no automatic rerun')
            row=budget.check(label)
            # Layer boundaries retain memory statistics; batch checks retain no arrays.
            if ':batch' not in label:result['memory'].append(row)
        result['initial_service']=service_stopped()
        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base
        layout_path=vbase/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
        if digest(layout_path)!=plan['layout_sha256']:raise RuntimeError('Original W4 layout differs')
        layout=json.loads(layout_path.read_bytes());entries={e['module']:e for e in layout['modules']}
        if [x['path'] for x in layout['files']]!=['weights0.bin','weights1.bin','weights2.bin','weights3.bin']:raise RuntimeError('Original four shard order differs')
        for row in layout['files']:
            p=vbase/'vision_layout'/row['path']
            if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Full frozen W4 shard SHA differs')
        result['weight_windows']={}
        def load_case(index):
            chains={}
            for j,part in enumerate(('fc1','fc2')):
                chain=chain_for(entries[f'model.visual.encoder.layers.{index}.mlp.{part}'],index*2+j)
                if chain!=plan['chains'][str(index)][part]:raise RuntimeError('Actual full layer chain differs')
                chains[part]=chain
            return dict(chains=chains)
        for index in SELECTED:load_case(index)
        host,initial=actual_host(RELEASE)
        original_record=baseline_source(plan)
        original=baseline_feature(original_record)
        result['baseline_source_sha256']=plan['baseline_raw_sha256']
        result['original_visual']=tensor(original)
        if result['original_visual']!=expected['visual']:raise RuntimeError('Saved complete original feature SHA differs')
        for index in range(24):
            checked_boundary=baseline_boundary(original_record,index)
            del checked_boundary
        result['saved_original_all24_boundaries_verified']=True
        result['original_reference_pass']=True
        active_range={}
        def candidate_sink(index,arr):
            if tensor(arr)!=accepted['boundary_comparison'][index]['candidate']:raise RuntimeError('Complete saved software boundary differs:'+str(index))
            ref=baseline_boundary(original_record,index)
            active_range['boundary_comparison'].append(dict(layer=index,original=tensor(ref),candidate=tensor(arr),metrics=metrics(ref,arr)))
            del ref
            print('M430_BOUNDARY '+str(index),flush=True)
        def vision(mode,sink,selected):
            nonlocal scope
            phase[0]=active_range['name']+'-full-visual';checkpoint(phase[0]+':before');result['visual_forward_calls']+=1
            scope=PLRangeScope(torch,runtime.vision.encoder.layers,targets,load_case,initial,host,sink,checkpoint,stage,wire_check)
            with scope:answer=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            scopes.append(scope.restored)
            if not scope.complete:raise RuntimeError('Full24 boundaries/two Linears per selection incomplete')
            checkpoint(phase[0]+':after');return answer
        r=result
        class WorkOwner(lower.Owner):
            def memory(self,label):
                recovery=self.expected==0x4d395832;row=budget.check(label,recovery=recovery);
                if ':batch' not in label and label!='MLP-before-submit':r['memory'].append(row)
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
                r['PL_rows'].append(dict(layer=index,part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw),completed_snapshot=s));return raw
        owner=WorkOwner(base,r);lower_package=Path(plan['lower_directory']);lower_case=json.loads((lower_package/'BOARD_CASES.json').read_bytes())
        zero_packet=(lower_package/'build_packet.bin').read_bytes();zero_raw=(lower_package/'build_golden.bin').read_bytes()
        def zero(path,sha,build,label):
            phase[0]=label;owner.load(path,sha,build,label);owner.allocate([144]*4+[len(zero_packet),len(zero_raw)],label)
            for buf in owner.buffers[:4]:buf[:]=0;buf.sync_to_device()
            owner.transact(zero_packet,zero_raw,int(lower_case['build_config'],16),label);owner.release()
        def restore():zero(STABLE,STABLE_SHA,0x4d395832,'stable-restored-build-id');r['stable_restored']=True
        zero(Path(lower_case['hardware_directory']),lower_case['hardware_manifest_sha256'],0x4d333537,'candidate-legal-build-id')
        owner.allocate([557056]*4+[163856,524288,524288],'completeMLP-seven');sealed_ids=tuple(id(b) for b in owner.buffers);verify_owner_buffers(owner,sealed_ids);r['DMA_sealed_after_main']=True
        from m411_mlp_binding import stage_windows
        from m425_environment import read_environment
        from m425_warm import WarmSequence,adjudicate
        import resource
        def io_stats():
            return {line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/self/io').read_text().splitlines()}
        def stage(index,part,c):
            checkpoint('before-staging')
            rows=[dict(row,relative_file='vision_layout/'+row['path']) for row in plan['windows'][str(index)][part]]
            result['staging'].append(dict(layer=index,**stage_windows(owner,part,rows,vbase)))
        environment=read_environment();result['reference_environment']=environment
        seq=WarmSequence(result,environment,protocol_sha=plan['protocol_sha256'])
        snapshots=[]
        for index,variant in enumerate(performance_protocol['combined_order']):
            seq.before(index);phase[0]='warm-visual-'+str(index+1)+'-'+variant
            checkpoint(phase[0]+':before')
            before_env=read_environment();before_cache=store.evidence();before_io=io_stats();before_usage=resource.getrusage(resource.RUSAGE_SELF);before_memory=proc()
            before_count=result['physical_transactions_started'];row_start=len(result['PL_rows']);stage_start=len(result['staging'])
            scope=None;wire_check=None
            if variant=='B':
                wire_check=SavedWireCheck(accepted['reference_batches'],owner.submit)
                scope=PLRangeScope(torch,runtime.vision.encoder.layers,targets,load_case,initial,host,lambda *x:None,checkpoint,stage,wire_check)
            result['visual_forward_calls']+=1
            tick=time.perf_counter_ns()
            if scope is None:candidate=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            else:
                with scope:candidate=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            elapsed=time.perf_counter_ns()-tick
            after_io=io_stats();after_usage=resource.getrusage(resource.RUSAGE_SELF);after_memory=proc();after_cache=store.evidence();after_env=read_environment()
            expected_feature=saved_arrays[0 if variant=='A' else 1]
            actual_feature=tensor(candidate)
            if not np.array_equal(candidate.view(np.uint32),expected_feature.view(np.uint32)):raise RuntimeError('Complete post-timer feature differs:'+variant)
            if wire_check is not None:
                wire_check.require_complete()
                if not scope.complete or not scope.restored or scope.peak_live_layer_scopes!=1:raise RuntimeError('Timed PL scope lifecycle incomplete')
                batches=scope.batches;scopes.append(scope.restored)
            else:batches={};scopes.append(True)
            count=result['physical_transactions_started']-before_count
            if count!=(286 if variant=='B' else 0):raise RuntimeError('Per-sample PL call count differs')
            row=dict(index=index+1,variant=variant,timing=dict(total_ms=elapsed/1e6),elapsed_ns=elapsed,
                feature=actual_feature,feature_complete_exact=True,before_environment=before_env,after_environment=after_env,
                before_cache=before_cache,after_cache=after_cache,io_delta={k:after_io[k]-before_io[k] for k in before_io},
                major_fault_delta=after_usage.ru_majflt-before_usage.ru_majflt,before_memory=before_memory,after_memory=after_memory,
                physical_calls=count,bindings_restored=scopes[-1],PL_batches=batches,staging_rows=result['staging'][stage_start:],
                device_wait_ns=sum(x['wait_ns'] for x in result['PL_rows'][row_start:]),staging_ns=sum(x['elapsed_ns'] for x in result['staging'][stage_start:]))
            del expected_feature,candidate
            seq.record(row);checkpoint(phase[0]+':after')
            print('M430_VISUAL_SAMPLE '+json.dumps(dict(index=index+1,variant=variant,ms=row['timing']['total_ms'],read_bytes=row['io_delta']['read_bytes'],major_faults=row['major_fault_delta'])),flush=True)
        result['performance_adjudication']=adjudicate(result['formal_samples'])
        a=result['performance_adjudication'];worthwhile=a['performance_pass'] and a['gain_percent']>=performance_protocol['adjudication']['worthwhile_complete_visual_gain_percent_minimum']
        a['scope']='Fixed-input controlled warm complete visual only; no language or production promotion.'
        a['reliable_positive_gain']=a['performance_pass'];a['worthwhile_complete_visual_gain_percent_minimum']=5.;a['performance_pass']=worthwhile
        a['status']='PASS_WORTHWHILE_COMPLETE_VISUAL_GAIN' if worthwhile else 'CLOSE_NO_WORTHWHILE_RELIABLE_COMPLETE_VISUAL_GAIN'
        result['performance_pass']=worthwhile;result['bindings_restored']=all(scopes);result['feature_screen_pass']=True
        result['numerical_hardware_proven']=True;result['matched_wire_batches_reused']=286
        result['candidate_visual']=prior_numeric['candidate_visual'];result['full_visual_quality']=prior_numeric['full_visual_quality']
        result['retained_features']=[]
        result['dma_allocations']=len(result['allocations']);result['fpga_transactions']=result['physical_transactions_started']
        result['backend_after']=backend_evidence(torch);result['CPU_store_after']=store.evidence()
        if result['backend_before']!=result['backend_after'] or not result['CPU_store_after']['cache_within_budget']:raise RuntimeError('Backend/cache bound differs')
        owner.release();sealed_ids=None
        del original,original_record,load_case,vision
        targets=scope=store=None;runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
        if not result['visual_owner_closed'] or not result['bindings_restored']:raise RuntimeError('Visual scope/owner close unproven')
        restore();result['boot_unchanged']=digest(boot)==boot_sha;result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmdline;result['final_service']=service_stopped()
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected system changed')
        result['status']='PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED';result['gate_return_code']=0
    except BaseException as error:
        result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        if owner is not None and owner.kernel is not None:
            result['failure_snapshot_before_cleanup']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
            print('M430_FAILURE_STATE '+json.dumps(dict(snapshot=result['failure_snapshot_before_cleanup'],transaction=result.get('active_transaction'),physical_started=result['physical_transactions_started'])),flush=True)
    finally:
        unsafe=owner is not None and (owner.active or (bool(owner.buffers) and not owner.safe()))
        if not unsafe:
            try:
                if scope is not None and (scope.handles or scope.active):scope.__exit__(None,None,None)
                result['bindings_restored']=all(scopes) and (scope is None or scope.restored)
                if owner is not None:owner.release()
                sealed_ids=None;scope=targets=store=None
                if runtime is not None:runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
                if owner is not None and owner.overlay is not None and not result['stable_restored']:restore()
            except BaseException as error:unsafe=True;result['errors'].append(dict(type='CleanupUnproven',message=str(error)))
        if allocator is not None and not unsafe:
            try:allocator.close()
            except BaseException as error:unsafe=True;result['errors'].append(dict(type='AllocatorRestoreUnproven',message=str(error)))
        result['unsafe_dma_buffers_retained']=unsafe;result['safe_buffers_released']=not unsafe
        if owner is not None and owner.kernel is not None:result['final_snapshot']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
        result['dma_allocations']=len(result['allocations']);result['fpga_transactions']=result['physical_transactions_started']
        if unsafe:result['status']='FAIL_UNSAFE_RETAINED';result['gate_return_code']=1
        if result['gate_return_code']:result['numerical_hardware_proven']=False
        result['memory_after_cleanup']=proc();result['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        save(OUTPUT,json.dumps(result,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('utf-8'));stop.set()
        print('M430_RESULT_SAVED '+result['status'],flush=True)
        if unsafe:
            from m430_export import emit_saved
            emit_saved();print('M430_RETAIN_OWNER_PROCESS_AND_ALL_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return result['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
