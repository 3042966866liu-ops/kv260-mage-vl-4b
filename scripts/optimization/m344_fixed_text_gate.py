"""Original M238/M241 fixed 30-token E2E; exact full logits and all K/V."""
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
HERE = Path(__file__).resolve().parent
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
EVIDENCE = Path('/home/ubuntu/m344_fixed_text_evidence_01')
PRIOR_SHA = 'a7fadf42f0afb65dddbffb862163a1c99684a04664318463894e598f314cf67e'


def cma_free():
    for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
        if line.startswith('CmaFree:'): return int(line.split()[1]) * 1024
    raise RuntimeError('CmaFree unavailable')


def tensor(value):
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all(): raise FloatingPointError('Nonfinite model output')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())


def exact_array(a, b):
    # Includes signed zeros and all FP32 bits, without an arithmetic tolerance.
    return a.dtype == b.dtype and a.shape == b.shape and np.ascontiguousarray(a).tobytes() == np.ascontiguousarray(b).tobytes()


def check_call_contract(row, expected_macros):
    attempts = row['scale_attempts']
    if len(attempts) != 162: raise RuntimeError('Missing accepted per-chain scale records')
    if any(not a['attempted_shifts'] or a['selected_shift'] != a['attempted_shifts'][-1] for a in attempts):
        raise RuntimeError('Unconverged or inconsistent adaptive retry')
    language_retries = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is not None)
    head_retries = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is None)
    total = language_retries + head_retries
    if row['logical_calls'] != 162 or row['host_calls'] != 162 + total or row['retry_count'] != total:
        raise RuntimeError('Fixed-text logical/physical/total retry contract differs')
    if not row['retry_launches'] == row['nonfinite_detections'] == language_retries:
        raise RuntimeError('Language pipeline retry accounting differs')
    if row['logical_expected_macros'] != expected_macros:
        raise RuntimeError('Logical hardware macro count differs')
    row['language_retries'], row['head_retries'] = language_retries, head_retries


