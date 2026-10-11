"""Independent actual159 video capacity diagnostic; production admission unchanged."""
import argparse
import fcntl
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import weakref
from m370_patch_scope import PatchScope
from m390_capture_boundary import GateUpCapture,CaptureBoundary
sys.dont_write_bytecode = True
from measurement import sha256, write_json
from owned_buffer_release import OwnedBufferRelease
from m363_package_identity import verify_frozen_package
from m363_observers import observe_call,tokenizer_proxy,retained_inventory,mapping_inventory,ROLES
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, RELEASE,FRAMES,STACK_SHA
from types import SimpleNamespace
from m368_video_contract import tensor,check_call_contract,validate_stream
from memory_lifecycle import memory_snapshot
from ps_slot_capacity import CapacityRejected
from m368_stage_policy import StagePolicy,SHAPES
HERE = Path(__file__).resolve().parent
CANDIDATE = Path('/home/ubuntu/m357_candidate_01')
CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'
EVIDENCE = None
TARGET = None
TARGET_SHA = None
TARGET_BUILD = None
PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'
BLOCKED_BOARD_METHODS = ()


def forbid(name, blocked):
    def stop(*args, **kwargs):
        blocked.append(name)
        raise RuntimeError('Load-only probe forbids inference/transaction: ' + name)
    return stop


