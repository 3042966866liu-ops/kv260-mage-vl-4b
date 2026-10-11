"""Default-off one actual visual MLP; fixed numerical then complete-segment timing."""
import argparse,gc,hashlib,importlib.util,io,json,os,sys,threading,time,traceback,weakref
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m411_complete_mlp_01/BOARD_RESULT.json')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def verify_package(folder,expected):
    if digest(folder/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Package manifest differs')
    m=json.loads((folder/'PACKAGE_MANIFEST.json').read_bytes());names={x['path'] for x in m['files']}
    if {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}!=names|{'PACKAGE_MANIFEST.json'} or len(names)!=m['file_count'] or sum(x['bytes'] for x in m['files'])!=m['total_bytes']:raise RuntimeError('Package closure/count/bytes differs')
    for x in m['files']:
        p=folder/x['path']
        if p.is_symlink() or p.stat().st_size!=x['bytes'] or digest(p)!=x['sha256']:raise RuntimeError('Package payload differs')
def proc():
    result={}
    for name in ('read_bytes','rchar'):
        lines=Path('/proc/self/io').read_text().splitlines();result[name]=int(next(x.split()[1] for x in lines if x.startswith(name+':')))
    for x in Path('/proc/meminfo').read_text().splitlines():
        k=x.split(':')[0]
        if k in ('CmaFree','MemAvailable','Cached'):result[k]=int(x.split()[1])*1024
    result['VmRSS']=int(next(x.split()[1] for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')))*1024
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('--enable-complete-MLP-gate',action='store_true');a=ap.parse_args()
    if not a.enable_complete_MLP_gate:raise RuntimeError('Default-off complete MLP')
    if OUTPUT.parent.exists():raise RuntimeError('Original attempt exists; Collect only')
    OUTPUT.parent.mkdir(mode=0o700);started=time.monotonic();phase=['source'];stopped=threading.Event()
    r=dict(status='FAIL_M411_COMPLETE_MLP',gate_level='isolated-complete-visual-MLP',gate_return_code=1,manifest_sha256=a.manifest_sha,build_id='0x4D333537',errors=[],
        transactions=[],memory=[],allocations=[],releases=[],overlay_loads=[],physical_transactions_started=0,full_model=False,video=False,promoted=False,expanded_24_layers=False,
        performance_pass=False,numerical_pass=False,visual_forward_calls=0,language_forward_calls=0,bindings_restored=False,PS_owner_closed=False,samples=[],warmups=[],local_mlp_calls=0,PL_rows=[],staging=[])
    owner=runtime=mlp=layer=x=binding=cap=lock=None;restored=[];ps_ref=None
    def beat():
        while not stopped.wait(30):print('M411_HEARTBEAT '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        if os.geteuid()!=0:raise RuntimeError('Root required')
        verify_package(HERE,a.manifest_sha);plan=json.loads((HERE/'PLAN.json').read_bytes())
        for row in plan['reused_packages']:verify_package(Path(row['directory']),row['manifest_sha256'])
        sys.path[:0]=[str(Path(row['directory'])) for row in plan['reused_packages']]
        import numpy as np
        import m410_probe as lower
        from m410_saved_case import read_exact,load_case
        from m411_mlp_binding import PLMLPBinding,decision,stage_windows
        from m341_build_id_gate import ROOT,STABLE,STABLE_SHA,service_stopped
        from measurement import write_json
        from board_safety import safe_to_release
        import fcntl
        lower.EVIDENCE=OUTPUT.parent
        prior=Path(plan['chain_result']);assert digest(prior)==plan['chain_raw_sha256']
        previous=json.loads(prior.read_bytes());assert previous['status']=='PASS_M410_CHAIN' and previous['gate_return_code']==0
        r['prior_chain_sha256']=plan['chain_raw_sha256'];r['package_verified']=True
        ids=json.loads((Path(plan['reference_package'])/'M348_SOURCE_IDENTITIES.json').read_bytes())
        for row in ids['files']:
            p=ROOT/row['path']
            if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Frozen source identity differs')
        r['source_identities_verified']=len(ids['files'])
        from frozen_video_identity import module_paths,verify_m277_release_subset
        r['release_subset']=verify_m277_release_subset(ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0]=[str(p) for p in module_paths()]
        spec=importlib.util.spec_from_file_location('m411_original_preflight',ROOT/'scripts/preflight.py');preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
        phase[0]='original35asset-preflight';checked=preflight.inspect(json.loads((ROOT/'configs/deployment.example.json').read_bytes()),port_check=True)
        r['release_preflight']={k:checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        if checked['status']!='READY_FOR_BOARD_PREFLIGHT':raise RuntimeError('Original35 full asset checks rejected')
        import torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m408_target03 import resolve_target,verify_matrices
        from m408_mlp_capture04 import Capture,compare
        from m406_vision_observer import backend_evidence
        from test_m409_ftz_reference import actual_host
        sys.path.insert(0,str(STABLE/'runtime'));import board_runtime as base
        host,initial=actual_host(ROOT);lower_spec=json.loads((Path(plan['lower_package'])/'BOARD_CASES.json').read_bytes())
        from test_m411_binding import component
        r['component']=component(ROOT,OUTPUT.parent)
        print('M411_ACTUAL_TORCH_COMPONENT_PASS',flush=True)
        chains={}
        for mode in ('Descriptor','Chain'):
            chain,_,_,_,_=load_case(lower_spec,mode,ROOT,host);chains[lower_spec['cases'][mode]['part']]=chain
        reference_folder=Path(lower_spec['reference_directory']);ref=json.loads(read_exact(reference_folder/'RESULT.json',lower_spec['reference_result_bytes'],lower_spec['reference_raw_sha256']))
        expected={};candidate={}
        for part in ('fc1','fc2'):
            for b in ref['reference_batches'][part]:
                key=(part,b['start'],b['selected_shift']);name=f'{part}_{b["start"]:03d}_shift{b["selected_shift"]}'
                expected[key]=(read_exact(reference_folder/(name+'.packet'),b['input_bytes'],b['packet_sha256']),read_exact(reference_folder/(name+'.raw'),b['output_bytes'],b['raw_sha256']))
        for row in ref['artifacts']:
            if row['path'].endswith('.npy'):
                data=read_exact(reference_folder/row['path'],row['bytes'],row['sha256']);candidate[row['path'][:-4]]=np.load(io.BytesIO(data),allow_pickle=False)
        from m409_gate import load_capture
        # Existing capture loader is immutable and uses its original retained directory.
        original=load_capture(json.loads((Path(plan['reference_package'])/'M408_CAPTURE_EXPECTED.json').read_bytes()),np)
        if not np.array_equal(original['input'].view(np.uint32),candidate['input'].view(np.uint32)):raise RuntimeError('Same real input differs')
        before=proc();r['memory_before_constructor']=before
        if before['MemAvailable']<(1<<30)+(256<<20)+(64<<20):raise MemoryError('Original PS constructor/temporary64MiB reserve rejected')
        phase[0]='PS-constructor';vbase=ROOT/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime=M273LatestPSVisionRuntime(vbase/'ps_vision_payload',vbase/'vision_layout',vbase/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');ps_ref=weakref.ref(runtime)
        layer,r['target_resolution']=resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch);r['target_matrices']=verify_matrices(layer,M207FP32GemmW4Linear,torch)
        if r['target_matrices']!=ref['target_matrices'] or r['target_resolution']!=ref['target_resolution']:raise RuntimeError('Actual target/bias topology differs')
        mlp=layer.mlp;x=torch.from_numpy(original['input']).unsqueeze(0);r['backend_before']=backend_evidence(torch)
        from m261_budgeted_w4_runtime import CACHE_NAMES,M261BudgetedFourPortW4Store
        if type(mlp.fc1.store) is not M261BudgetedFourPortW4Store or mlp.fc1.store is not mlp.fc2.store or any(getattr(mlp,k).name in CACHE_NAMES for k in ('fc1','fc2')):raise RuntimeError('Original uncached target store/policy differs')
        r['CPU_store_before']=mlp.fc1.store.evidence()
        r['memory_after_constructor']=proc()
        if r['memory_after_constructor']['CmaFree']<64<<20:raise MemoryError('Actual complete PS constructor below64MiB CMA before hardware')
        r['initial_service']=service_stopped();lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        boot=ROOT.__class__('/boot/firmware/boot.scr.uimg');boot_before=digest(boot);cmd_before=Path('/proc/cmdline').read_text()
        class WorkOwner(lower.Owner):
            def submit(self,part,c,start,shift,packet):
                tx=self.buffers[4];rx=self.buffers[5+(len(r['PL_rows'])%2)];tx[:len(packet)]=np.frombuffer(packet,np.uint8);tx.sync_to_device();rx[:c['output_bytes']]=0xa5;rx.sync_to_device()
                self.memory('MLP-before-submit')
                for reg,b in zip(base.REG_POINTERS,self.buffers[:4]):base.write_u64(self.kernel,reg,base.physical_address(b))
                self.kernel.write(base.REG_CONFIG,int(c['config'],16));self.active=self.ever=True;self.completed=False;r['physical_transactions_started']+=1
                submitted=time.monotonic_ns();r['active_transaction']=dict(part=part,start=start,shift=shift,input_bytes=len(packet),output_bytes=c['output_bytes'],config=c['config'])
                self.dma.recvchannel.transfer(rx,nbytes=c['output_bytes']);self.kernel.write(base.REG_AP_CTRL,1);self.dma.sendchannel.transfer(tx,nbytes=len(packet))
                s,observation=lower.wait_observed(lambda:base.transaction_snapshot(self.kernel,self.dma),submitted,timeout_s=10.,expected_build_id=self.expected)
                if not safe_to_release(s):raise RuntimeError('Unproven completed state')
                self.active=False;self.completed=True;rx.sync_from_device();raw=bytes(memoryview(rx)[:c['output_bytes']])
                r['PL_rows'].append(dict(part=part,start=start,shift=shift,wait_ns=observation['wait_ns'],input_bytes=len(packet),output_bytes=len(raw)));return raw
        owner=WorkOwner(base,r)
        lower_case=lower_spec
        zero_packet=(Path(plan['lower_package'])/'build_packet.bin').read_bytes();zero_raw=(Path(plan['lower_package'])/'build_golden.bin').read_bytes()
        def zero(path,sha,build,label):
            phase[0]=label;owner.load(path,sha,build,label);owner.allocate([144]*4+[len(zero_packet),len(zero_raw)],label)
            for buf in owner.buffers[:4]:buf[:]=0;buf.sync_to_device()
            owner.transact(zero_packet,zero_raw,int(lower_case['build_config'],16),label);owner.release()
        def restore():zero(STABLE,STABLE_SHA,0x4d395832,'stable-restored-build-id');r['stable_restored']=True
        zero(Path(lower_case['hardware_directory']),lower_case['hardware_manifest_sha256'],0x4d333537,'candidate-legal-build-id')
        owner.allocate([557056]*4+[163856,524288,524288],'completeMLP-seven')
        def stage(part,c):
            rows=lower_case['cases']['Chain' if part=='fc1' else 'Descriptor']['windows']
            r['staging'].append(stage_windows(owner,part,rows,ROOT))
        with torch.inference_mode():
            phase[0]='numerical-original';r['local_mlp_calls']+=1
            with Capture(mlp) as cap:mlp(x)
            cap.require_complete();restored.append(cap.restored)
            if any(not np.array_equal(cap.values[k].view(np.uint32),original[k].view(np.uint32)) for k in cap.values):raise RuntimeError('Original CPU replay differs')
            phase[0]='numerical-PL';r['local_mlp_calls']+=1;binding=PLMLPBinding(torch,mlp,chains,initial,host,stage,owner.submit,expected)
            with Capture(mlp) as cap:
                with binding:mlp(x)
            cap.require_complete();restored.extend([cap.restored,binding.restored])
            if any(not np.array_equal(cap.values[k].view(np.uint32),candidate[k].view(np.uint32)) for k in cap.values):raise RuntimeError('Complete actual PL software reference differs')
            r['numerical_batches']=binding.batches;r['full_wire_reference_batches_exact']=26
            r['quality_metrics'],quality=compare(original,cap.values)
            from m407_mlp_contract import metrics,local_screen
            ref_boundary=torch.from_numpy(original['residual']+original['output']).to(torch.bfloat16).float().numpy();alt_boundary=torch.from_numpy(original['residual']+cap.values['output']).to(torch.bfloat16).float().numpy()
            r['boundary_residual_bf16']=metrics(ref_boundary,alt_boundary)
            if not quality or not local_screen(r['boundary_residual_bf16']):raise RuntimeError('Frozen local quality threshold rejected')
            r['numerical_pass']=True;binding=cap=None;del ref_boundary,alt_boundary
            def run(variant,warmup):
                phase[0]=('warmup-' if warmup else 'timed-')+variant;before=proc();first=len(r['PL_rows']);staged=len(r['staging']);r['local_mlp_calls']+=1
                if variant=='B':
                    # Binding setup outside timer; first weight read/restore is inside actual MLP.
                    with PLMLPBinding(torch,mlp,chains,initial,host,stage,owner.submit) as current:
                        t=time.perf_counter_ns();answer=mlp(x);elapsed=time.perf_counter_ns()-t
                    restored.append(current.restored);batches=current.batches
                else:t=time.perf_counter_ns();answer=mlp(x);elapsed=time.perf_counter_ns()-t;batches=None
                after=proc();arr=answer[0].numpy();want=original['output'] if variant=='A' else candidate['output']
                if not np.array_equal(arr.view(np.uint32),want.view(np.uint32)):raise RuntimeError('Timed branch output differs outside timer')
                row=dict(variant=variant,elapsed_ns=elapsed,read_bytes=after['read_bytes']-before['read_bytes'],rchar=after['rchar']-before['rchar'],before=before,after=after,output_exact_outside_timer=True,
                    logical_PL_calls=26 if variant=='B' else 0,physical_PL_calls=len(r['PL_rows'])-first,staging_bytes=sum(z['bytes'] for z in r['staging'][staged:]),batches=batches)
                (r['warmups'] if warmup else r['samples']).append(row);print('M411_SEGMENT '+json.dumps(dict(variant=variant,warmup=warmup,elapsed_s=elapsed/1e9,read_bytes=row['read_bytes'])),flush=True)
                if time.monotonic()-started>840:raise RuntimeError('Predeclared bounded gate expired; no extra samples')
            run('A',True);run('B',True)
            for variant in 'ABBABAAB':run(variant,False)
        r['comparison']=decision(r['samples']);r['performance_pass']=r['comparison']['performance_pass'];r['backend_after']=backend_evidence(torch)
        r['CPU_store_after']=mlp.fc1.store.evidence()
        if r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=12:raise RuntimeError('Original six CPU segments/twelve uncached Linear restores differ')
        if r['backend_before']!=r['backend_after']:raise RuntimeError('Backend or threads changed')
        r['bindings_restored']=all(restored);owner.release();binding=cap=mlp=layer=x=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None
        if not r['bindings_restored'] or not r['PS_owner_closed']:raise RuntimeError('PS owner/binding lifecycle unproven')
        restore();r['boot_unchanged']=digest(boot)==boot_before;r['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmd_before;r['final_service']=service_stopped()
        if not r['boot_unchanged'] or not r['cmdline_unchanged']:raise RuntimeError('Protected system identity changed')
        r['status']='PASS_M411_COMPLETE_MLP_NET_GAIN' if r['performance_pass'] else 'CLOSED_M411_COMPLETE_MLP_NO_RELIABLE_NET_GAIN'
        r['gate_return_code']=0
    except BaseException as error:r['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        if binding is not None and binding.previous:binding.__exit__(None,None,None)
        if cap is not None and cap.handles:cap.__exit__(None,None,None)
        unsafe=owner is not None and (owner.active or (bool(owner.buffers) and not owner.safe()))
        if not unsafe:
            try:
                if owner is not None:owner.release()
                binding=cap=mlp=layer=x=None
                if runtime is not None:runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None
                if owner is not None and owner.overlay is not None and not r.get('stable_restored'):restore()
            except BaseException as error:unsafe=True;r['errors'].append(dict(type='CleanupUnproven',message=str(error)))
        r['unsafe_dma_buffers_retained']=unsafe;r['safe_buffers_released']=not unsafe
        if owner is not None and owner.kernel is not None:r['final_snapshot']=owner.base.transaction_snapshot(owner.kernel,owner.dma)
        if unsafe:r['status']='FAIL_UNSAFE_RETAINED';r['gate_return_code']=1
        if r['gate_return_code']:r['performance_pass']=False
        r['phase']=phase[0];r['elapsed_s_diagnostic_not_performance']=time.monotonic()-started;r['memory_after_cleanup']=proc()
        raw=(json.dumps(r,indent=2,allow_nan=False)+'\n').encode('utf-8');tmp=OUTPUT.with_suffix('.partial')
        with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,OUTPUT);stopped.set();print('M411_RESULT_SAVED '+r['status'],flush=True)
        if unsafe:
            from m411_export import emit_saved
            emit_saved();print('M411_RETAIN_OWNER_PROCESS_AND_ALL_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True:time.sleep(30)
        if lock is not None:os.close(lock)
    return r['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
