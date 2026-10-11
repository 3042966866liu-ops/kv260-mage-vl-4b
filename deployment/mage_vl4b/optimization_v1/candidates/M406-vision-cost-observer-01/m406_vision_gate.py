"""Default-off, once-only PS visual cost observation. No PYNQ/Overlay/Linear changes."""
import base64
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace
import weakref

from m406_vision_observer import Observer, CpuSampler, backend_evidence, proc_snapshot

HERE = Path(__file__).resolve().parent
OUTPUT = Path('/home/ubuntu/m406_vision_cost_observation_01/RESULT.json')
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def tensor(value):
    return dict(shape=list(value.shape), dtype=str(value.dtype), bytes=int(value.nbytes),
                sha256=hashlib.sha256(value.tobytes()).hexdigest())


def verify(expected):
    if sha(HERE / 'PACKAGE_MANIFEST.json') != expected:
        raise RuntimeError('Package manifest differs')
    manifest = json.loads((HERE / 'PACKAGE_MANIFEST.json').read_bytes())
    names = {r['path'] for r in manifest['files']}
    if len(names) != manifest['file_count'] or {p.name for p in HERE.iterdir()} != names | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Package whitelist differs')
    for row in manifest['files']:
        p = HERE / row['path']
        if p.name != row['path'] or p.is_symlink() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Package file differs: ' + row['path'])
    if sum(x['bytes'] for x in manifest['files']) != manifest['total_bytes']:
        raise RuntimeError('Package byte total differs')
    ids = json.loads((HERE / 'M348_SOURCE_IDENTITIES.json').read_bytes())
    for row in ids['files']:
        p = RELEASE / row['path']
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Installed frozen source differs: ' + row['path'])
    return ids


def component(torch, linear_cls, source):
    import numpy as np
    class Store:
        def decode(self, name):
            return np.asarray([[.25, -2, 1, 0], [3, .5, -1, 7], [-.125, 2, 0, -1]], np.float32).copy()
    class Vision(torch.nn.Module):
        def __init__(self, dtype):
            super().__init__()
            self.linear = linear_cls(torch, Store(), 'fixture', 4, 3, False, dtype)
        def forward(self, value):
            return self.linear(value)
    original_to = torch.Tensor.to
    original_forward = linear_cls.forward
    cases = []
    for dtype in (torch.float32, torch.bfloat16):
        for scale in (0., .03125, 1., 128.):
            vision = Vision(dtype)
            values = torch.from_numpy(np.asarray([[1, -2, .1, 4], [-.5, 7, 3, -1]], np.float32) * scale).to(dtype)
            with torch.inference_mode():
                reference = vision(values)
                with Observer(SimpleNamespace(torch=torch, vision=vision), linear_cls, source) as obs:
                    with obs.clock.phase('fixture', 'vision_total'):
                        answer = vision(values)
                assert torch.equal(reference, answer)
            assert torch.Tensor.to is original_to and linear_cls.forward is original_forward
            evidence = obs.clock.evidence()
            assert sum(x['calls'] for x in evidence['rows'] if x['category'] == 'linear_gemm') == 1
            cases.append(dict(dtype=str(dtype), scale=scale, bit_exact=True))
    vision = Vision(torch.float32)
    old = torch.nn.functional.linear
    def fail(*args, **kwargs):
        raise RuntimeError('M406 intentional GEMM exception fixture')
    torch.nn.functional.linear = fail
    try:
        try:
            with Observer(SimpleNamespace(torch=torch, vision=vision), linear_cls, source) as obs:
                with obs.clock.phase('fixture', 'vision_total'):
                    vision(torch.zeros((1, 4)))
        except RuntimeError as error:
            assert 'intentional GEMM' in str(error)
        else:
            raise AssertionError('Original exception not propagated')
    finally:
        torch.nn.functional.linear = old
    assert torch.Tensor.to is original_to and linear_cls.forward is original_forward
    assert not obs.restore and not obs.clock.stack
    return dict(real_torch_fixture_cases=cases, exception_propagated=True, bindings_restored=True,
                source_AST_restoration_exact=True, FPGA_or_actual_model_evidence=False)


