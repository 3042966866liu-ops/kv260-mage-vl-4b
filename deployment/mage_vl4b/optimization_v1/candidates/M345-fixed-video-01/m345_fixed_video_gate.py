"""Unchanged M276 real-video stream, exact baseline/candidate M241 outputs."""
import argparse
import base64
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
from types import SimpleNamespace
sys.dont_write_bytecode = True
import numpy as np
from board_safety import safe_to_release
from measurement import sha256, write_json
from m341_build_id_gate import verify_self, service_stopped, STABLE, STABLE_SHA
from weight_prefetch import WeightPrefetchSession, RetainedBuffersError, chain_identity
from frozen_video_identity import module_paths, verify_m277_release_subset, FRAMES, STACK_SHA, ADDON, RELEASE
HERE = Path(__file__).resolve().parent
EVIDENCE = Path('/home/ubuntu/m345_fixed_video_evidence_01')
PRIOR_SHA = '897bb817d6bd2a12f5de5437bb015541210f86c297c85456bc570586d479673a'


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
    return a.dtype == b.dtype and a.shape == b.shape and np.ascontiguousarray(a).tobytes() == np.ascontiguousarray(b).tobytes()


def check_call_contract(row, expected_macros):
    attempts = row['scale_attempts']
    if len(attempts) != 778: raise RuntimeError('Missing accepted per-T32/head scale records')
    if any(not a['attempted_shifts'] or a['selected_shift'] != a['attempted_shifts'][-1] for a in attempts):
        raise RuntimeError('Unconverged or inconsistent adaptive retry')
    language = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is not None)
    head = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is None)
    if row['logical_calls'] != 778 or row['host_calls'] != 778 + language + head or row['retry_count'] != language + head:
        raise RuntimeError('Video logical/physical/total retry contract differs')
    if not row['retry_launches'] == row['nonfinite_detections'] == language:
        raise RuntimeError('Language pipeline retry accounting differs')
    if row['logical_expected_macros'] != expected_macros: raise RuntimeError('Logical hardware macro count differs')
    row['language_retries'], row['head_retries'] = language, head


