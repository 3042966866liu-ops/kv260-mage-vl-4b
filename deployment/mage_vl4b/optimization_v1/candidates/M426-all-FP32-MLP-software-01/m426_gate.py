"""One original and one all22 FP32 MLP exact-software visual quality screen.

No Overlay, DMA, model language forward or performance adjudication. Preserve
complete features for a subsequent unchanged-language task consistency gate.
"""
import argparse,gc,hashlib,importlib.util,json,os,sys,threading,time,traceback,weakref
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/ubuntu/m426_range_software_01/BOARD_RESULT.json')

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
    ap=argparse.ArgumentParser();ap.add_argument('manifest_sha');ap.add_argument('--enable-software-range',action='store_true');args=ap.parse_args()
    if not args.enable_software_range:raise RuntimeError('Software range disabled by default')
    if OUTPUT.parent.exists():raise RuntimeError('Saved attempt exists; Collect only')
    if os.geteuid()!=0:raise RuntimeError('Same-terminal root required')
    OUTPUT.parent.mkdir(mode=0o700);started=time.monotonic();phase=['source'];stop=threading.Event()
    result=dict(status='FAIL_M426_SOFTWARE_RANGE',gate_level='CPU-only-cumulative-visual-MLP-range-screen',gate_return_code=1,
        manifest_sha256=args.manifest_sha,selected_layers=list(range(2,24)),errors=[],memory=[],boundary_comparison=[],
        overlay_loaded=False,dma_allocations=0,fpga_transactions=0,visual_forward_calls=0,language_forward_calls=0,
        temperature_measurement_enabled=False,performance_pass=False,formal_promotion_allowed=False,
        feature_screen_pass=False,task_screen_pass=False,task_screen_recorded=False,
        numerical_hardware_proven=False,bindings_restored=False,visual_owner_closed=False)
    runtime=targets=scope=store=None;owner_ref=None;scopes=[];lock=None
    def beat():
        while not stop.wait(30):print('M426_HEARTBEAT '+phase[0],flush=True)
    threading.Thread(target=beat,daemon=True).start()
    try:
        package(HERE,args.manifest_sha);plan=json.loads((HERE/'PLAN.json').read_bytes())
        if plan['selected_layers']!=result['selected_layers'] or plan['candidate_PL_enabled'] or plan['temperature_measurement_enabled']:raise RuntimeError('Frozen software scope differs')
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
        from m426_range import resolve,RangeScope,SELECTED
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
        phase[0]='PS-constructor';base=RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime=M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json');owner_ref=weakref.ref(runtime)
        targets,result['targets']=resolve(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,M207FP32GemmW4Linear,torch)
        store=runtime.store;result['backend_before']=backend_evidence(torch);result['CPU_store_before']=store.evidence()
        result['memory_after_constructor']=proc();budget=MemoryBudget(result['memory_after_constructor'],proc)
        def checkpoint(label):
            if time.monotonic()-started>plan['budget_seconds']:raise RuntimeError('Frozen software budget exhausted; no automatic rerun')
            row=budget.check(label)
            # Layer boundaries retain memory statistics; batch checks retain no arrays.
            if ':batch' not in label:result['memory'].append(row)
        layout_path=base/'vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
        if digest(layout_path)!=plan['layout_sha256']:raise RuntimeError('Original W4 layout differs')
        layout=json.loads(layout_path.read_bytes());entries={e['module']:e for e in layout['modules']}
        if [x['path'] for x in layout['files']]!=['weights0.bin','weights1.bin','weights2.bin','weights3.bin']:raise RuntimeError('Original four shard order differs')
        for row in layout['files']:
            p=base/'vision_layout'/row['path']
            if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('Full frozen W4 shard SHA differs')
        result['weight_windows']={}
        def load_case(index):
            chains={};windows={};result['weight_windows'][str(index)]={}
            for j,part in enumerate(('fc1','fc2')):
                chain=chain_for(entries[f'model.visual.encoder.layers.{index}.mlp.{part}'],index*2+j)
                if chain!=plan['chains'][str(index)][part]:raise RuntimeError('Actual full layer chain differs')
                parts=[];rows=[]
                for file in layout['files']:
                    path=base/'vision_layout'/file['path'];offset=chain['stage_base_words']*16;size=chain['stage_bytes_per_shard']
                    planned=plan['windows'][str(index)][part][len(parts)]
                    raw=read_exact(path,size,planned['sha256'],offset=offset,file_size=file['bytes'])
                    parts.append(raw);rows.append(planned)
                chains[part]=chain;windows[part]=parts;result['weight_windows'][str(index)][part]=rows
            return dict(chains=chains,windows=windows)
        host,initial=actual_host(RELEASE)
        def original_sink(index,arr):
            array_file(OUTPUT.parent/f'original_boundary_{index:02d}.npy',arr)
        def candidate_sink(index,arr):
            ref=np.load(OUTPUT.parent/f'original_boundary_{index:02d}.npy',allow_pickle=False)
            result['boundary_comparison'].append(dict(layer=index,original=tensor(ref),candidate=tensor(arr),metrics=metrics(ref,arr)))
            del ref
            print('M426_BOUNDARY '+str(index),flush=True)
        def vision(mode,sink):
            nonlocal scope
            phase[0]=mode+'-full-visual';checkpoint(phase[0]+':before');result['visual_forward_calls']+=1
            scope=RangeScope(torch,runtime.vision.encoder.layers,targets,SELECTED,mode,load_case,initial,host,sink,checkpoint)
            with scope:answer=runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
            scopes.append(scope.restored)
            if not scope.complete:raise RuntimeError('Full24 boundaries/two Linears per selection incomplete')
            checkpoint(phase[0]+':after');return answer
        original=vision('original',original_sink);result['original_visual']=tensor(original)
        result['retained_features']=[array_file(OUTPUT.parent/'original_visual.npy',original)]
        if result['original_visual']!=expected['visual']:raise RuntimeError('Fixed board original feature SHA differs; no quantization judgement')
        result['original_reference_pass']=True
        candidate=vision('software',candidate_sink);result['candidate_visual']=tensor(candidate)
        result['retained_features'].append(array_file(OUTPUT.parent/'candidate_visual.npy',candidate))
        result['reference_batches']=scope.batches;result['peak_live_layer_scopes']=scope.peak_live_layer_scopes
        result['logical_reference_calls']=sum(len(rows) for parts in scope.batches.values() for rows in parts.values())
        result['physical_reference_attempts']=sum(x['physical_reference_attempts'] for parts in scope.batches.values() for rows in parts.values() for x in rows)
        if result['logical_reference_calls']!=572 or result['peak_live_layer_scopes']!=1:raise RuntimeError('Bounded all22 software contract differs')
        result['full_visual_quality']=visual_quality(original,candidate);result['feature_screen_pass']=result['full_visual_quality']['feature_screen_pass']
        result['software_screen_completed']=True;result['bindings_restored']=all(scopes)
        result['backend_after']=backend_evidence(torch);result['CPU_store_after']=store.evidence()
        if result['backend_before']!=result['backend_after'] or not result['CPU_store_after']['cache_within_budget']:raise RuntimeError('Backend/cache bound differs')
        del original,candidate,load_case,vision
        targets=scope=store=None;runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
        result['no_pynq_import']=not any(n=='pynq' or n.startswith('pynq.') for n in sys.modules)
        result['boot_unchanged']=digest(boot)==boot_sha;result['cmdline_unchanged']=Path('/proc/cmdline').read_text()==cmdline
        if not all(result[k] for k in ('bindings_restored','visual_owner_closed','no_pynq_import','boot_unchanged','cmdline_unchanged')):raise RuntimeError('CPU lifecycle/system evidence incomplete')
        result['status']='PASS_M426_FEATURE_SCREEN_TASK_PENDING' if result['feature_screen_pass'] else 'REJECT_M426_ALL22_FEATURE_RANGE'
        result['gate_return_code']=0
    except BaseException as error:result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        try:
            if scope is not None and (scope.handles or scope.active):scope.__exit__(None,None,None)
            result['bindings_restored']=all(scopes) and (scope is None or scope.restored)
            scope=targets=store=None
            if runtime is not None:runtime.close();runtime=None;gc.collect();result['visual_owner_closed']=owner_ref() is None
        except BaseException as error:result['errors'].append(dict(type='PSCleanupUnproven',message=str(error)));result['gate_return_code']=1;result['status']='FAIL_M426_SOFTWARE_RANGE'
        result['memory_after_cleanup']=proc();result['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        save(OUTPUT,json.dumps(result,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('utf-8'));stop.set()
        if lock is not None:os.close(lock)
        print('M426_RESULT_SAVED '+result['status'],flush=True)
    return result['gate_return_code']
if __name__=='__main__':raise SystemExit(main())