def main():
    global EVIDENCE,TARGET,TARGET_SHA,TARGET_BUILD
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); parser.add_argument('case',choices=('B1',)); parser.add_argument('--enable-capture',action='store_true'); args = parser.parse_args()
    is_candidate=args.case.startswith('B')
    TARGET=CANDIDATE if is_candidate else STABLE
    TARGET_SHA=CAND_SHA if is_candidate else STABLE_SHA
    TARGET_BUILD='0x4D333537' if is_candidate else '0x4D395832'
    EVIDENCE=Path('/home/ubuntu/m390_gate_up_capture_01')/args.case
    if not args.enable_capture: raise RuntimeError('M390 disabled by default')
    path = EVIDENCE / 'load-memory.json'
    if EVIDENCE.exists(): raise RuntimeError('Immutable evidence directory exists; collect only')
    EVIDENCE.mkdir(mode=0o700,parents=True,exist_ok=False)
    result = dict(status='FAIL', gate_level='sealed-DMA-fixed159-layer0-gate-up-capture', build_id=TARGET_BUILD,case=args.case,io_events=[],common_runner_sha256=sha256(Path(__file__)),cache_policy='natural cache; no clearing; identical policy is not identical cache residency', errors=[], stages=[],
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                  overlay_loaded=False, model_forward_calls=0, blocked_inference_attempts=[], allocated_buffers=[],
                  experiment_scope='Original complete runtime retained, no PS prefetch; original visual and layer0 q/kv/attention_out/gate_up only; no mlp_down, later layer or head',
                  worker_started=False, ps_slot={}, released_buffers=[], fpga_transactions=0, memory_capacity_proven=False, serving_after_vision_capacity_proven=False, gate_return_code=1)
    runtime = engine = base = lock = policy = None
    initialized = unsafe = False
    allocations = []; registry = PatchScope(); slots = []; ps_session = None
    phase, stopped = ['package'], threading.Event()
    started = time.monotonic()
    def heartbeat():
        warned = False
        while not stopped.wait(30):
            elapsed = time.monotonic() - started
            print('M390_HEARTBEAT phase=' + phase[0] + ' elapsed_s=' + str(round(elapsed,1)), flush=True)
            if elapsed > 900 and not warned:
                warned = True
                print('M390_LOAD_BUDGET_EXCEEDED_RETAIN_PROCESS_NO_KILL', flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    def mark(name):
        phase[0] = name
        observed = memory_snapshot()
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            if line.startswith('CmaTotal:'): observed['system_bytes']['CmaTotal'] = int(line.split()[1]) * 1024
        row = dict(name=name, elapsed_s=time.monotonic()-started, memory=observed)
        result['stages'].append(row)
        print('M390_MEMORY ' + json.dumps(row, separators=(',', ':')), flush=True)
        write_json(EVIDENCE / 'progress.json',dict(case=args.case,stage=row,allocated_buffers=result['allocated_buffers'],released_buffers=result['released_buffers']))
        return observed
    def patch(obj, name, replacement):
        return registry.patch(obj,name,replacement)
    try:
        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha
        prior_video_path=Path('/home/ubuntu/m368_staged_video_02/B1/load-memory.json')
        prior_video=json.loads(prior_video_path.read_text(encoding='utf-8'))
        if sha256(prior_video_path)!='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf' or prior_video['status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC' or prior_video['manifest_sha256']!='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66':raise RuntimeError('Same-source actual video loader prerequisite differs')
        result['same_loading_path_video_sha256']=sha256(prior_video_path)
        prior=json.loads((HERE/'STAGE_PREREQUISITE.json').read_text(encoding='utf-8'))
        if prior['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prior['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Independent text prerequisite differs')
        visual_reference=json.loads((HERE/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        if visual_reference['status']!='PASS_MISSING_PS_VISUAL_REFERENCE' or visual_reference['gate_return_code'] or visual_reference['fpga_transactions'] or visual_reference['language_forward_calls']:raise RuntimeError('Missing-only visual reference prerequisite differs')
        prerequisite_path = HERE/'M357_COMPARE_PREREQUISITE.json'
        prerequisite = json.loads(prerequisite_path.read_text(encoding='utf-8'))
        if sha256(prerequisite_path) != PRIOR_SHA or prerequisite['status'] != 'PASS_M357_COMPARE' or not prerequisite['chain_performance_pass'] or not prerequisite['stable_restored']:
            raise RuntimeError('Exact M357 balanced single-chain prerequisite differs')
        result['prior_board_sha256'] = PRIOR_SHA
        text_path=Path('/home/ubuntu/m386_ps_text_01/B1/load-memory.json')
        text=json.loads(text_path.read_text(encoding='utf-8'))
        if sha256(text_path)!='775aaab821f251d12313dc7ac75fec71ac6130bda0d54cb4ef2910cdcb057c01' or text['status']!='PASS_M386_PS_TEXT_NUMERICAL' or not text['session_weakref_dead']:raise RuntimeError('Actual PS text prerequisite differs')
        result['historical_text_prerequisite_sha256']=sha256(text_path)
        video_path=Path('/home/ubuntu/m387_ps_video_01/B1/load-memory.json')
        if sha256(video_path)!='0d36bf91329a1f2e433bfad64905b61836aa75e36c85a54432c028551609d348':raise RuntimeError('Same source actual video prerequisite differs')
        if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')
        hardware = json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if hardware['status'] != 'PASS_ALL_NEW_CIRCUIT_PREREQUISITES': raise RuntimeError('Stable same-SHA hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        result['target_package_identity']=verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=not is_candidate)
        boot = Path('/boot/firmware/boot.scr.uimg'); before_boot = sha256(boot)
        before_cmd = Path('/proc/cmdline').read_text(encoding='utf-8')
        mark('initial-before-source-and-runtime-imports')
        closure = json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        audited = json.loads((HERE/'M348_SOURCE_IDENTITIES.json').read_text(encoding='utf-8'))
        for row in audited['files']:
            file = RELEASE/row['path']
            if file.stat().st_size != row['bytes'] or sha256(file) != row['sha256']: raise RuntimeError('M348 final source drift: '+row['path'])
        for row in closure['files']:
            file = RELEASE/row['path']
            if file.stat().st_size != row['bytes'] or sha256(file) != row['sha256']: raise RuntimeError('Installed source drift: '+row['path'])
        if sha256(RELEASE/'INSTALL_PACKAGE_MANIFEST.json') != 'fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e': raise RuntimeError('Release manifest drift')
        if sha256(ADDON/'PACKAGE_MANIFEST.json') != '4eb8c6c95752208b5848e0e52efb2a713f98487f5b88518dbd5b58801d236568': raise RuntimeError('Video addon manifest drift')
        result['m277_release_subset'] = verify_m277_release_subset(RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0] = [str(p) for p in module_paths()]
        import m276_m254_video_server
        import m276_video_runtime
        import m222_video_server
        import m243_video_server
        import m241_video_language_runtime
        import m238_prefill_runtime
        import video_server
        import board_runtime as base
        import reserved_ddr_pool
        for name, relative in closure['modules'].items():
            if name in sys.modules and Path(sys.modules[name].__file__).resolve() != (RELEASE/relative).resolve(): raise RuntimeError('Final import resolution drift: '+name)
        if not (m222_video_server.M222PSVisionRuntime.__name__ == 'M273LatestPSVisionRuntime' and video_server.M120VideoRuntime.__name__ == 'M276ShortPromptBinaryRuntime'):
            raise RuntimeError('Accepted video class identity drift')
        policy=StagePolicy(result,lambda:runtime,base)
        mark('after-exact-runtime-imports')
        spec = importlib.util.spec_from_file_location('release_preflight',RELEASE/'scripts/preflight.py')
        preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
        patch(preflight,'digest',observe_call(preflight.digest,'release_preflight.digest',mark,result['io_events']))
        for module in (base,video_server,sys.modules['video_language_runtime'],sys.modules['ps_vision_runtime']):
            patch(module,'sha256',observe_call(module.sha256,module.__name__+'.sha256',mark,result['io_events']))
        import tokenizers
        original_tokenizer=tokenizers.Tokenizer
        observed_from_file=observe_call(original_tokenizer.from_file,'tokenizer.from_file',mark,result['io_events'])
        from m363_tokenizer_once import ValidatedTokenizerOnce
        tokenizer_once=ValidatedTokenizerOnce(observed_from_file)
        patch(tokenizers,'Tokenizer',tokenizer_proxy(original_tokenizer,tokenizer_once.from_file))
        inspected = preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_text(encoding='utf-8')),port_check=True)
        result['release_preflight'] = {k:inspected[k] for k in ('status','build_id','missing','hash_or_identity_mismatch','port_free')}
        if inspected['status'] != 'READY_FOR_BOARD_PREFLIGHT': raise RuntimeError('Release assets rejected')
        mark('after-release-asset-hashes')
        d = RELEASE/'deployment/mage_vl4b'
        config = video_server.make_config(d/'m181_m120_video_board_candidate',STABLE,RELEASE/'external_assets/weights',
            RELEASE/'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(config['tokenizer'])); del tokenizer
        mark('after-tokenizer-preconstruction-retained-for-original-loader')
        envpath = EVIDENCE/'environment.json'
        phase[0] = 'fixed-environment-preflight'
        checked = subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(TARGET),
            '--expected-package-manifest-sha256',TARGET_SHA,'--result',str(envpath)],timeout=90)
        if checked.returncode: raise RuntimeError('Fixed environment rejected; no overlay')
        result['environment_sha256'] = sha256(envpath)
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*a,**kw):
            index=len(allocations)
            if index>=7: raise RuntimeError('Allocator sealed: extra DMA allocation refused')
            requested=int(a[0][0]) if a and isinstance(a[0],tuple) and len(a[0])==1 else -1
            if requested!=SHAPES[index] or kw.get('dtype')!=sys.modules['numpy'].uint8:raise RuntimeError('Original buffer request differs')
            before=policy.snapshot()['system_bytes']
            aligned=((requested+4095)//4096)*4096
            if before['CmaFree']<aligned:raise MemoryError('Diagnostic free-page request precheck refused; not allocator failure')
            mark('before-DMA-allocation-'+ROLES[index])
            buffer = original_allocate(*a,**kw); allocations.append(buffer)
            mark('after-DMA-allocation-'+ROLES[index])
            row=dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)),role=ROLES[index],allocation_order=index)
            result['allocated_buffers'].append(row)
            original_free=buffer.freebuffer
            def release_proven():
                observed=base.transaction_snapshot(runtime.kernel,runtime.dma)
                return policy.safe()
            buffer.freebuffer=OwnedBufferRelease(original_free,release_proven,lambda:result['released_buffers'].append(row))
            return buffer
        patch(base,'BUILD_ID',int(TARGET_BUILD,16))
        patch(pynq,'Overlay',observe_call(pynq.Overlay,'pynq.Overlay',mark,result['io_events']))
        board_cls = m243_video_server.M238PrefillRuntime
        blocked = result['blocked_inference_attempts']
        class OwnedBoard(board_cls):
            def __init__(self,*a,**kw):
                nonlocal runtime,initialized
                runtime = self; self._m368_closed = False
                mark('before-original-M238-constructor')
                if not a or Path(a[0]).resolve() != (STABLE/'overlay/m120_m89x2_t32.bit').resolve(): raise RuntimeError('Original constructor bit argument differs')
                super().__init__(TARGET/'overlay/m120_m89x2_t32.bit',*a[1:],**kw); initialized = True
                mark('after-original-M238-and-all-DMA-buffer-allocations')
            def close(self):
                super().close(); self._m368_closed = True
        for name in BLOCKED_BOARD_METHODS: setattr(OwnedBoard,name,forbid('board.'+name,blocked))
        vision_cls = m222_video_server.M222PSVisionRuntime
        class ObservedVision(vision_cls):
            def __init__(self,*a,**kw):
                mark('before-original-PS-vision-constructor')
                super().__init__(*a,**kw)
                mark('after-original-PS-vision-constructor')
            def __call__(self,*a,**kw):
                if result.get('vision_forward_calls',0):raise RuntimeError('Unexpected second visual forward')
                result['vision_forward_calls']=1
                policy.capture('before-original-visual-forward',True)
                visual=super().__call__(*a,**kw)
                policy.capture('after-original-visual-forward',True)
                result['visual_features']=tensor(visual)
                return visual
        language_cls = m243_video_server.M241VideoLanguageModel
        class ObservedLanguage(language_cls):
            def __init__(self,*a,**kw):
                mark('before-original-M241-embedding-and-norm-constructor')
                super().__init__(*a,**kw)
                mark('after-original-M241-embedding-and-norm-constructor')
        for name in ('decode',): setattr(ObservedLanguage,name,forbid('language.'+name,blocked))
        patch(pynq,'allocate',tracked_allocate)
        patch(m243_video_server,'M238PrefillRuntime',OwnedBoard)
        patch(m222_video_server,'M222PSVisionRuntime',ObservedVision)
        patch(m243_video_server,'M241VideoLanguageModel',ObservedLanguage)
        engine = m276_video_runtime.M276ShortPromptBinaryRuntime(config)
        # Original M276 stream executes only the frozen request below.
        mark('before-complete-original-engine-load')
        engine.load()
        patch(video_server,'BUILD_ID',TARGET_BUILD)
        result['overlay_loaded'] = True
        if engine.board is not runtime or not isinstance(engine.language,language_cls): raise RuntimeError('Complete real object closure differs')
        if runtime.host_calls != 0 or runtime.logical_calls != 0 or blocked: raise RuntimeError('Unexpected inference during load')
        result['host_calls'] = runtime.host_calls; result['logical_calls'] = runtime.logical_calls
        result['loaded_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
        result['release_lifecycle'] = 'No transaction submitted: guarded launch paths and exact constructors; DMASR=0 is not completed-DMA idle evidence'
        result['tokenizer_single_parse_reused']=bool(tokenizer_once.parse_count==1 and tokenizer_once.reuse_count==1 and tokenizer_once.cached is None and id(engine.tokenizer)==tokenizer_once.object_identity)
        if not result['tokenizer_single_parse_reused']: raise RuntimeError('Original loader tokenizer identity differs')
        loaded = mark('complete-runtime-loaded-retained')
        result['retained_inventory']=retained_inventory(engine,runtime,allocations)
        result['retained_mappings']=mapping_inventory()
        def capacity(snapshot):
            mem=snapshot['system_bytes']
            row=dict(cma_free_bytes=mem['CmaFree'],mem_available_bytes=mem['MemAvailable'],required_cma_bytes=64<<20,required_mem_available_bytes=64<<20)
            row['meets_threshold']=row['cma_free_bytes']>=row['required_cma_bytes'] and row['mem_available_bytes']>=row['required_mem_available_bytes']
            return row
        result['loaded_capacity']=capacity(loaded)
        if len(allocations)!=7 or runtime.maximum_weight_window_bytes!=6963200:raise RuntimeError('Seven buffer geometry differs')

        import numpy as np
        
        from m368_stage_policy import FAMILIES
        from board_safety import safe_to_release
        policy.seal(allocations,int(TARGET_BUILD,16))
        result['production_threshold_would_admit']=result['loaded_capacity']['meets_threshold']
        result['diagnostic_admitted']=True
        result['additional_cma_requests_allowed']=False
        result['diagnostic_ps_growth_limit_bytes']=1024<<20
        result['diagnostic_ps_available_margin_bytes']=64<<20
        if runtime.host_calls or runtime.logical_calls: raise RuntimeError('Unexpected prior transaction')
        # Bootstrap completes one legal transaction on this very Overlay.
        packet=(CANDIDATE/'build_packet.bin').read_bytes()
        golden=(CANDIDATE/'build_golden.bin').read_bytes()
        if len(packet)!=2576 or len(golden)!=4096: raise RuntimeError('Minimal fixture size differs')
        for buffer in runtime.staged_buffers: buffer[:144]=0;buffer.sync_to_device()
        runtime.input_buffer[:len(packet)]=np.frombuffer(packet,np.uint8);runtime.input_buffer.sync_to_device()
        runtime.output_buffer[:len(golden)]=0xa5;runtime.output_buffer.sync_to_device()
        for reg,buffer in zip(base.REG_POINTERS,runtime.staged_buffers):base.write_u64(runtime.kernel,reg,base.physical_address(buffer))
        runtime.kernel.write(base.REG_CONFIG,0x10201)
        policy.capture('before-same-overlay-legal-minimal',True)
        policy.active=policy.ever=True;policy.completed=False
        result['fpga_transactions']=1
        runtime.dma.recvchannel.transfer(runtime.output_buffer,nbytes=len(golden))
        runtime.kernel.write(base.REG_AP_CTRL,1)
        runtime.dma.sendchannel.transfer(runtime.input_buffer,nbytes=len(packet))
        minimal=base.wait_transaction(runtime.kernel,runtime.dma,10.0)
        if not safe_to_release(minimal) or minimal['ap_return']!=policy.build:raise RuntimeError('Minimal transaction completion unsafe')
        policy.active=False;policy.completed=True
        runtime.output_buffer.sync_from_device()
        if bytes(memoryview(runtime.output_buffer)[:len(golden)])!=golden:raise RuntimeError('Minimal full output differs')
        runtime._programmed_weight_addresses=None;runtime._programmed_config=None
        result['same_overlay_minimal_proof']=dict(snapshot=minimal,output_bytes=len(golden),full_output_exact=True)
        policy.capture('after-same-overlay-legal-minimal',True)
        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate',blocked))
        patch(runtime,'allocate',forbid('extra-DMA.runtime.allocate',blocked))
        def resident():
            return (initialized and not runtime._m368_closed and engine.board is runtime
                and engine.language is not None and engine.vision is not None and engine.tokenizer is not None
                and len(allocations)==7 and not result['released_buffers'] and not blocked
                and [int(x.nbytes) for x in allocations]==SHAPES and policy.safe())
        for name in ('_launch_prepacked','_launch_once'):
            patch(runtime,name,policy.wrap_launch(getattr(runtime,name),name))
        from m368_head_observer import bind as bind_head
        observed_head,proof=bind_head(runtime._execute,policy,runtime.head_contract.chains)
        if proof['original_module']!='m230_prefill_runtime' or proof['original_function']!='M230PrefillRuntime._execute':raise RuntimeError('Actual head executor identity differs')
        result['head_observer_proof']=proof
        patch(runtime,'_execute',forbid('head.not-admitted',blocked))
        expected=json.loads((HERE/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))
        frames=[]
        for name,digest in FRAMES.items():
            file=ADDON/'fixtures'/name
            if sha256(file)!=digest:raise RuntimeError('Frozen video file identity differs')
            frames.append(np.load(file,allow_pickle=False))
        frames=np.ascontiguousarray(np.stack(frames))
        if frames.shape!=(4,448,448,3) or frames.dtype!=np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest()!=STACK_SHA:raise RuntimeError('Frozen frame tensor differs')
        result['frames_sha256']=STACK_SHA
        model=engine.language;captured={}
        capture=GateUpCapture(model._family,expected['baseline']['families'],policy,EVIDENCE)
        patch(model,'_family',capture)
        original_prefill=model.prefill
        def observed_prefill(hidden):
            if captured:raise RuntimeError('Unexpected second prefill')
            captured['input']=tensor(hidden)
            if captured['input']!=expected['baseline']['input'] or hidden.shape!=(159,2560):raise RuntimeError('Original159 video input differs')
            policy.capture('before-language-capture',True)
            result['model_forward_calls']=1
            result['ps_prefetch_enabled']=False
            result['original_parser_workers']=1
            result['extra_pynq_allocations']=len(allocations)-7
            original_prefill(hidden)
            raise RuntimeError('Original prefill returned instead of bounded capture')
        patch(model,'prefill',observed_prefill)
        original_preprocess=m276_video_runtime.preprocess
        def observed_preprocess(frames):
            answer=original_preprocess(frames)
            result['preprocessed']={k:tensor(v) for k,v in sorted(answer.items())}
            if result['preprocessed']!=visual_reference['preprocessed']:raise RuntimeError('Frozen preprocessing reference differs')
            policy.capture('after-preprocess',True)
            return answer
        patch(m276_video_runtime,'preprocess',observed_preprocess)
        original_tokenize=m276_video_runtime.tokenize
        def observed_tokenize(*a,**kw):
            ids=original_tokenize(*a,**kw)
            if ids!=visual_reference['prompt_token_ids']:raise RuntimeError('Exact159 token identities differ')
            result['prompt_token_ids']=ids
            return ids
        patch(m276_video_runtime,'tokenize',observed_tokenize)
        # Loader-only reuse is complete; original request tokenization remains original.
        patch(tokenizers,'Tokenizer',original_tokenizer)
        original_progress=engine.vision.progress_callback if hasattr(engine.vision,'progress_callback') else None
        for wrapped in engine.vision.vision.encoder.layers:
            callback=wrapped.progress_callback
            def memory_progress(name,payload,_original=callback):
                if _original is not None:_original(name,payload)
                policy.capture('vision:'+name+':'+str(payload.get('index')),True)
            patch(wrapped,'progress_callback',memory_progress)
        request=SimpleNamespace(prompt=m276_video_runtime.M276_KNIFE_PROMPT,max_new_tokens=1,frames_rgb_u8=frames)
        policy.capture('before-original-video-stream',True);policy.begin_sampling()
        events=[];boundary_reached=False
        try:
            for event,payload in engine.stream(request):
                events.append((event,payload))
                if event=='stage':policy.capture('stream-stage:'+payload['name'],True)
                print('M390_EVENT '+event,flush=True)
        except CaptureBoundary:
            boundary_reached=True
        policy.capture('after-bounded-video-capture',True);policy.stop_sampling()
        evidence=runtime.evidence()
        result['boundary_reached']=boundary_reached
        result['captured_families']=capture.families
        result['actual_gate_up_fixtures']=capture.fixtures
        result['attempted_after_boundary']=capture.attempted_after_boundary
        result['input']=captured.get('input')
        result['events']=events
        result['decoder']=engine.vision.decoder_evidence()
        result['partial_call_contract']={k:evidence[k] for k in ('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','scale_attempts','stage_bytes')}
        attempts=evidence['scale_attempts']
        expected_attempts=expected['baseline']['scale_attempts'][:20]
        if not boundary_reached or not capture.done or len(capture.families)!=4 or capture.attempted_after_boundary:raise RuntimeError('Bounded capture incomplete')
        if attempts!=expected_attempts or evidence['logical_calls']!=20 or evidence['host_calls']!=20 or len(result['transactions'])!=20:raise RuntimeError('Original layer0 prefix physical/logical/retry accounting differs')
        if evidence['scale_retry_count'] or evidence['pipeline_retry_launches'] or evidence['fused_nonfinite_detections']:raise RuntimeError('Unexpected layer0 retry')
        if any(r['layer']!=0 or r['family'] not in ('q','kv','attention_out','gate_up') for r in result['transactions']):raise RuntimeError('Transaction escaped capture prefix')
        if [p['name'] for n,p in events if n=='stage']!=['preprocess','vision','prefill'] or any(n!='stage' for n,p in events):raise RuntimeError('Unexpected stream output after boundary')
        if result['preprocessed']!=visual_reference['preprocessed'] or result['visual_features']!=visual_reference['visual_features'] or result['prompt_token_ids']!=visual_reference['prompt_token_ids']:raise RuntimeError('Actual visual/input identity differs')
        if not resident() or any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Capture completion/worker lifecycle unproven')
        result['capture_pass']=True
        result['numerical_pass']=False
        result['fixed_video_diagnostic_pass']=False
        result['status']='PASS_M390_ACTUAL_GATE_UP_CAPTURE'
        result['memory_capacity_proven']=False
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
    except CapacityRejected as exc:
        result['status'] = 'FAIL_COMPLETE_RUNTIME_CAPACITY'
        result['errors'].append(type(exc).__name__+': '+str(exc))
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback'] = traceback.format_exc()
    finally:
        # Keep guards installed until all resource cleanup is finished.
        unsafe=unsafe or ps_session is not None
        result['fpga_transactions']=(1 if policy is not None and policy.ever else 0)+len(result.get('transactions',[]))
        if policy is not None:
            try:policy.stop_sampling()
            except BaseException as exc:unsafe=True;result['errors'].append('Observer retained: '+str(exc))
        if runtime is not None:
            result['overlay_loaded'] = hasattr(runtime,'overlay')
            result['host_calls']=getattr(runtime,'host_calls',-1)
            result['logical_calls']=getattr(runtime,'logical_calls',-1)
            if hasattr(runtime,'dma') and hasattr(runtime,'kernel'):
                result['final_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
            unsafe = unsafe or not initialized or policy is None or not policy.safe()
        elif allocations:
            unsafe = True
        if not unsafe:
            try:
                result['ps_slot_port_count_before_release']=len(slots)
                slots.clear()
                result['ps_slot_released']=True
                if engine is not None and engine.board is not None:
                    engine.close(); engine.language = engine.vision = engine.tokenizer = None
                elif initialized and not runtime._m368_closed: runtime.close()
                elif not initialized:
                    for buffer in reversed(allocations):
                        if not getattr(buffer,'freed',False): buffer.freebuffer()
                result['safe_buffers_released'] = True
                result['original_buffer_release_count']=len(result['released_buffers'])
                if len(result['released_buffers'])!=len(allocations):
                    raise RuntimeError('Original allocation/free accounting incomplete')
                # No GC/trim experiment: use ordinary owned object cleanup only.
                mark('after-safe-close-and-PS-object-disposal')
            except BaseException as exc:
                unsafe = True; result['errors'].append('Cleanup failed, process retained: '+str(exc))
        result['unsafe_buffers_retained'] = unsafe
        if unsafe: result['status'] = 'FAIL_UNSAFE_RETAINED'
        elif result['errors'] and result['status'] != 'FAIL_COMPLETE_RUNTIME_CAPACITY': result['status'] = 'FAIL'
        result['gate_return_code']=0 if result['status']=='PASS_M390_ACTUAL_GATE_UP_CAPTURE' else 1
        result['memory_capacity_proven']=False
        if not unsafe:
            registry.restore_all(completion_proven=True,release_proven=True)
            result['patch_registry_cleared']=not registry.entries
            if runtime is not None and hasattr(runtime,'overlay'):
                try:
                    restored_env=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),'--expected-package-manifest-sha256',STABLE_SHA,'--result',str(EVIDENCE/'stable_restore_environment.json')],timeout=90)
                    if restored_env.returncode: raise RuntimeError('Stable restore environment rejected')
                    from pynq import Overlay
                    restored_overlay=Overlay(str(STABLE/'overlay/m120_m89x2_t32.bit'),download=True)
                    result['stable_overlay_reloaded']=True
                    result['stable_bit_sha256']=sha256(STABLE/'overlay/m120_m89x2_t32.bit')
                    result['stable_restore_transaction_submitted']=False
                    from m120_board_common import KERNEL_NAME,DMA_NAME
                    result['stable_restore_snapshot']=base.transaction_snapshot(getattr(restored_overlay,KERNEL_NAME),getattr(restored_overlay,DMA_NAME))
                except BaseException as exc:
                    result['errors'].append('Stable reload rejected: '+str(exc));result['status']='FAIL';result['gate_return_code']=1;result['memory_capacity_proven']=False

        result['elapsed_s_diagnostic_not_performance'] = time.monotonic()-started
        result['next_step'] = 'Capture identity/lifecycle adjudication only; CPU SiLU component after raw/closure triad, no whole model or performance rerun'
        if result['elapsed_s_diagnostic_not_performance'] > 900:
            result['errors'].append('Diagnostic budget exceeded; no automatic retry')
            result['status']='FAIL_BUDGET'; result['gate_return_code']=1; result['memory_capacity_proven']=False
        print('M390_FAILURE_OR_COMPLETION_STATE '+json.dumps(dict(gate_rc=result['gate_return_code'],candidate_snapshot=result.get('final_snapshot'),stable_snapshot=result.get('stable_restore_snapshot'),fpga_transactions=result['fpga_transactions'],last_transaction=result.get('transactions',[])[-1:])),flush=True)
        write_json(path,result)
        print('M390_RESULT_SAVED status='+result['status']+' sha256='+sha256(path),flush=True)
        stopped.set()
        if unsafe:
            from m390_export_result import emit_saved
            emit_saved(args.case)
            print('M390_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return result['gate_return_code']


if __name__ == '__main__': raise SystemExit(main())