def export():
    if os.geteuid() != 0:
        raise RuntimeError('Root export required')
    raw = OUTPUT.read_bytes()
    parts = [raw[i:i+900] for i in range(0, len(raw), 900)]
    print('M406_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
    for i, part in enumerate(parts):
        print(f'M406_RESULT_CHUNK={i}/{len(parts)}:' + base64.b64encode(part).decode('ascii'), flush=True)
        time.sleep(.025)


def main():
    if sys.argv[1:] == ['Collect']:
        export()
        return 0
    if len(sys.argv) != 3 or sys.argv[2] != '--enable-PS-vision-observation':
        raise RuntimeError('PS visual observation disabled by default')
    if os.geteuid() != 0:
        raise RuntimeError('Same-terminal root required')
    ids = verify(sys.argv[1])
    if OUTPUT.parent.exists():
        raise RuntimeError('Existing observation; Collect only')
    OUTPUT.parent.mkdir()
    started = time.monotonic()
    result = dict(status='FAIL_PS_VISUAL_COST_OBSERVATION', gate_return_code=1, errors=[],
                  gate_level='PS-only-fixed-input-visual-cost-observation',
                  manifest_sha256=sys.argv[1], build_context='0x4D333537-language-not-executed',
                  overlay_loaded=False, dma_allocations=0, language_forward_calls=0, fpga_transactions=0,
                  visual_forward_calls=0, cache_policy_changed=False, thread_settings_changed=False,
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
                  component_pass=False, bindings_restored=False, visual_owner_closed=False,
                  source_identities_verified=len(ids['files']))
    runtime = observer = None
    try:
        from frozen_video_identity import module_paths, verify_m277_release_subset, ADDON, FRAMES, STACK_SHA
        result['m277_release_subset'] = verify_m277_release_subset(RELEASE / 'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0] = [str(p) for p in module_paths()]
        spec = importlib.util.spec_from_file_location('release_preflight', RELEASE / 'scripts/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        checked = preflight.inspect(json.loads((RELEASE / 'configs/deployment.example.json').read_bytes()), port_check=True)
        result['release_preflight'] = {k: checked[k] for k in ('status', 'missing', 'hash_or_identity_mismatch', 'port_free')}
        if checked['status'] != 'READY_FOR_BOARD_PREFLIGHT':
            raise RuntimeError('Original complete asset preflight rejected; no model')
        import numpy as np
        import torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m273_latest_multiscale_contract import preprocess
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        # Recheck actual import resolution, not only the bytes at expected paths.
        imports = {name: sys.modules[name] for name in ('ps_vision_runtime', 'm206_ps_vision_runtime',
                   'm207_ps_vision_runtime', 'm222_vectorized_w4_runtime', 'm258_vectorized_w4_runtime',
                   'm259_variable_vision_runtime', 'm260_cached_w4_runtime',
                   'm261_budgeted_w4_runtime', 'm273_latest_vision_runtime', 'm273_latest_multiscale_contract')}
        identities = {x['path']: x for x in ids['files']}
        result['resolved_modules'] = {}
        for name, module in imports.items():
            path = Path(module.__file__).resolve()
            rel = path.relative_to(RELEASE).as_posix()
            row = identities[rel]
            if sha(path) != row['sha256']:
                raise RuntimeError('Actual import identity differs')
            result['resolved_modules'][name] = dict(path=rel, sha256=row['sha256'])
        source = Path(imports['m207_ps_vision_runtime'].__file__).read_text(encoding='utf-8')
        result['backend_before'] = backend_evidence(torch)
        result['component'] = component(torch, M207FP32GemmW4Linear, source)
        result['component_pass'] = True
        frames = []
        for name, digest in FRAMES.items():
            path = ADDON / 'fixtures' / name
            if sha(path) != digest:
                raise RuntimeError('Frame file SHA differs')
            frames.append(np.load(path, allow_pickle=False))
        frames = np.ascontiguousarray(np.stack(frames))
        if frames.shape != (4, 448, 448, 3) or frames.dtype != np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest() != STACK_SHA:
            raise RuntimeError('Ordered input stack differs')
        tensors = preprocess(np.ascontiguousarray(frames[-1:]))
        expected = json.loads((HERE / 'EXPECTED.json').read_bytes())
        if {k: tensor(v) for k, v in sorted(tensors.items())} != expected['preprocessed']:
            raise RuntimeError('Original preprocessed tensors differ')
        base = RELEASE / 'deployment/mage_vl4b/m181_m120_video_board_candidate'
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))) * 1024
        if available < (1 << 30) + (64 << 20):
            raise RuntimeError('PS memory entry budget insufficient')
        result['before_constructor'] = proc_snapshot()
        runtime = M273LatestPSVisionRuntime(base / 'ps_vision_payload', base / 'vision_layout',
                                            base / 'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
        owner_ref = weakref.ref(runtime)
        result['attention_implementations'] = sorted({str(m.config._attn_implementation) for m in runtime.vision.modules()
                                                       if type(m).__name__ == 'MageVLVisionAttention'})
        result['warmup_before'] = proc_snapshot()
        result['visual_forward_calls'] += 1
        visual = runtime(tensors['pixel_values'], tensors['image_grid_thw'], tensors['patch_positions'])
        if tensor(visual) != expected['visual']:
            raise RuntimeError('Visual warmup differs from frozen reference')
        del visual
        result['warmup_after'] = proc_snapshot()
        result['before_cache'] = runtime.decoder_evidence()
        if result['before_cache']['cache_entries'] != 26 or result['before_cache']['cache_bytes'] != 66699264:
            raise RuntimeError('Original visual cache contract differs')
        result['visual_forward_calls'] += 1
        original_forward, original_to = M207FP32GemmW4Linear.forward, torch.Tensor.to
        observer = Observer(runtime, M207FP32GemmW4Linear, source)
        # Native operator report explains dispatcher execution, not normal request performance.
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU], record_shapes=False,
                                    profile_memory=False, with_stack=False) as native:
            with observer:
                with CpuSampler(observer.clock) as sampler:
                    with observer.clock.phase('original-M273-call', 'vision_total'):
                        visual = runtime(tensors['pixel_values'], tensors['image_grid_thw'], tensors['patch_positions'])
        result['bindings_restored'] = not observer.restore and M207FP32GemmW4Linear.forward is original_forward and torch.Tensor.to is original_to
        result['costs'] = observer.clock.evidence()
        result['cpu_observation'] = sampler.evidence()
        result['native_cpu_operators'] = [dict(name=e.key, calls=e.count,
            self_cpu_time_us=e.self_cpu_time_total, inclusive_cpu_time_us=e.cpu_time_total)
            for e in native.key_averages()]
        if len(result['native_cpu_operators']) > 400:
            raise RuntimeError('Native operator summary budget exceeded')
        result['native_operator_times_are_not_additive_wall_time'] = True
        result['after_cache'] = runtime.decoder_evidence()
        result['visual'] = tensor(visual)
        result['numerical_pass'] = result['visual'] == expected['visual']
        if not result['numerical_pass'] or not result['bindings_restored']:
            raise RuntimeError('Observed numerical/restore check failed')
        rows = result['costs']['rows']
        gemms = [x for x in rows if x['category'] == 'linear_gemm']
        if len(gemms) != 98 or sum(x['calls'] for x in gemms) != 98:
            raise RuntimeError('Actual visual Linear coverage incomplete')
        if sum(x['calls'] for x in rows if x['category'] == 'encoder_layer_other') != 24:
            raise RuntimeError('Actual visual layer coverage incomplete')
        result['backend_after'] = backend_evidence(torch)
        if result['backend_before'] != result['backend_after']:
            raise RuntimeError('Backend or settings changed')
        result['no_pynq_import'] = not any(n == 'pynq' or n.startswith('pynq.') for n in sys.modules)
        if not result['no_pynq_import']:
            raise RuntimeError('Unexpected PYNQ import in PS-only path')
        if (result['costs']['vision_wall_ns'] > 90e9 or time.monotonic() - started > 600):
            raise RuntimeError('Observation budget exceeded; no additional request')
        del visual, observer, native
        observer = None
        runtime.close()
        runtime = None
        gc.collect()
        result['visual_owner_closed'] = owner_ref() is None
        result['after_release'] = proc_snapshot()
        if not result['visual_owner_closed']:
            raise RuntimeError('Visual owner retained unexpectedly')
        result.update(status='PASS_PS_VISUAL_COST_OBSERVATION', gate_return_code=0)
    except BaseException as error:
        result['errors'].append(dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
    finally:
        if observer is not None:
            observer.__exit__(None, None, None)
            observer = None
        if runtime is not None:
            runtime.close()
            runtime = None
            gc.collect()
            result['failure_visual_owner_close_called'] = True
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic() - started
        blob = (json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        temp = OUTPUT.with_suffix('.partial')
        with temp.open('xb') as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, OUTPUT)
    return result['gate_return_code']


if __name__ == '__main__':
    raise SystemExit(main())
