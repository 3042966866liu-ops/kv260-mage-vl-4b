"""M357 complete runtime capacity only. All inference is blocked."""
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
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, RELEASE
from memory_lifecycle import memory_snapshot
from ps_slot_capacity import (eligibility, require_capacity, materialize_slot, never_submitted_release, CapacityRejected)
HERE = Path(__file__).resolve().parent
CANDIDATE = Path('/home/ubuntu/m357_candidate_01')
CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'
EVIDENCE = Path('/home/ubuntu/m358_candidate_capacity_01')
PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'
BLOCKED_BOARD_METHODS = ('_execute', '_launch_once', '_launch_prepacked', '_stage',
                         'language_family_many', 'language_family', 'lm_head')


def forbid(name, blocked):
    def stop(*args, **kwargs):
        blocked.append(name)
        raise RuntimeError('Load-only probe forbids inference/transaction: ' + name)
    return stop


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); parser.add_argument('--enable-load-only',action='store_true'); args = parser.parse_args()
    if not args.enable_load_only: raise RuntimeError('M358 disabled by default')
    path = EVIDENCE / 'load-memory.json'
    if EVIDENCE.exists(): raise RuntimeError('Immutable evidence directory exists; collect only')
    EVIDENCE.mkdir(mode=0o700,parents=False,exist_ok=False)
    result = dict(status='FAIL', gate_level='load-only-memory-diagnostic', build_id='0x4D333537', errors=[], stages=[],
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                  overlay_loaded=False, model_forward_calls=0, blocked_inference_attempts=[], allocated_buffers=[],
                  experiment_scope='Original complete video runtime with M357 bit; no extra CMA/PS slot, GC/trim/forward/worker/PL transaction',
                  worker_started=False, ps_slot={}, released_buffers=[], fpga_transactions=0, memory_capacity_proven=False, serving_after_vision_capacity_proven=False, gate_return_code=1)
    runtime = engine = base = lock = None
    initialized = unsafe = False
    allocations = []; restorations = []; slots = []
    phase, stopped = ['package'], threading.Event()
    started = time.monotonic()
    def heartbeat():
        warned = False
        while not stopped.wait(30):
            elapsed = time.monotonic() - started
            print('M358_HEARTBEAT phase=' + phase[0] + ' elapsed_s=' + str(round(elapsed,1)), flush=True)
            if elapsed > 600 and not warned:
                warned = True
                print('M358_LOAD_BUDGET_EXCEEDED_RETAIN_PROCESS_NO_KILL', flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    def mark(name):
        phase[0] = name
        observed = memory_snapshot()
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            if line.startswith('CmaTotal:'): observed['system_bytes']['CmaTotal'] = int(line.split()[1]) * 1024
        row = dict(name=name, elapsed_s=time.monotonic()-started, memory=observed)
        result['stages'].append(row)
        print('M358_MEMORY ' + json.dumps(row, separators=(',', ':')), flush=True)
        write_json(EVIDENCE / 'progress.json', result)
        return observed
    def patch(obj, name, replacement):
        original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)
        return original
    try:
        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha
        prerequisite_path = HERE/'M357_COMPARE_PREREQUISITE.json'
        prerequisite = json.loads(prerequisite_path.read_text(encoding='utf-8'))
        if sha256(prerequisite_path) != PRIOR_SHA or prerequisite['status'] != 'PASS_M357_COMPARE' or not prerequisite['chain_performance_pass'] or not prerequisite['stable_restored']:
            raise RuntimeError('Exact M357 balanced single-chain prerequisite differs')
        result['prior_board_sha256'] = PRIOR_SHA
        if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')
        hardware = json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if hardware['status'] != 'PASS_ALL_NEW_CIRCUIT_PREREQUISITES': raise RuntimeError('Stable same-SHA hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
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
        mark('after-exact-runtime-imports')
        spec = importlib.util.spec_from_file_location('release_preflight',RELEASE/'scripts/preflight.py')
        preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
        inspected = preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_text(encoding='utf-8')),port_check=True)
        result['release_preflight'] = {k:inspected[k] for k in ('status','build_id','missing','hash_or_identity_mismatch','port_free')}
        if inspected['status'] != 'READY_FOR_BOARD_PREFLIGHT': raise RuntimeError('Release assets rejected')
        mark('after-release-asset-hashes')
        d = RELEASE/'deployment/mage_vl4b'
        config = video_server.make_config(d/'m181_m120_video_board_candidate',STABLE,RELEASE/'external_assets/weights',
            RELEASE/'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(config['tokenizer'])); del tokenizer
        mark('after-tokenizer-asset-preconstruction')
        envpath = EVIDENCE/'environment.json'
        phase[0] = 'fixed-environment-preflight'
        verify_self(CANDIDATE,CAND_SHA)
        checked = subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(CANDIDATE),
            '--expected-package-manifest-sha256',CAND_SHA,'--result',str(envpath)],timeout=90)
        if checked.returncode: raise RuntimeError('Fixed environment rejected; no overlay')
        result['environment_sha256'] = sha256(envpath)
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*a,**kw):
            buffer = original_allocate(*a,**kw); allocations.append(buffer)
            row=dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer)))
            result['allocated_buffers'].append(row)
            original_free=buffer.freebuffer
            def guarded_free():
                observed=base.transaction_snapshot(runtime.kernel,runtime.dma)
                if not never_submitted_release(observed,runtime.host_calls,runtime.logical_calls,result['blocked_inference_attempts'],len(allocations)):
                    raise RuntimeError('Never-submitted lifecycle no longer proven; retain all remaining buffers')
                if row in result['released_buffers']:
                    raise RuntimeError('Duplicate original-buffer free refused')
                original_free()
                result['released_buffers'].append(row)
            buffer.freebuffer=guarded_free
            return buffer
        board_cls = m243_video_server.M238PrefillRuntime
        blocked = result['blocked_inference_attempts']
        class OwnedBoard(board_cls):
            def __init__(self,*a,**kw):
                nonlocal runtime,initialized
                runtime = self; self._m358_closed = False
                mark('before-original-M238-constructor')
                if not a or Path(a[0]).resolve() != (STABLE/'overlay/m120_m89x2_t32.bit').resolve(): raise RuntimeError('Original constructor bit argument differs')
                super().__init__(CANDIDATE/'overlay/m120_m89x2_t32.bit',*a[1:],**kw); initialized = True
                mark('after-original-M238-and-all-DMA-buffer-allocations')
            def close(self):
                super().close(); self._m358_closed = True
        for name in BLOCKED_BOARD_METHODS: setattr(OwnedBoard,name,forbid('board.'+name,blocked))
        vision_cls = m222_video_server.M222PSVisionRuntime
        class ObservedVision(vision_cls):
            def __init__(self,*a,**kw):
                mark('before-original-PS-vision-constructor')
                super().__init__(*a,**kw)
                # Block the Torch tower too, while leaving construction intact.
                self.vision.forward = forbid('vision.tower.forward',blocked)
                mark('after-original-PS-vision-constructor')
            __call__ = forbid('vision.__call__',blocked)
        language_cls = m243_video_server.M241VideoLanguageModel
        class ObservedLanguage(language_cls):
            def __init__(self,*a,**kw):
                mark('before-original-M241-embedding-and-norm-constructor')
                super().__init__(*a,**kw)
                mark('after-original-M241-embedding-and-norm-constructor')
        for name in ('prefill','decode','_family'): setattr(ObservedLanguage,name,forbid('language.'+name,blocked))
        patch(pynq,'allocate',tracked_allocate)
        patch(m243_video_server,'M238PrefillRuntime',OwnedBoard)
        patch(m222_video_server,'M222PSVisionRuntime',ObservedVision)
        patch(m243_video_server,'M241VideoLanguageModel',ObservedLanguage)
        engine = m276_video_runtime.M276ShortPromptBinaryRuntime(config)
        engine.stream = forbid('engine.stream',blocked)
        mark('before-complete-original-engine-load')
        engine.load()
        result['overlay_loaded'] = True
        if engine.board is not runtime or not isinstance(engine.language,language_cls): raise RuntimeError('Complete real object closure differs')
        if runtime.host_calls != 0 or runtime.logical_calls != 0 or blocked: raise RuntimeError('Unexpected inference during load')
        result['host_calls'] = runtime.host_calls; result['logical_calls'] = runtime.logical_calls
        result['loaded_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
        result['release_lifecycle'] = 'No transaction submitted: guarded launch paths and exact constructors; DMASR=0 is not completed-DMA idle evidence'
        loaded = mark('complete-runtime-loaded-retained')
        def capacity(snapshot):
            mem=snapshot['system_bytes']
            row=dict(cma_free_bytes=mem['CmaFree'],mem_available_bytes=mem['MemAvailable'],required_cma_bytes=64<<20,required_mem_available_bytes=64<<20)
            row['meets_threshold']=row['cma_free_bytes']>=row['required_cma_bytes'] and row['mem_available_bytes']>=row['required_mem_available_bytes']
            return row
        result['loaded_capacity']=capacity(loaded)
        if len(allocations)!=7 or runtime.maximum_weight_window_bytes!=6963200: raise RuntimeError('Original allocation/window geometry differs')
        if not result['loaded_capacity']['meets_threshold']: raise CapacityRejected('M357 complete runtime reserve rejected: '+repr(result['loaded_capacity']))
        time.sleep(2)
        result['settled_capacity']=capacity(mark('complete-runtime-retained-plus-2s'))
        if not result['settled_capacity']['meets_threshold']: raise CapacityRejected('M357 settled reserve rejected: '+repr(result['settled_capacity']))
        result['extra_pynq_allocations']=len(allocations)-7
        result['load_only_capacity_pass']=True
        if runtime.host_calls != 0 or runtime.logical_calls != 0 or blocked: raise RuntimeError('Unexpected transaction/inference')
        result['boot_unchanged'] = sha256(boot) == before_boot
        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text(encoding='utf-8') == before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']: raise RuntimeError('Protected identities changed')
        result['status'] = 'PASS_M357_COMPLETE_RUNTIME_CAPACITY'
        result['memory_capacity_proven'] = True
    except CapacityRejected as exc:
        result['status'] = 'FAIL_M357_COMPLETE_RUNTIME_CAPACITY'
        result['errors'].append(type(exc).__name__+': '+str(exc))
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback'] = traceback.format_exc()
    finally:
        # Keep guards installed until all resource cleanup is finished.
        if runtime is not None:
            result['overlay_loaded'] = hasattr(runtime,'overlay')
            result['host_calls']=getattr(runtime,'host_calls',-1)
            result['logical_calls']=getattr(runtime,'logical_calls',-1)
            if hasattr(runtime,'dma') and hasattr(runtime,'kernel'):
                result['final_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
            unsafe = not initialized or not never_submitted_release(result.get('final_snapshot',{}),getattr(runtime,'host_calls',-1),getattr(runtime,'logical_calls',-1),result['blocked_inference_attempts'],len(allocations))
        elif allocations:
            unsafe = True
        if not unsafe:
            try:
                result['ps_slot_port_count_before_release']=len(slots)
                slots.clear()
                result['ps_slot_released']=True
                if engine is not None and engine.board is not None:
                    engine.close(); engine.language = engine.vision = engine.tokenizer = None
                elif initialized and not runtime._m358_closed: runtime.close()
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
        elif result['errors'] and result['status'] != 'FAIL_M357_COMPLETE_RUNTIME_CAPACITY': result['status'] = 'FAIL'
        result['gate_return_code']=0 if result['status']=='PASS_M357_COMPLETE_RUNTIME_CAPACITY' else 1
        result['memory_capacity_proven']=result['gate_return_code']==0
        if not unsafe:
            for obj,name,original in reversed(restorations): setattr(obj,name,original)
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
        result['next_step'] = 'Independent load-only adjudication and three-record synchronization; no video/worker/performance unlocked automatically'
        if result['elapsed_s_diagnostic_not_performance'] > 600:
            result['errors'].append('Diagnostic budget exceeded; no automatic retry')
            result['status']='FAIL_BUDGET'; result['gate_return_code']=1; result['memory_capacity_proven']=False
        print('M358_FAILURE_OR_COMPLETION_STATE '+json.dumps(dict(gate_rc=result['gate_return_code'],candidate_snapshot=result.get('final_snapshot'),stable_snapshot=result.get('stable_restore_snapshot'),fpga_transactions=0,input_bytes=0,output_bytes=0)),flush=True)
        write_json(path,result)
        print('M358_RESULT_SAVED status='+result['status']+' sha256='+sha256(path),flush=True)
        stopped.set()
        if unsafe:
            from m358_export_result import emit_saved
            emit_saved()
            print('M358_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return result['gate_return_code']


if __name__ == '__main__': raise SystemExit(main())
