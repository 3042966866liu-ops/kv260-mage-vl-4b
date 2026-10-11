"""Bounded original video load/GC/trim observation. All inference is blocked."""
import argparse
import base64
import fcntl
import gc
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
from memory_lifecycle import memory_snapshot, glibc_trim
HERE = Path(__file__).resolve().parent
EVIDENCE = Path('/home/ubuntu/m346_load_memory_evidence_01')
PRIOR_SHA = 'b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'
REQUIRED_FREE = 27852800 + (64 << 20)
BLOCKED_BOARD_METHODS = ('_execute', '_launch_once', '_launch_prepacked', '_stage',
                         'language_family_many', 'language_family', 'lm_head')


def memory_eligibility(snapshot):
    free = snapshot['system_bytes']['CmaFree']
    return dict(cma_free_bytes=free, required_free_bytes=REQUIRED_FREE, meets_load_only_threshold=free >= REQUIRED_FREE,
                serving_after_vision_capacity_proven=False, numerical_or_performance_pass=False)


def forbid(name, blocked):
    def stop(*args, **kwargs):
        blocked.append(name)
        raise RuntimeError('Load-only probe forbids inference/transaction: ' + name)
    return stop


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); args = parser.parse_args()
    path = EVIDENCE / 'load-memory.json'
    if path.exists(): raise RuntimeError('Immutable load-only result exists; collect only')
    result = dict(status='FAIL', gate_level='load-only-memory-diagnostic', build_id='0x4D395832', errors=[], stages=[],
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                  overlay_loaded=False, model_forward_calls=0, blocked_inference_attempts=[], allocated_buffers=[],
                  experiment_scope='Original complete video runtime load; retained objects before GC and malloc_trim; no forward/PL transaction')
    runtime = engine = base = lock = None
    initialized = unsafe = False
    allocations = []; restorations = []
    phase, stopped = ['package'], threading.Event()
    started = time.monotonic()
    def heartbeat():
        warned = False
        while not stopped.wait(30):
            elapsed = time.monotonic() - started
            print('M346_HEARTBEAT phase=' + phase[0] + ' elapsed_s=' + str(round(elapsed,1)), flush=True)
            if elapsed > 600 and not warned:
                warned = True
                print('M346_LOAD_BUDGET_EXCEEDED_RETAIN_PROCESS_NO_KILL', flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    def mark(name):
        phase[0] = name
        observed = memory_snapshot()
        for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
            if line.startswith('CmaTotal:'): observed['system_bytes']['CmaTotal'] = int(line.split()[1]) * 1024
        row = dict(name=name, elapsed_s=time.monotonic()-started, memory=observed)
        result['stages'].append(row)
        print('M346_MEMORY ' + json.dumps(row, separators=(',', ':')), flush=True)
        write_json(EVIDENCE / 'progress.json', result)
        return observed
    def patch(obj, name, replacement):
        original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)
        return original
    try:
        verify_self(HERE,args.manifest_sha); result['manifest_sha256'] = args.manifest_sha
        prerequisite = json.loads((HERE/'M345_FAILURE_PREREQUISITE.json').read_text(encoding='utf-8'))
        if prerequisite['board_result_sha256'] != PRIOR_SHA or prerequisite['status'] != 'FAIL_CMA_REJECTION_SAFELY_CLOSED' or prerequisite['candidate_prefill_launched']:
            raise RuntimeError('Exact safely closed M345 CMA prerequisite differs')
        result['prior_board_sha256'] = PRIOR_SHA
        if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')
        hardware = json.loads((HERE/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if hardware['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED': raise RuntimeError('Stable same-SHA hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        boot = Path('/boot/firmware/boot.scr.uimg'); before_boot = sha256(boot)
        before_cmd = Path('/proc/cmdline').read_text(encoding='utf-8')
        mark('initial-before-source-and-runtime-imports')
        closure = json.loads((HERE/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
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
        checked = subprocess.run([sys.executable,'-B',str(HERE/'m120_board_env_preflight.py'),'--candidate',str(STABLE),
            '--expected-package-manifest-sha256',STABLE_SHA,'--result',str(envpath)],timeout=90)
        if checked.returncode: raise RuntimeError('Fixed environment rejected; no overlay')
        result['environment_sha256'] = sha256(envpath)
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*a,**kw):
            buffer = original_allocate(*a,**kw); allocations.append(buffer)
            result['allocated_buffers'].append(dict(bytes=int(buffer.nbytes),address=int(base.physical_address(buffer))))
            return buffer
        board_cls = m243_video_server.M238PrefillRuntime
        blocked = result['blocked_inference_attempts']
        class OwnedBoard(board_cls):
            def __init__(self,*a,**kw):
                nonlocal runtime,initialized
                runtime = self; self._m346_closed = False
                mark('before-original-M238-constructor')
                super().__init__(*a,**kw); initialized = True
                mark('after-original-M238-and-all-DMA-buffer-allocations')
            def close(self):
                super().close(); self._m346_closed = True
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
        result['load_only_eligibility_before_gc'] = memory_eligibility(loaded)
        result['gc_collected'] = gc.collect()
        after_gc = mark('retained-runtime-after-PS-GC')
        result['load_only_eligibility_after_gc'] = memory_eligibility(after_gc)
        result['trim'] = glibc_trim()
        if not result['trim'].get('called'): raise RuntimeError('Actual board malloc_trim unavailable')
        trimmed = mark('retained-runtime-after-PS-glibc-trim')
        result['load_only_eligibility_after_trim'] = memory_eligibility(trimmed)
        time.sleep(2); mark('retained-runtime-after-trim-plus-2s')
        time.sleep(3); mark('retained-runtime-after-trim-plus-5s')
        if runtime.host_calls != 0 or runtime.logical_calls != 0 or blocked: raise RuntimeError('Unexpected transaction/inference')
        result['boot_unchanged'] = sha256(boot) == before_boot
        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text(encoding='utf-8') == before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']: raise RuntimeError('Protected identities changed')
        result['status'] = 'PASS_LOAD_ONLY_DIAGNOSTIC'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback'] = traceback.format_exc()
    finally:
        # Keep guards installed until all resource cleanup is finished.
        if runtime is not None:
            result['overlay_loaded'] = hasattr(runtime,'overlay')
            if hasattr(runtime,'dma') and hasattr(runtime,'kernel'):
                result['final_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
            unsafe = getattr(runtime,'host_calls',0) != 0 or getattr(runtime,'logical_calls',0) != 0
        if not unsafe:
            try:
                if engine is not None and engine.board is not None:
                    engine.close(); engine.language = engine.vision = engine.tokenizer = None
                elif initialized and not runtime._m346_closed: runtime.close()
                elif not initialized:
                    for buffer in reversed(allocations):
                        if not getattr(buffer,'freed',False): buffer.freebuffer()
                result['safe_buffers_released'] = True
                gc.collect(); result['post_close_trim'] = glibc_trim()
                mark('after-safe-close-and-PS-object-disposal')
            except BaseException as exc:
                unsafe = True; result['errors'].append('Cleanup failed, process retained: '+str(exc))
        result['unsafe_buffers_retained'] = unsafe
        if unsafe or result['errors']: result['status'] = 'FAIL'
        if not unsafe:
            for obj,name,original in reversed(restorations): setattr(obj,name,original)
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic()-started
        result['next_step'] = 'Interpret load-only memory evidence; remain at fixed159-video CMA failure level; no E2E/performance gate unlocked'
        write_json(path,result); raw = path.read_bytes()
        print('M346_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
        chunks = [raw[i:i+1800] for i in range(0,len(raw),1800)]
        for i,chunk in enumerate(chunks): print('M346_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(chunk).decode(),flush=True)
        print('M346_SUMMARY='+json.dumps(dict(status=result['status'],errors=result['errors'],unsafe=unsafe)),flush=True)
        stopped.set()
        if unsafe:
            print('M346_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return 0 if result['status'] == 'PASS_LOAD_ONLY_DIAGNOSTIC' else 1


if __name__ == '__main__': raise SystemExit(main())