def validate_stream(events, decoder):
    stages = [p['name'] for n,p in events if n == 'stage']
    groups = {n:[p for k,p in events if k == n] for n in ('complete','token','knife_observation')}
    if stages != ['preprocess','vision','prefill'] or any(len(v) != 1 for v in groups.values()):
        raise RuntimeError('Original stream stages/events incomplete')
    final, token, observation = (groups[n][0] for n in ('complete','token','knife_observation'))
    proof = final.get('proof', {})
    if not (final.get('status') == 'PASS' and final.get('prompt_tokens') == 159 and final.get('generated_tokens') == 1
            and final.get('decode_calls') == 0 and final.get('selected_frame_indices') == [3]
            and token.get('token_id') == 15 and token.get('text') == '0' and token.get('knife_verdict') == 'ABSENT'
            and observation.get('verdict') == 'ABSENT' and observation.get('selected_frame_indices') == [3]
            and str(proof.get('build_id','')).lower() == '0x4d395832'
            and proof.get('pl_logical_chain_calls') == proof.get('expected_pl_logical_chain_calls') == 778
            and proof.get('language_cpu_linear_fallback') is False and proof.get('decode_calls') == 0
            and proof.get('pl_expected_macros', 0) > 0):
        raise RuntimeError('Frozen M277 functional contract failed')
    if not (decoder.get('cache_entries') == 26 and decoder.get('cache_bytes') == 66699264
            and decoder.get('cache_misses') == 26 and decoder.get('cache_within_budget') is True):
        raise RuntimeError('Original bounded vision cache contract differs')
    # Timing is diagnostic only. Original constrained decision fields are exact.
    semantic = dict(token=token, observation=observation, proof=proof, prompt_tokens=159,
                    selected_frame_indices=[3], generated_tokens=1, decode_calls=0)
    if not token['knife_score'] == observation['knife_score'] == final['knife_score']:
        raise RuntimeError('Inconsistent constrained decision score')
    return semantic


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); args = parser.parse_args()
    path = EVIDENCE / 'fixed-video.json'
    if path.exists(): raise RuntimeError('Immutable fixed-video evidence exists; only collect')
    result = dict(status='FAIL', gate_level='fixed159-video-E2E', build_id='0x4D395832', errors=[], passes=[],
                  performance_pass=False, formal_promotion_allowed=False, model_math_changed=False,
                  overlay_loaded=False, active_transaction=None, scope='Frozen four-frame source window; original latest-frame two-view M276')
    engine = runtime = base = session = lock = None
    unsafe = any_launch = initialized = False
    allocated, bank_records = [], []
    phase, stop = ['package'], threading.Event()
    def heartbeat():
        while not stop.wait(30): print('M345_HEARTBEAT phase=' + phase[0], flush=True)
    threading.Thread(target=heartbeat, daemon=True).start()
    started = time.monotonic()
    try:
        verify_self(HERE, args.manifest_sha); result['manifest_sha256'] = args.manifest_sha
        prior = json.loads((HERE / 'FIXED_TEXT_PREREQUISITE.json').read_text(encoding='utf-8'))
        if prior['status'] != 'PASS' or prior['sha256'] != PRIOR_SHA or prior['errors'] or not all(prior['exact'].values()):
            raise RuntimeError('Synchronized exact M344 fixed-text prerequisite required')
        result['fixed_text_prerequisite_sha256'] = PRIOR_SHA
        if os.geteuid() != 0: raise RuntimeError('Root required')
        hardware = json.loads((HERE / 'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
        if hardware['status'] != 'PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED': raise RuntimeError('Stable hardware evidence required')
        lock = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        boot = Path('/boot/firmware/boot.scr.uimg'); before_boot = sha256(boot)
        before_cmd = Path('/proc/cmdline').read_text(encoding='utf-8')
        phase[0] = 'release-source-and-asset-preflight'
        closure = json.loads((HERE / 'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
        for row in closure['files']:
            file = RELEASE / row['path']
            if file.stat().st_size != row['bytes'] or sha256(file) != row['sha256']:
                raise RuntimeError('Installed source identity mismatch: ' + row['path'])
        if sha256(RELEASE / 'INSTALL_PACKAGE_MANIFEST.json') != 'fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e':
            raise RuntimeError('Frozen installed manifest identity differs')
        if sha256(ADDON / 'PACKAGE_MANIFEST.json') != '4eb8c6c95752208b5848e0e52efb2a713f98487f5b88518dbd5b58801d236568':
            raise RuntimeError('Frozen video companion identity differs')
        result['m277_release_subset'] = verify_m277_release_subset(RELEASE / 'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0] = [str(p) for p in module_paths()]
        import m276_m254_video_server
        import m276_video_runtime
        import m222_video_server
        import m243_video_server
        import video_server
        import m241_video_language_runtime
        import m238_prefill_runtime
        import board_runtime as base
        import reserved_ddr_pool
        for name, relative in closure['modules'].items():
            if name in sys.modules:
                module = sys.modules[name]
                if Path(module.__file__).resolve() != (RELEASE / relative).resolve(): raise RuntimeError('Unexpected import path: ' + name)
        if not (m222_video_server.M222PSVisionRuntime.__name__ == 'M273LatestPSVisionRuntime'
                and video_server.M120VideoRuntime.__name__ == 'M276ShortPromptBinaryRuntime'):
            raise RuntimeError('Original M276/M273 class identity differs')
        result['exact_imports_before_overlay'] = {name: str(sys.modules[name].__file__) for name in
            ('m276_video_runtime','m273_latest_vision_runtime','m238_prefill_runtime','m241_video_language_runtime','board_runtime','reserved_ddr_pool')}
        spec = importlib.util.spec_from_file_location('release_preflight', RELEASE / 'scripts/preflight.py')
        preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
        inspected = preflight.inspect(json.loads((RELEASE / 'configs/deployment.example.json').read_text(encoding='utf-8')), port_check=True)
        result['release_preflight'] = {k:inspected[k] for k in ('status','build_id','missing','hash_or_identity_mismatch','port_free')}
        if inspected['status'] != 'READY_FOR_BOARD_PREFLIGHT': raise RuntimeError('Release assets rejected before overlay')
        frames = []
        for name, digest in FRAMES.items():
            file = ADDON / 'fixtures' / name
            if sha256(file) != digest: raise RuntimeError('Frozen frame file identity differs')
            frames.append(np.load(file, allow_pickle=False))
        frames = np.ascontiguousarray(np.stack(frames))
        if frames.shape != (4,448,448,3) or frames.dtype != np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest() != STACK_SHA:
            raise RuntimeError('Frozen ordered source frame tensor differs')
        result['frames_sha256'] = STACK_SHA
        d = RELEASE / 'deployment/mage_vl4b'
        config = video_server.make_config(d / 'm181_m120_video_board_candidate', STABLE, RELEASE / 'external_assets/weights',
            RELEASE / 'tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json')
        from tokenizers import Tokenizer
        Tokenizer.from_file(str(config['tokenizer']))  # Actual asset construction before overlay, no fake import.
        envpath = EVIDENCE / 'environment.json'; phase[0] = 'fixed-environment-preflight'
        env = subprocess.run([sys.executable, '-B', str(HERE / 'm120_board_env_preflight.py'), '--candidate', str(STABLE),
            '--expected-package-manifest-sha256', STABLE_SHA, '--result', str(envpath)], timeout=90)
        if env.returncode: raise RuntimeError('Fixed same-terminal environment preflight rejected')
        result['environment_sha256'] = sha256(envpath)
        import pynq
        original_allocate = pynq.allocate
        def tracked_allocate(*a, **kw):
            buffer = original_allocate(*a, **kw); allocated.append(buffer); return buffer
        original_cls = m243_video_server.M238PrefillRuntime
        class OwnedRuntime(original_cls):
            def __init__(self, *a, **kw):
                nonlocal runtime, initialized
                runtime = self; self._m345_closed = False
                super().__init__(*a, **kw); initialized = True
            def close(self):
                super().close(); self._m345_closed = True
        engine = m276_video_runtime.M276ShortPromptBinaryRuntime(config)
        pynq.allocate = tracked_allocate; m243_video_server.M238PrefillRuntime = OwnedRuntime
        phase[0] = 'original-video-runtime-load'
        try: engine.load()
        finally:
            pynq.allocate = original_allocate; m243_video_server.M238PrefillRuntime = original_cls
        if not isinstance(engine.language, m241_video_language_runtime.M241VideoLanguageModel) or engine.board is not runtime:
            raise RuntimeError('Original real M238/M241 object closure differs')
        result['overlay_loaded'] = True; result['cma_after_actual_runtime_allocations'] = cma_free()
        if runtime.maximum_weight_window_bytes != 6963200: raise RuntimeError('Frozen weight buffer geometry differs')
        family_plan = [(layer, family) for layer in range(36) for family in
                       (('q','kv','attention_out','gate_up','mlp_down') if layer < 10 else ('qkv','attention_out','gate_up','mlp_down'))]
        plan = [(runtime.language_layout, runtime._language_chain(layer, family)) for layer,family in family_plan]
        plan.extend((runtime.head_layout, chain) for chain in runtime.head_contract.chains)
        if len(plan) != 162 or len(runtime.head_contract.chains) != 8: raise RuntimeError('Complete frozen prefetch plan differs')
        expected_macros = sum(c['expected_macros'] * (5 if i < 154 else 1) for i,(_,c) in enumerate(plan))
        stage_bytes = sum(4 * base.chain_window(layout,c)[1] for layout,c in plan)
        result['plan_identity_sha256'] = hashlib.sha256(''.join(chain_identity(c) for _,c in plan).encode()).hexdigest()
        for name in ('_launch_prepacked','_launch_once','_execute'):
            original = getattr(runtime,name)
            def observe(chain,*a,_name=name,_original=original,**kw):
                nonlocal any_launch
                any_launch = True
                result['active_transaction'] = dict(launch=_name, chain_identity=chain_identity(chain), chain_index=chain['chain_index'],
                    layer=chain.get('layer'), family=chain.get('family','lm_head'), input_bytes=int(chain['input_bytes']), output_bytes=int(chain['output_bytes']))
                return _original(chain,*a,**kw)
            setattr(runtime,name,observe)
        model = engine.language
        original_prefill, original_family = model.prefill, model._family
        label, observations, captured = ['baseline'], [], {}
        def family(layer,name,values):
            phase[0] = label[0] + ':layer' + str(layer) + ':' + name
            if name in ('q','qkv'): print('M345_LAYER ' + label[0] + ' layer=' + str(layer), flush=True)
            outputs = original_family(layer,name,values)
            observations.append(dict(layer=layer,family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(outputs.items())}))
            return outputs
        def capture_prefill(hidden):
            nonlocal session
            if 'input' in captured: raise RuntimeError('Unexpected second prefill in one stream')
            captured['input'] = tensor(hidden); captured['input_array'] = hidden.copy()
            if hidden.shape != (159,2560): raise RuntimeError('Actual original video hidden geometry differs')
            if label[0] == 'candidate':
                free = cma_free(); result['cma_before_extra_bank_after_baseline_and_candidate_vision'] = free
                session = WeightPrefetchSession(runtime,base,plan,cma_free_bytes=free)
                with session:
                    result['cma_with_extra_bank'] = cma_free()
                    staged = runtime._stage
                    def observed_stage(layout,chain):
                        buffers,words = staged(layout,chain); _,size = base.chain_window(layout,chain)
                        bank_records.append(dict(chain_identity=chain_identity(chain),words=words,bytes_per_shard=size,
                            addresses=[base.physical_address(b) for b in buffers],weight_sha256=[hashlib.sha256(memoryview(b)[:size]).hexdigest() for b in buffers]))
                        return buffers,words
                    runtime._stage = observed_stage
                    output = original_prefill(hidden)
                result['prefetch'] = session.record
            else: output = original_prefill(hidden)
            captured['output'] = output
            return output
        model._family, model.prefill = family, capture_prefill
        request = SimpleNamespace(prompt=m276_video_runtime.M276_KNIFE_PROMPT,max_new_tokens=1,frames_rgb_u8=frames)
        def run(name):
            label[0] = name; observations.clear(); captured.clear()
            old = json.loads(json.dumps(runtime.evidence())); old_gqa = model.grouped_attention_calls
            events = []
            for event,payload in engine.stream(request):
                events.append((event,payload))
                print('M345_EVENT ' + name + ' ' + json.dumps(dict(event=event,payload=payload),ensure_ascii=False),flush=True)
            token,logits,kv = captured['output']; new = runtime.evidence()
            row = dict(label=name,input=captured['input'],token=token,logits=tensor(logits),keys=[tensor(v) for v in kv.keys],
                values=[tensor(v) for v in kv.values],families=list(observations),grouped_attention_calls=model.grouped_attention_calls-old_gqa,
                scale_attempts=new['scale_attempts'][len(old['scale_attempts']):],snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma),
                events=events,decoder=engine.vision.decoder_evidence())
            for key in ('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','stage_bytes','logical_expected_macros','expected_macros'):
                row[{'scale_retry_count':'retry_count','pipeline_retry_launches':'retry_launches','fused_nonfinite_detections':'nonfinite_detections'}.get(key,key)] = new[key]-old[key]
            result['passes'].append(row)
            check_call_contract(row,expected_macros); row['semantic'] = validate_stream(events,row['decoder'])
            if [(o['layer'],o['family']) for o in observations] != family_plan or row['grouped_attention_calls'] != 36:
                raise RuntimeError('Complete original 36-layer model sequence differs')
            if logits.shape != (151936,) or len(kv.keys) != 36 or len(kv.values) != 36 or row['stage_bytes'] != stage_bytes:
                raise RuntimeError('Full video output/weight byte geometry differs')
            if not safe_to_release(row['snapshot']): raise RetainedBuffersError('Unsafe full video device state')
            return row,captured['input_array'],logits,kv
        baseline,baseline_hidden,baseline_logits,baseline_kv = run('baseline')
        candidate,candidate_hidden,candidate_logits,candidate_kv = run('candidate')
        compared = ('input','families','token','logits','keys','values','logical_calls','host_calls','retry_count','retry_launches',
                    'nonfinite_detections','scale_attempts','stage_bytes','logical_expected_macros','expected_macros','semantic')
        result['exact_comparison'] = {k:baseline[k] == candidate[k] for k in compared}
        result['direct_bitwise_video_hidden_equal'] = exact_array(baseline_hidden,candidate_hidden)
        result['direct_bitwise_logits_equal'] = exact_array(baseline_logits,candidate_logits)
        result['direct_bitwise_72_kv_equal'] = all(exact_array(a,b) for a,b in zip(baseline_kv.keys+baseline_kv.values,candidate_kv.keys+candidate_kv.values))
        if not all(result['exact_comparison'].values()) or not all(result[k] for k in ('direct_bitwise_video_hidden_equal','direct_bitwise_logits_equal','direct_bitwise_72_kv_equal')):
            raise RuntimeError('Original/candidate exact video logits/KV/family/semantic comparison failed')
        if session.record['stages'] != 162 or session.record['total_weight_bytes'] != stage_bytes or len(bank_records) != 162:
            raise RuntimeError('Incomplete prefetch plan')
        addresses = [r['addresses'] for r in bank_records]
        if any(addresses[i] != addresses[i%2] for i in range(162)) or set(addresses[0]) & set(addresses[1]):
            raise RuntimeError('Strict complete A-B bank alternation differs')
        phase[0] = 'independent-original-file-window-hashes'
        for (layout,chain),row in zip(plan,bank_records):
            expected = []
            for item in layout.manifest['files']:
                with (layout.root/item['path']).open('rb') as stream:
                    stream.seek(row['words']*16); raw = stream.read(row['bytes_per_shard'])
                if len(raw) != row['bytes_per_shard']: raise RuntimeError('Short original weight window')
                expected.append(hashlib.sha256(raw).hexdigest())
            if row['weight_sha256'] != expected: raise RuntimeError('Prefetch staged bytes differ from original file')
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
        if runtime is not None and base is not None and hasattr(runtime,'dma'):
            result['overlay_loaded'] = hasattr(runtime,'overlay')
            result['final_snapshot'] = base.transaction_snapshot(runtime.kernel,runtime.dma)
            unsafe = unsafe or (any_launch and not safe_to_release(result['final_snapshot']))
        if not unsafe:
            try:
                if engine is not None and engine.board is not None: engine.close()
                elif initialized and not runtime._m345_closed: runtime.close()
                elif not initialized:
                    for buffer in reversed(allocated): buffer.freebuffer()
                result['safe_buffers_released'] = True
            except BaseException as exc:
                unsafe = True; result['status'] = 'FAIL'; result['errors'].append('Release failed; retain process: ' + str(exc))
        result['unsafe_buffers_retained'] = unsafe
        if unsafe: result['status'] = 'FAIL'
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic()-started
        result['next_step'] = 'balanced interleaved fixed159 full-request A/B with matched cache and timing scope' if result['status'] == 'PASS' else 'debug fixed159-video level only; do not advance'
        write_json(path,result); raw = path.read_bytes()
        print('M345_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(),flush=True)
        chunks = [raw[i:i+1800] for i in range(0,len(raw),1800)]
        for i,chunk in enumerate(chunks): print('M345_RESULT_CHUNK=' + str(i) + '/' + str(len(chunks)) + ':' + base64.b64encode(chunk).decode(),flush=True)
        print('M345_SUMMARY=' + json.dumps(dict(status=result['status'],errors=result['errors'],unsafe=unsafe)),flush=True)
        stop.set()
        if unsafe:
            print('M345_RECOVERY_REQUIRED_RETAIN_BUFFERS_DO_NOT_INTERRUPT',flush=True)
            while True: time.sleep(30)
        if lock is not None: os.close(lock)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
