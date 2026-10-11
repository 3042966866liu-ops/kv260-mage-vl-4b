"""Balanced fixed159 video request timing; production admission unchanged."""
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
sys.dont_write_bytecode = True
from measurement import sha256, write_json
from m370_patch_scope import PatchScope
from owned_buffer_release import OwnedBufferRelease
from m363_package_identity import verify_frozen_package
from m363_observers import observe_call,tokenizer_proxy,retained_inventory,mapping_inventory,ROLES
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, RELEASE,FRAMES,STACK_SHA
from types import SimpleNamespace
from m368_video_contract import tensor,check_call_contract,validate_stream
from memory_lifecycle import memory_snapshot
from ps_slot_capacity import CapacityRejected
from m369_light_policy import StagePolicy
from m368_stage_policy import SHAPES
from m395_trials import run_trials
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
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); parser.add_argument('case',choices=('B1',)); parser.add_argument('--enable-staged-video',action='store_true'); args = parser.parse_args()
    is_candidate=True  # Both SiLU variants use identical current parallel hardware
    TARGET=CANDIDATE if is_candidate else STABLE
    TARGET_SHA=CAND_SHA if is_candidate else STABLE_SHA
    TARGET_BUILD='0x4D333537' if is_candidate else '0x4D395832'
    EVIDENCE=Path('/home/ubuntu/m395_silu_performance_01')
    if not args.enable_staged_video: raise RuntimeError('M395 disabled by default')
    path = EVIDENCE / 'load-memory.json'
    if EVIDENCE.exists(): raise RuntimeError('Immutable evidence directory exists; collect only')
    EVIDENCE.mkdir(mode=0o700,parents=True,exist_ok=False)
    result = dict(status='FAIL', gate_level='balanced-fixed159-video-original-expression-versus-SiLU-workspace', build_id=TARGET_BUILD,case=args.case,io_events=[],common_runner_sha256=sha256(Path(__file__)),cache_policy='natural cache; no clearing; identical policy is not identical cache residency', errors=[], stages=[],
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                  overlay_loaded=False, model_forward_calls=0, blocked_inference_attempts=[], allocated_buffers=[],
                  experiment_scope='Original complete runtime objects retained; independent fixed159-token diagnostic including36 layers/head, B ordinary5.900390625MiB workspace, no extra CMA; original visual plus language and head; production policy unchanged',
                  worker_started=False, ps_slot={}, released_buffers=[], fpga_transactions=0, memory_capacity_proven=False, serving_after_vision_capacity_proven=False, gate_return_code=1)
    runtime = engine = base = lock = policy = None
    initialized = unsafe = False
    allocations = []; slots = []; registry = PatchScope()
    phase, stopped = ['package'], threading.Event()
    started = time.monotonic()
    def heartbeat():
        warned = False
        while not stopped.wait(30):
            elapsed = time.monotonic() - started
            print('M395_HEARTBEAT phase=' + phase[0] + ' elapsed_s=' + str(round(elapsed,1)), flush=True)
            if elapsed > 3600 and not warned:
                warned = True
                print('M395_LOAD_BUDGET_EXCEEDED_RETAIN_PROCESS_NO_KILL', flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    def mark(name):
        phase[0] = name
        observed = memory_snapshot()
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            if line.startswith('CmaTotal:'): observed['system_bytes']['CmaTotal'] = int(line.split()[1]) * 1024
        row = dict(name=name, elapsed_s=time.monotonic()-started, memory=observed)
        result['stages'].append(row)
        print('M395_MEMORY ' + json.dumps(row, separators=(',', ':')), flush=True)
        write_json(EVIDENCE / 'progress.json',dict(case=args.case,stage=row,allocated_buffers=result['allocated_buffers'],released_buffers=result['released_buffers']))
        return observed
    def patch(obj, name, replacement):
        return registry.patch(obj,name,replacement)
    try:
        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha
        numeric=json.loads((HERE/'NUMERIC_PREREQUISITE.json').read_text(encoding='utf-8'))
        if numeric['status']!='PASS_INDEPENDENT_VIDEO_CAPACITY_AND_NUMERICS' or not numeric['numerical_pass'] or numeric['raw_status']!='PASS_M368_FIXED_VIDEO_DIAGNOSTIC':raise RuntimeError('Synchronized actual-video numeric prerequisite differs')
        prior=json.loads((HERE/'STAGE_PREREQUISITE.json').read_text(encoding='utf-8'))
        if prior['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prior['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Independent text prerequisite differs')
        visual_reference=json.loads((HERE/'VISUAL_EXPECTED.json').read_text(encoding='utf-8'))
        if visual_reference['status']!='PASS_MISSING_PS_VISUAL_REFERENCE' or visual_reference['gate_return_code'] or visual_reference['fpga_transactions'] or visual_reference['language_forward_calls']:raise RuntimeError('Missing-only visual reference prerequisite differs')
        prerequisite_path = HERE/'M357_COMPARE_PREREQUISITE.json'
        prerequisite = json.loads(prerequisite_path.read_text(encoding='utf-8'))
        if sha256(prerequisite_path) != PRIOR_SHA or prerequisite['status'] != 'PASS_M357_COMPARE' or not prerequisite['chain_performance_pass'] or not prerequisite['stable_restored']:
            raise RuntimeError('Exact M357 balanced single-chain prerequisite differs')
        result['prior_board_sha256'] = PRIOR_SHA
        video_path=Path('/home/ubuntu/m394_silu_video_01/B1/load-memory.json')
        video=json.loads(video_path.read_text(encoding='utf-8'))
        if sha256(video_path)!='bff53238edcbfc611e7c3ca275113294bd75c70106af882115b9f880e03d256c' or video['status']!='PASS_M394_SILU_VIDEO_NUMERICAL' or video['gate_return_code'] or not video['scope_weakref_dead'] or not video['safe_buffers_released']:raise RuntimeError('Actual SiLU video prerequisite differs')
        result['silu_video_prerequisite_sha256']=sha256(video_path)
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
                result['vision_forward_calls']=result.get('vision_forward_calls',0)+1
                policy.capture('before-original-visual-forward',True)
                visual=super().__call__(*a,**kw)
                policy.capture('after-original-visual-forward',True)
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
        patch(tokenizers,'Tokenizer',original_tokenizer)
        result['build_id']='0x4D333537'
        result['production_policy_changed']=False
        result['production_threshold_would_admit']=result['loaded_capacity']['meets_threshold']
        def new_board(variant,index):
            nonlocal runtime,policy,initialized,allocations
            global TARGET,TARGET_SHA,TARGET_BUILD
            if not runtime._m368_closed:raise RuntimeError('Previous runtime not safely closed')
            initialized=False;allocations=[]
            result['allocated_buffers']=[];result['released_buffers']=[];result['transactions']=[]
            TARGET=CANDIDATE
            TARGET_SHA=CAND_SHA
            TARGET_BUILD='0x4D333537'
            verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=False)
            envpath=EVIDENCE/('trial_environment_'+str(index)+'.json')
            checked=subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(TARGET),'--expected-package-manifest-sha256',TARGET_SHA,'--result',str(envpath)],timeout=90)
            if checked.returncode:raise RuntimeError('Trial environment rejected; no overlay')
            patch(base,'BUILD_ID',int(TARGET_BUILD,16))
            patch(video_server,'BUILD_ID',TARGET_BUILD)
            runtime=OwnedBoard(STABLE/'overlay/m120_m89x2_t32.bit',config['weights_root']/'language_fourport',config['weights_root']/'lmhead_fourport',STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',STABLE/'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json',weight_mode='staged-low-cma')
            policy=StagePolicy(result,lambda:runtime,base)
            policy.seal(allocations,int(TARGET_BUILD,16))
            return runtime,policy
        def restore_trial(owner,owned_policy):
            if not owner._m368_closed or not owned_policy.safe():raise RuntimeError('Trial lifecycle not proven; retain owner')
            count=registry.restore_owner(owner,completion_proven=True,release_proven=True)
            if any(e[0] is owner for e in registry.entries):raise RuntimeError('Trial owner retained by registry')
            return count
        run_trials(engine,runtime,policy,base,CANDIDATE,HERE,result,new_board,patch,restore_trial)
        result['boot_unchanged']=sha256(boot)==before_boot
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:raise RuntimeError('Protected identities changed')
        result['status']='PASS_M395_LIGHT_VIDEO_MEASUREMENTS'
    except CapacityRejected as exc:
        result['status'] = 'FAIL_COMPLETE_RUNTIME_CAPACITY'
        result['errors'].append(type(exc).__name__+': '+str(exc))
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback'] = traceback.format_exc()
    finally:
        # Keep guards installed until all resource cleanup is finished.
        unsafe=unsafe or result.get('retained_SiLU_scope',False)
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
        result['gate_return_code']=0 if result['status']=='PASS_M395_LIGHT_VIDEO_MEASUREMENTS' else 1
        result['memory_capacity_proven']=False
        if not unsafe:
            registry.restore_all(completion_proven=True,release_proven=True)
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
        result['next_step'] = 'Adjudicate all8 original full-request times and order variability; no automatic promotion'
        if result['elapsed_s_diagnostic_not_performance'] > 3600:
            result['errors'].append('Diagnostic budget exceeded; no automatic retry')
            result['status']='FAIL_BUDGET'; result['gate_return_code']=1; result['memory_capacity_proven']=False
        print('M395_FAILURE_OR_COMPLETION_STATE '+json.dumps(dict(gate_rc=result['gate_return_code'],candidate_snapshot=result.get('final_snapshot'),stable_snapshot=result.get('stable_restore_snapshot'),fpga_transactions=result['fpga_transactions'],last_transaction=result.get('transactions',[])[-1:])),flush=True)
        write_json(path,result)
        print('M395_RESULT_SAVED status='+result['status']+' sha256='+sha256(path),flush=True)
        stopped.set()
        if unsafe:
            from m395_export_result import emit_saved
            emit_saved(args.case)
            print('M395_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return result['gate_return_code']


if __name__ == '__main__': raise SystemExit(main())
