"""One layer, original M238/M241, exact stable versus weight-prefetch outputs."""
import argparse
import base64
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
sys.dont_write_bytecode = True
import numpy as np
from board_safety import safe_to_release
from measurement import sha256, write_json
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from weight_prefetch import WeightPrefetchSession, RetainedBuffersError, chain_identity
from m343_layer_scope import bind

HERE = Path(__file__).resolve().parent
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
EVIDENCE = Path('/home/ubuntu/m343_single_layer_evidence_01')
PRIOR_SHA = '6fcc267aab9fdebbc3641a921d6518c9c266f31a9b7a515972dc30d9fa948aea'
FAMILIES = ('q', 'kv', 'attention_out', 'gate_up', 'mlp_down')


def cma_free():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('CmaFree:'):
            return int(line.split()[1]) * 1024
    raise RuntimeError('CmaFree unavailable')


def tensor(value):
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all():
        raise FloatingPointError('Nonfinite layer output')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())


def load_frozen():
    closure = json.loads((HERE / 'SOURCE_CLOSURE.json').read_text())
    for item in closure['files']:
        path = RELEASE / item['path']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise RuntimeError('Installed dependency mismatch: ' + item['path'])
    sys.path[:0] = [str(RELEASE / p) for p in closure['module_dirs']]
    modules = {}
    for name, relative in closure['modules'].items():
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != (RELEASE / relative).resolve():
            raise RuntimeError('Unexpected imported module: ' + name)
        modules[name] = module
    contract = json.loads((HERE / 'INPUT_CONTRACT.json').read_text())
    aux = np.load(STABLE / 'auxiliary/m77_text_aux_fp16.npz', allow_pickle=False)
    tensors = {name: aux[name] for name in aux.files}
    selected = contract['selected_embedding_ids']
    rows = np.asarray(tensors['model.language_model.embed_tokens.weight'], np.float32)
    original = np.stack([rows[selected.index(token)] for token in contract['prompt_token_ids']])
    hidden = np.tile(original, (6, 1))[:159].copy()
    if tensor(hidden) != contract['input_tensor']:
        raise RuntimeError('Frozen 159-token component input differs')
    return modules, tensors, hidden, closure


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manifest_sha')
    a = p.parse_args()
    result_path = EVIDENCE / 'single-layer.json'
    if result_path.exists():
        raise RuntimeError('Immutable layer result exists; collect it, never rerun')
    result = dict(status='FAIL', gate_level='single-layer', build_id='0x4D395832',
                  errors=[], performance_pass=False, formal_promotion_allowed=False,
                  model_math_changed=False, overlay_loaded=False, passes=[], active_transaction=None)
    runtime = session = base = lock = None
    allocated = []
    initialized = any_launch = unsafe = False
    stop = threading.Event()
    phase = ['package']
    def heartbeat():
        while not stop.wait(30):
            print('M343_HEARTBEAT phase=' + phase[0], flush=True)
    beat = threading.Thread(target=heartbeat, daemon=True)
    beat.start()
    started = time.monotonic()
    try:
        verify_self(HERE, a.manifest_sha)
        result['manifest_sha256'] = a.manifest_sha
        prior_path = HERE / 'SINGLE_CHAIN_PREREQUISITE.json'
        prior = json.loads(prior_path.read_text())
        if sha256(prior_path) != PRIOR_SHA or prior['status'] != 'PASS' or prior['unsafe_buffers_retained']:
            raise RuntimeError('Exact safely completed chain prerequisite required')
        result['single_chain_prerequisite_sha256'] = PRIOR_SHA
        if os.geteuid() != 0:
            raise RuntimeError('Root required')
        closure = json.loads((HERE / 'HARDWARE_CLOSURE.json').read_text())
        if closure['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED':
            raise RuntimeError('Unchanged stable hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        boot = Path('/boot/firmware/boot.scr.uimg')
        before_boot, before_cmd = sha256(boot), Path('/proc/cmdline').read_text()
        phase[0] = 'frozen-imports-and-input'
        modules, norms, hidden, source_closure = load_frozen()
        base = modules['board_runtime']
        m241 = modules['m241_video_language_runtime']
        run_layer = bind(m241, (HERE / 'frozen_one_layer.py').read_text())
        result['input_contract'] = json.loads((HERE / 'INPUT_CONTRACT.json').read_text())
        result['source_closure_sha256'] = sha256(HERE / 'SOURCE_CLOSURE.json')
        phase[0] = 'fixed-environment-preflight'
        envpath = EVIDENCE / 'environment.json'
        env = subprocess.run([sys.executable, '-B', str(HERE / 'm120_board_env_preflight.py'),
            '--candidate', str(STABLE), '--expected-package-manifest-sha256', STABLE_SHA,
            '--result', str(envpath)], timeout=90)
        if env.returncode:
            raise RuntimeError('Fixed environment preflight rejected')
        result['environment_sha256'] = sha256(envpath)
        # Retain the object and every allocation even if original init raises.
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*args, **kwargs):
            buffer = original_allocate(*args, **kwargs)
            allocated.append(buffer)
            return buffer
        pynq.allocate = tracked_allocate
        cls = modules['m238_prefill_runtime'].M238PrefillRuntime
        runtime = cls.__new__(cls)
        phase[0] = 'original-runtime-weight-verification-and-allocation'
        weights = RELEASE / 'external_assets/weights'
        try:
            cls.__init__(runtime, STABLE / 'overlay/m120_m89x2_t32.bit',
                weights / 'language_fourport', weights / 'lmhead_fourport',
                STABLE / 'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json',
                STABLE / 'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json')
            initialized = True
        finally:
            pynq.allocate = original_allocate
        result['overlay_loaded'] = True
        result['cma_after_actual_runtime_allocations'] = cma_free()
        if runtime.maximum_weight_window_bytes != 6963200:
            raise RuntimeError('Maximum frozen weight-window geometry drift')
        plan = [(runtime.language_layout, runtime._language_chain(0, family)) for family in FAMILIES]
        result['chain_plan'] = [dict(family=f, identity=chain_identity(c),
            input_bytes=int(c['input_bytes']), output_bytes=int(c['output_bytes']),
            window=list(base.chain_window(layout, c))) for f, (layout, c) in zip(FAMILIES, plan)]
        # Observers wrap the accepted launch functions, including adaptive retries.
        for name in ('_launch_prepacked', '_launch_once'):
            original = getattr(runtime, name)
            def observe(chain, *args, _name=name, _original=original, **kwargs):
                nonlocal any_launch
                any_launch = True
                result['active_transaction'] = dict(launch=_name, chain_index=chain['chain_index'],
                    chain_identity=chain_identity(chain), layer=chain.get('layer'), family=chain.get('family'),
                    input_bytes=int(chain['input_bytes']), output_bytes=int(chain['output_bytes']))
                return _original(chain, *args, **kwargs)
            setattr(runtime, name, observe)
        def run(label):
            phase[0] = label
            model = m241.M241VideoLanguageModel.__new__(m241.M241VideoLanguageModel)
            model.runtime, model.norms = runtime, norms
            model.grouped_attention_calls = 0
            model.grouped_attention_wall_ms = 0.0
            model.rope_cache_used = False
            families = []
            original_family = model._family
            def family(layer, name, values):
                print('M343_FAMILY ' + label + ' ' + name, flush=True)
                phase[0] = label + ':' + name
                output = original_family(layer, name, values)
                families.append(dict(family=name, input=tensor(values),
                                     output={n: tensor(v) for n, v in sorted(output.items())}))
                return output
            model._family = family
            old = json.loads(json.dumps(runtime.evidence()))
            output, kv = run_layer(model, hidden.copy())
            new = runtime.evidence()
            row = dict(label=label, families=families, hidden=tensor(output),
                       keys=[tensor(v) for v in kv.keys], values=[tensor(v) for v in kv.values],
                       grouped_attention_calls=model.grouped_attention_calls,
                       logical_calls=new['logical_calls'] - old['logical_calls'],
                       host_calls=new['host_calls'] - old['host_calls'],
                       retry_count=new['scale_retry_count'] - old['scale_retry_count'],
                       retry_launches=new['pipeline_retry_launches'] - old['pipeline_retry_launches'],
                       nonfinite_detections=new['fused_nonfinite_detections'] - old['fused_nonfinite_detections'],
                       scale_attempts=new['scale_attempts'][len(old['scale_attempts']):],
                       stage_bytes=new['stage_bytes'] - old['stage_bytes'],
                       snapshot=base.transaction_snapshot(runtime.kernel, runtime.dma))
            result['passes'].append(row)
            if [f['family'] for f in families] != list(FAMILIES) or row['logical_calls'] != 25 or row['grouped_attention_calls'] != 1:
                raise RuntimeError('Single layer/five T32 batches call contract differs')
            if row['host_calls'] != 25 + row['retry_count'] or not row['retry_count'] == row['retry_launches'] == row['nonfinite_detections']:
                raise RuntimeError('Accepted adaptive retry accounting differs')
            if not safe_to_release(row['snapshot']):
                raise RetainedBuffersError('Unsafe completed layer state')
            return row
        # This baseline is the legal same-overlay transaction proof required
        # before a WeightPrefetchSession; fresh DMASR=0 is never considered idle.
        baseline = run('baseline')
        free = cma_free()
        result['cma_before_extra_bank_after_baseline'] = free
        session = WeightPrefetchSession(runtime, base, plan, cma_free_bytes=free)
        with session:
            result['cma_with_extra_bank'] = cma_free()
            stage = runtime._stage
            bank_records = []
            def observed_stage(layout, chain):
                buffers, words = stage(layout, chain)
                _, size = base.chain_window(layout, chain)
                bank_records.append(dict(family=chain['family'], words=words, bytes_per_shard=size,
                    addresses=[base.physical_address(b) for b in buffers],
                    weight_sha256=[hashlib.sha256(memoryview(b)[:size]).hexdigest() for b in buffers]))
                return buffers, words
            runtime._stage = observed_stage
            candidate = run('candidate')
            result['bank_records'] = bank_records
        result['prefetch'] = session.record
        compared = ('families', 'hidden', 'keys', 'values', 'logical_calls', 'host_calls',
                    'retry_count', 'retry_launches', 'nonfinite_detections', 'scale_attempts', 'stage_bytes')
        result['exact_comparison'] = {key: baseline[key] == candidate[key] for key in compared}
        if not all(result['exact_comparison'].values()):
            raise RuntimeError('Stable/candidate full single-layer bitwise or retry difference')
        if session.record['stages'] != 5 or session.record['total_weight_bytes'] != candidate['stage_bytes']:
            raise RuntimeError('Incomplete five-family prefetch plan')
        addresses = [r['addresses'] for r in bank_records]
        if addresses[0] != addresses[2] or addresses[0] != addresses[4] or addresses[1] != addresses[3] or set(addresses[0]) & set(addresses[1]):
            raise RuntimeError('Bank alternation differs from A-B-A-B-A')
        # Independently read the five original windows and compare staging hashes.
        for (layout, chain), row in zip(plan, bank_records):
            offset = row['words'] * 16
            expected = []
            for item in layout.manifest['files']:
                with (layout.root / item['path']).open('rb') as stream:
                    stream.seek(offset)
                    raw = stream.read(row['bytes_per_shard'])
                if len(raw) != row['bytes_per_shard']:
                    raise RuntimeError('Independent source window short read')
                expected.append(hashlib.sha256(raw).hexdigest())
            if row['weight_sha256'] != expected:
                raise RuntimeError('Staged weight differs from original file window')
        result['boot_unchanged'] = sha256(boot) == before_boot
        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text() == before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:
            raise RuntimeError('Protected boot identities changed')
        result['runtime_evidence'] = runtime.evidence()
        result['status'] = 'PASS'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__ + ': ' + str(exc))
        result['traceback'] = traceback.format_exc()
    finally:
        if session is not None and not session.closed:
            try:
                session.close()
            except BaseException as exc:
                unsafe = True
                result['errors'].append('Retained session: ' + str(exc))
            result['prefetch'] = session.record
        if runtime is not None and base is not None and hasattr(runtime, 'dma'):
            result['final_snapshot'] = base.transaction_snapshot(runtime.kernel, runtime.dma)
            unsafe = unsafe or (any_launch and not safe_to_release(result['final_snapshot']))
        result['unsafe_buffers_retained'] = unsafe
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic() - started
        result['next_step'] = 'fixed-text E2E; no full video/speed promotion' if result['status'] == 'PASS' else 'debug single-layer only; never advance'
        if not unsafe:
            if initialized:
                runtime.close()
            else:
                for buffer in reversed(allocated):
                    buffer.freebuffer()
            result['safe_buffers_released'] = True
        write_json(result_path, result)
        raw = result_path.read_bytes()
        print('M343_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
        print('M343_RESULT_BASE64=' + base64.b64encode(raw).decode(), flush=True)
        print('M343_SUMMARY=' + json.dumps(dict(status=result['status'], errors=result['errors'], unsafe=unsafe)), flush=True)
        stop.set()
        if unsafe:
            print('M343_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT', flush=True)
            while True:
                time.sleep(30)
        if lock is not None:
            os.close(lock)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