def main():
    p = argparse.ArgumentParser(); p.add_argument('manifest_sha'); a = p.parse_args()
    path = EVIDENCE / 'fixed-text.json'
    if path.exists(): raise RuntimeError('Immutable fixed-text evidence exists; only collect')
    result = dict(status='FAIL', gate_level='fixed-text-E2E', build_id='0x4D395832', errors=[], passes=[],
                  performance_pass=False, formal_promotion_allowed=False, model_math_changed=False,
                  overlay_loaded=False, active_transaction=None)
    runtime = session = base = lock = None
    initialized = any_launch = unsafe = False
    allocated = []
    phase, stop = ['package'], threading.Event()
    def heartbeat():
        while not stop.wait(30): print('M344_HEARTBEAT phase=' + phase[0], flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    started = time.monotonic()
    try:
        verify_self(HERE, a.manifest_sha)
        result['manifest_sha256'] = a.manifest_sha
        prior_path = HERE / 'SINGLE_LAYER_PREREQUISITE.json'
        prior = json.loads(prior_path.read_text(encoding='utf-8'))
        if sha256(prior_path) != PRIOR_SHA or prior['status'] != 'PASS' or prior['unsafe_buffers_retained']:
            raise RuntimeError('Exact safely completed layer prerequisite required')
        result['single_layer_prerequisite_sha256'] = PRIOR_SHA
        if os.geteuid() != 0: raise RuntimeError('Root required')
        hardware = json.loads((HERE / 'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if hardware['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED':
            raise RuntimeError('Stable hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        boot = Path('/boot/firmware/boot.scr.uimg')
        before_boot, before_cmd = sha256(boot), Path('/proc/cmdline').read_text(encoding='utf-8')
        phase[0] = 'source-closure-and-original-fixed-input'
        closure = json.loads((HERE / 'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        for item in closure['files']:
            file = RELEASE / item['path']
            if file.stat().st_size != item['bytes'] or sha256(file) != item['sha256']:
                raise RuntimeError('Installed identity mismatch: ' + item['path'])
        sys.path[:0] = [str(RELEASE / directory) for directory in closure['module_dirs']]
        modules = {}
        for name, relative in closure['modules'].items():
            module = importlib.import_module(name)
            if Path(module.__file__).resolve() != (RELEASE / relative).resolve():
                raise RuntimeError('Unexpected import: ' + name)
            modules[name] = module
        base = modules['board_runtime']; m241 = modules['m241_video_language_runtime']
        contract = json.loads((HERE / 'INPUT_CONTRACT.json').read_text(encoding='utf-8'))
        reference = json.loads((STABLE / 'auxiliary/official_cpu_text_1token.json').read_text(encoding='utf-8'))
        if reference['prompt_token_ids'] != contract['prompt_token_ids'] or reference['generated_token_ids'] != [17]:
            raise RuntimeError('Original fixed CPU token reference mismatch')
        with np.load(STABLE / 'auxiliary/m77_text_aux_fp16.npz', allow_pickle=False) as archive:
            norms = {name: archive[name] for name in archive.files}
        rows = np.asarray(norms['model.language_model.embed_tokens.weight'], np.float32)
        hidden = np.stack([rows[contract['selected_embedding_ids'].index(token)] for token in contract['prompt_token_ids']])
        if tensor(hidden) != contract['input_tensor']: raise RuntimeError('Original 30-token W3 embedding differs')
        result['input_contract'] = contract
        phase[0] = 'fixed-environment-preflight'
        envpath = EVIDENCE / 'environment.json'
        env = subprocess.run([sys.executable, '-B', str(HERE / 'm120_board_env_preflight.py'), '--candidate', str(STABLE),
            '--expected-package-manifest-sha256', STABLE_SHA, '--result', str(envpath)], timeout=90)
        if env.returncode: raise RuntimeError('Fixed environment preflight rejected')
        result['environment_sha256'] = sha256(envpath)
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*args, **kwargs):
            buffer = original_allocate(*args, **kwargs); allocated.append(buffer); return buffer
        pynq.allocate = tracked_allocate
        cls = modules['m238_prefill_runtime'].M238PrefillRuntime
        runtime = cls.__new__(cls)
        phase[0] = 'original-runtime-weight-verification-and-allocation'
        weights = RELEASE / 'external_assets/weights'
        try:
            cls.__init__(runtime, STABLE / 'overlay/m120_m89x2_t32.bit', weights / 'language_fourport', weights / 'lmhead_fourport',
                STABLE / 'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json', STABLE / 'contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json')
            initialized = True
        finally: pynq.allocate = original_allocate
        result['overlay_loaded'] = True
        result['cma_after_actual_runtime_allocations'] = cma_free()
        if runtime.maximum_weight_window_bytes != 6963200: raise RuntimeError('Frozen buffer geometry differs')
        family_plan = [(layer, family) for layer in range(36) for family in
                       (('q', 'kv', 'attention_out', 'gate_up', 'mlp_down') if layer < 10 else ('qkv', 'attention_out', 'gate_up', 'mlp_down'))]
        plan = [(runtime.language_layout, runtime._language_chain(layer, family)) for layer, family in family_plan]
        plan.extend((runtime.head_layout, chain) for chain in runtime.head_contract.chains)
        if len(plan) != 162 or len(runtime.head_contract.chains) != 8: raise RuntimeError('Frozen complete prefetch plan differs')
        expected_macros = sum(c['expected_macros'] for _, c in plan)
        expected_stage_bytes = sum(4 * base.chain_window(layout, chain)[1] for layout, chain in plan)
        result['plan_identity_sha256'] = hashlib.sha256(''.join(chain_identity(c) for _, c in plan).encode()).hexdigest()
        # Both scheduler launches and ordinary LM-head _execute are observed;
        # no observer changes packets, arithmetic, timing policy or retry shifts.
        for name in ('_launch_prepacked', '_launch_once', '_execute'):
            original = getattr(runtime, name)
            def observe(chain, *args, _name=name, _original=original, **kwargs):
                nonlocal any_launch
                any_launch = True
                result['active_transaction'] = dict(launch=_name, chain_identity=chain_identity(chain),
                    chain_index=chain['chain_index'], layer=chain.get('layer'), family=chain.get('family', 'lm_head'),
                    input_bytes=int(chain['input_bytes']), output_bytes=int(chain['output_bytes']))
                return _original(chain, *args, **kwargs)
            setattr(runtime, name, observe)
        def run(label):
            model = m241.M241VideoLanguageModel.__new__(m241.M241VideoLanguageModel)
            model.runtime, model.norms = runtime, norms
            model.grouped_attention_calls = 0; model.grouped_attention_wall_ms = 0.0; model.rope_cache_used = False
            observations = []
            original_family = model._family
            def family(layer, name, values):
                phase[0] = label + ':layer' + str(layer) + ':' + name
                if name in ('q', 'qkv'): print('M344_LAYER ' + label + ' layer=' + str(layer), flush=True)
                outputs = original_family(layer, name, values)
                observations.append(dict(layer=layer, family=name, input=tensor(values),
                                         output={n: tensor(v) for n, v in sorted(outputs.items())}))
                return outputs
            model._family = family
            old = json.loads(json.dumps(runtime.evidence()))
            token, logits, kv = model.prefill(hidden.copy())
            new = runtime.evidence()
            row = dict(label=label, token=token, logits=tensor(logits),
                       keys=[tensor(v) for v in kv.keys], values=[tensor(v) for v in kv.values],
                       families=observations, grouped_attention_calls=model.grouped_attention_calls,
                       scale_attempts=new['scale_attempts'][len(old['scale_attempts']):],
                       snapshot=base.transaction_snapshot(runtime.kernel, runtime.dma))
            for key in ('logical_calls', 'host_calls', 'scale_retry_count', 'pipeline_retry_launches', 'fused_nonfinite_detections',
                        'stage_bytes', 'logical_expected_macros', 'expected_macros'):
                row[{'scale_retry_count': 'retry_count', 'pipeline_retry_launches': 'retry_launches',
                     'fused_nonfinite_detections': 'nonfinite_detections'}.get(key, key)] = new[key] - old[key]
            result['passes'].append(row)
            check_call_contract(row, expected_macros)
            if [(o['layer'], o['family']) for o in observations] != family_plan or model.grouped_attention_calls != 36:
                raise RuntimeError('Complete original model family/attention sequence differs')
            if logits.shape != (151936,) or len(kv.keys) != 36 or len(kv.values) != 36 or token != 17:
                raise RuntimeError('Full fixed-text logits/KV/reference token gate failed')
            if row['stage_bytes'] != expected_stage_bytes: raise RuntimeError('Whole-model staged weight byte count differs')
            if not safe_to_release(row['snapshot']): raise RetainedBuffersError('Unsafe complete E2E state')
            return row, logits, kv
        baseline, baseline_logits, baseline_kv = run('baseline')
        result['cma_before_extra_bank_after_baseline'] = free = cma_free()
        session = WeightPrefetchSession(runtime, base, plan, cma_free_bytes=free)
        with session:
            result['cma_with_extra_bank'] = cma_free()
            staged = runtime._stage; bank_records = []
            def observed_stage(layout, chain):
                buffers, words = staged(layout, chain)
                _, size = base.chain_window(layout, chain)
                bank_records.append(dict(chain_identity=chain_identity(chain), words=words, bytes_per_shard=size,
                    addresses=[base.physical_address(b) for b in buffers],
                    weight_sha256=[hashlib.sha256(memoryview(b)[:size]).hexdigest() for b in buffers]))
                return buffers, words
            runtime._stage = observed_stage
            candidate, candidate_logits, candidate_kv = run('candidate')
        result['prefetch'] = session.record
        compared = ('families', 'token', 'logits', 'keys', 'values', 'logical_calls', 'host_calls', 'retry_count',
                    'retry_launches', 'nonfinite_detections', 'scale_attempts', 'stage_bytes', 'logical_expected_macros', 'expected_macros')
        result['exact_comparison'] = {key: baseline[key] == candidate[key] for key in compared}
        result['direct_bitwise_logits_equal'] = exact_array(baseline_logits, candidate_logits)
        result['direct_bitwise_72_kv_equal'] = all(exact_array(x, y) for x, y in
            zip(baseline_kv.keys + baseline_kv.values, candidate_kv.keys + candidate_kv.values))
        if not all(result['exact_comparison'].values()) or not result['direct_bitwise_logits_equal'] or not result['direct_bitwise_72_kv_equal']:
            raise RuntimeError('Original/candidate full logits/KV or family bytes differ')
        if session.record['stages'] != 162 or session.record['total_weight_bytes'] != expected_stage_bytes:
            raise RuntimeError('Incomplete model prefetch plan')
        addresses = [r['addresses'] for r in bank_records]
        if any(addresses[i] != addresses[i % 2] for i in range(162)) or set(addresses[0]) & set(addresses[1]):
            raise RuntimeError('Whole-model bank alternation differs')
        phase[0] = 'independent-original-file-window-hashes'
        for (layout, chain), row in zip(plan, bank_records):
            expected = []
            for item in layout.manifest['files']:
                with (layout.root / item['path']).open('rb') as stream:
                    stream.seek(row['words'] * 16); raw = stream.read(row['bytes_per_shard'])
                if len(raw) != row['bytes_per_shard']: raise RuntimeError('Original source window short read')
                expected.append(hashlib.sha256(raw).hexdigest())
            if row['weight_sha256'] != expected: raise RuntimeError('Staged weight differs from independent original window')
        result['bank_records'] = bank_records
        result['boot_unchanged'] = sha256(boot) == before_boot
        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text(encoding='utf-8') == before_cmd
        if not result['boot_unchanged'] or not result['cmdline_unchanged']: raise RuntimeError('Protected identities changed')
        result['status'] = 'PASS'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__ + ': ' + str(exc)); result['traceback'] = traceback.format_exc()
    finally:
        if session is not None and not session.closed:
            try: session.close()
            except BaseException as exc:
                unsafe = True; result['errors'].append('Retained session: ' + str(exc))
            result['prefetch'] = session.record
        if runtime is not None and base is not None and hasattr(runtime, 'dma'):
            result['overlay_loaded'] = hasattr(runtime, 'overlay')
            result['final_snapshot'] = base.transaction_snapshot(runtime.kernel, runtime.dma)
            unsafe = unsafe or (any_launch and not safe_to_release(result['final_snapshot']))
        if not unsafe:
            try:
                if initialized: runtime.close()
                else:
                    for buffer in reversed(allocated): buffer.freebuffer()
                result['safe_buffers_released'] = True
            except BaseException as exc:
                result['status'] = 'FAIL'; unsafe = True
                result['errors'].append('Release failed; retained process: ' + str(exc))
        result['unsafe_buffers_retained'] = unsafe
        if unsafe: result['status'] = 'FAIL'
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic() - started
        result['next_step'] = 'fixed159 video full logits/KV numerical gate, then balanced A/B' if result['status'] == 'PASS' else 'debug fixed-text level only; never advance'
        write_json(path, result); raw = path.read_bytes()
        print('M344_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
        # Fixed small blocks preserve bounded serial result recovery and avoid
        # sending or relying on a very long single encoded line.
        chunks = [raw[i:i+1800] for i in range(0, len(raw), 1800)]
        for index, chunk in enumerate(chunks):
            print('M344_RESULT_CHUNK=' + str(index) + '/' + str(len(chunks)) + ':' + base64.b64encode(chunk).decode(), flush=True)
        print('M344_SUMMARY=' + json.dumps(dict(status=result['status'], errors=result['errors'], unsafe=unsafe)), flush=True)
        stop.set()
        if unsafe:
            print('M344_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT', flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
