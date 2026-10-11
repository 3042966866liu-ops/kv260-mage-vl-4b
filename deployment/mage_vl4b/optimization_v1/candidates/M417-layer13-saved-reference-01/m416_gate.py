"""Default-off one original visual capture, followed by local MLP-only A8 QDQ."""
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
import weakref
from m408_mlp_capture04 import Capture, SHAPES, qdq_matrix, compare
from m408_component04 import component
from m416_target13 import resolve_target, verify_matrices
from m414_entry import run_component, retain_reference
from m406_vision_observer import backend_evidence, proc_snapshot

HERE = Path(__file__).resolve().parent
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
OUTPUT = Path('/home/ubuntu/m416_layer13_capture_01/RESULT.json')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''): h.update(block)
    return h.hexdigest()


def tensor(value):
    import numpy as np
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all(): raise FloatingPointError('Nonfinite tensor')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())


def verify(expected):
    if sha(HERE/'PACKAGE_MANIFEST.json') != expected: raise RuntimeError('Package identity differs')
    manifest = json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes())
    names = {x['path'] for x in manifest['files']}
    if len(names) != manifest['file_count'] or {p.name for p in HERE.iterdir()} != names | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Whitelist differs')
    for row in manifest['files']:
        p = HERE/row['path']
        if p.name != row['path'] or p.is_symlink() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Payload differs: ' + row['path'])
    if sum(x['bytes'] for x in manifest['files']) != manifest['total_bytes']: raise RuntimeError('Byte count differs')
    ids = json.loads((HERE/'M348_SOURCE_IDENTITIES.json').read_bytes())
    for row in ids['files']:
        p = RELEASE/row['path']
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Installed source differs: ' + row['path'])
    plan = json.loads((HERE/'PREREQUISITE.json').read_bytes())
    if plan['contract_sha256'] != 'f59ef66f9ad1252272f17f878a9f76f26443ef0962853bd10d8ba80d0266ab89' or plan['layout_closure_sha256'] != '60d40d15fcea261b84acb1a598be0fafb64e7ac54a12a88c59fab8744829aec2':
        raise RuntimeError('M407 strict prerequisite differs')
    layout = RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
    if sha(layout) != plan['layout_sha256']: raise RuntimeError('Visual layout identity differs')
    return ids


def save_arrays(values):
    """Retain bounded versioned PS capture files, never arbitrary historical tensors."""
    import numpy as np
    rows = []
    for name, value in sorted(values.items()):
        if name not in SHAPES or tuple(value.shape) != SHAPES[name] or value.dtype != np.float32:
            raise RuntimeError('Capture file contract differs')
        target = OUTPUT.parent/(name+'.npy')
        temp = target.with_suffix('.partial')
        with temp.open('xb') as f:
            np.save(f, value, allow_pickle=False); f.flush(); os.fsync(f.fileno())
        os.replace(temp, target)
        rows.append(dict(path=target.name, file_bytes=target.stat().st_size, file_sha256=sha(target), tensor=tensor(value)))
    if sum(x['file_bytes'] for x in rows) > (32 << 20): raise RuntimeError('Capture file budget exceeded')
    path = OUTPUT.parent/'CAPTURE_MANIFEST.json'
    blob = (json.dumps(dict(default_off=True, semantic_quality_proven=False, PL_arithmetic_proven=False,
                          files=rows), indent=2, allow_nan=False)+'\n').encode('utf-8')
    with path.with_suffix('.partial').open('xb') as f: f.write(blob); f.flush(); os.fsync(f.fileno())
    os.replace(path.with_suffix('.partial'), path)
    return dict(path=str(path), sha256=sha(path), files=rows)


def export():
    if os.geteuid() != 0: raise RuntimeError('Root saved-only export required')
    raw = OUTPUT.read_bytes()
    if not 0 < len(raw) <= 1<<20: raise RuntimeError('Bounded saved result required')
    parts = [raw[i:i+900] for i in range(0, len(raw), 900)]
    print('M416_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(), flush=True)
    for i, part in enumerate(parts):
        print(f'M416_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(part).decode('ascii'), flush=True)
        time.sleep(.16)


def main():
    if sys.argv[1:] == ['Collect']: export(); return 0
    if len(sys.argv) != 3 or sys.argv[2] != '--enable-local-MLP-A8-screen': raise RuntimeError('Default-off MLP screen')
    if os.geteuid() != 0: raise RuntimeError('Same-terminal root required')
    if OUTPUT.parent.exists(): raise RuntimeError('Original capture exists; Collect only')
    OUTPUT.parent.mkdir()
    started = time.monotonic()
    result = dict(status='FAIL_M416_PS_LOCAL_MLP_CAPTURE_A8_SCREEN', gate_return_code=1, errors=[],
        gate_level='PS-only-real-input-local-MLP-A8-rejection-screen', manifest_sha256=sys.argv[1],
        overlay_loaded=False, dma_allocations=0, fpga_transactions=0, language_forward_calls=0,
        visual_forward_calls=0, local_mlp_forward_calls=0, selected_layer=13,
        cache_policy_changed=False, thread_settings_changed=False, PL_arithmetic_proven=False,
        semantic_quality_proven=False, performance_pass=False, formal_promotion_allowed=False,
        component_pass=False, capture_exact=False, local_A8_screen_pass=False, bindings_restored=False,
        visual_owner_closed=False)
    runtime = captured = replay = candidate = mlp = layer = None
    try:
        ids = verify(sys.argv[1]); result['source_identities_verified'] = len(ids['files'])
        from frozen_video_identity import module_paths, verify_m277_release_subset, FRAMES, ADDON, STACK_SHA
        result['m277_release_subset'] = verify_m277_release_subset(RELEASE/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate')
        sys.path[:0] = [str(p) for p in module_paths()]
        spec = importlib.util.spec_from_file_location('release_preflight', RELEASE/'scripts/preflight.py')
        preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
        checked = preflight.inspect(json.loads((RELEASE/'configs/deployment.example.json').read_bytes()), port_check=True)
        result['release_preflight'] = {k: checked[k] for k in ('status','missing','hash_or_identity_mismatch','port_free')}
        if checked['status'] != 'READY_FOR_BOARD_PREFLIGHT': raise RuntimeError('Original complete asset preflight rejected')
        import numpy as np
        import torch
        from m273_latest_vision_runtime import M273LatestPSVisionRuntime
        from m273_latest_multiscale_contract import preprocess
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        import contract_runtime
        names = ('ps_vision_runtime','m206_ps_vision_runtime','m207_ps_vision_runtime',
                 'm222_vectorized_w4_runtime','m258_vectorized_w4_runtime','m259_variable_vision_runtime',
                 'm260_cached_w4_runtime','m261_budgeted_w4_runtime','m273_latest_vision_runtime',
                 'm273_latest_multiscale_contract','contract_runtime')
        identities = {x['path']: x for x in ids['files']}; result['resolved_modules'] = {}
        for name in names:
            path = Path(sys.modules[name].__file__).resolve(); rel = path.relative_to(RELEASE).as_posix()
            if sha(path) != identities[rel]['sha256']: raise RuntimeError('Actual resolved module differs: '+name)
            result['resolved_modules'][name] = dict(path=rel, sha256=identities[rel]['sha256'])
        result['backend_before'] = backend_evidence(torch)
        checked_component, result['component_isolation'] = run_component(RELEASE,OUTPUT.parent,HERE/'m416_component_entry.py')
        result['component'] = checked_component['component']
        result['target_component'] = checked_component['target_component']
        result['component_pass'] = True
        frames = []
        for name, digest in FRAMES.items():
            path = ADDON/'fixtures'/name
            if sha(path) != digest: raise RuntimeError('Fixed frame differs')
            frames.append(np.load(path, allow_pickle=False))
        frames = np.ascontiguousarray(np.stack(frames))
        if frames.shape != (4,448,448,3) or frames.dtype != np.uint8 or hashlib.sha256(frames.tobytes()).hexdigest() != STACK_SHA:
            raise RuntimeError('Fixed ordered frame stack differs')
        tensors = preprocess(np.ascontiguousarray(frames[-1:]))
        expected = json.loads((HERE/'EXPECTED.json').read_bytes())
        result['preprocessed'] = {k: tensor(v) for k,v in sorted(tensors.items())}
        if result['preprocessed'] != expected['preprocessed']: raise RuntimeError('Fixed preprocess differs')
        available = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
        if available < (1 << 30)+(192 << 20)+(64 << 20): raise RuntimeError('PS construction/capture transient budget insufficient')
        result['memory_before_constructor'] = proc_snapshot()
        base = RELEASE/'deployment/mage_vl4b/m181_m120_video_board_candidate'
        runtime = M273LatestPSVisionRuntime(base/'ps_vision_payload',base/'vision_layout',base/'auxiliary/M90_VISION_RAW_AUX_MANIFEST.json')
        owner_ref = weakref.ref(runtime)
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        layer,result['target_resolution'] = resolve_target(runtime.vision,M206ProgressLayer,M196PrecisionBoundary,torch)
        mlp = layer.mlp
        result['target_matrices'] = verify_matrices(layer,M207FP32GemmW4Linear,torch)
        target_expected = json.loads((HERE/'EXPECTED_TARGET.json').read_bytes())
        if result['target_resolution'] != target_expected['topology'] or result['target_matrices'] != target_expected['matrices']: raise RuntimeError('Actual constructor target identity differs')
        result['visual_forward_calls'] = 1
        with Capture(mlp, norm=layer.layer_norm2) as captured:
            visual = runtime(tensors['pixel_values'],tensors['image_grid_thw'],tensors['patch_positions'])
        captured.require_complete()
        result['bindings_restored'] = captured.restored
        result['native_capture_shapes'] = captured.native_shapes
        if captured.native_shapes != {k:[1,*s] for k,s in SHAPES.items()}: raise RuntimeError('Original native batch geometry differs')
        result['visual'] = tensor(visual)
        if result['visual'] != expected['visual']:
            result['failed_reference_files'] = retain_reference(OUTPUT.parent,visual,captured.values)
            raise RuntimeError('Original visual reference differs')
        del visual
        result['memory_after_capture'] = proc_snapshot()
        result['capture_manifest'] = save_arrays(captured.values)
        result['capture'] = {k:tensor(v) for k,v in captured.values.items()}
        with torch.inference_mode():
            x = torch.from_numpy(captured.values['input']).unsqueeze(0)
            result['local_mlp_forward_calls'] += 1
            with Capture(mlp) as replay: mlp(x)
            replay.require_complete()
            if any(not np.array_equal(captured.values[k].view(np.uint32),v.view(np.uint32)) for k,v in replay.values.items()):
                raise RuntimeError('Retained real-input MLP replay differs from capture')
            result['capture_exact'] = True
            batches = {}
            def qdq(key,value):
                if list(value.shape) != [1,*SHAPES[key]]: raise RuntimeError('Original QDQ native rank differs')
                arr, rows = qdq_matrix(value.detach().numpy()[0],contract_runtime.quantize_t32)
                batches[key] = rows
                return torch.from_numpy(arr).unsqueeze(0)
            result['local_mlp_forward_calls'] += 1
            with Capture(mlp, qdq=qdq) as candidate: mlp(x)
            candidate.require_complete()
            result['quality_metrics'], result['local_A8_screen_pass'] = compare(captured.values,candidate.values)
            result['A8_batches'] = batches
            if set(batches) != {'input','gelu'} or any([r['rows'] for r in v] != [32]*12+[8] for v in batches.values()):
                raise RuntimeError('Two actual 392-row T32 activation contracts incomplete')
            result['candidate_tensors'] = {k:tensor(v) for k,v in candidate.values.items()}
        result['bindings_restored'] = all(o.restored for o in (captured,replay,candidate))
        result['backend_after'] = backend_evidence(torch)
        if result['backend_before'] != result['backend_after']: raise RuntimeError('Backend changed')
        result['no_pynq_import'] = not any(n == 'pynq' or n.startswith('pynq.') for n in sys.modules)
        if not result['no_pynq_import']: raise RuntimeError('Unexpected PYNQ import')
        if time.monotonic()-started > 600: raise RuntimeError('Bounded capture budget exceeded; no additional run')
        del x, qdq
        captured = replay = candidate = mlp = layer = None
        runtime.close(); runtime = None; gc.collect()
        result['visual_owner_closed'] = owner_ref() is None
        result['memory_after_release'] = proc_snapshot()
        if not result['bindings_restored'] or not result['visual_owner_closed']: raise RuntimeError('Lifecycle incomplete')
        if not result['local_A8_screen_pass']: raise RuntimeError('Local A8 rejection screen failed; stop before PL')
        result.update(status='PASS_M416_PS_LOCAL_MLP_CAPTURE_A8_SCREEN',gate_return_code=0)
    except BaseException as error:
        result['errors'].append(dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
    finally:
        for obj in (captured,replay,candidate):
            if obj is not None and obj.handles: obj.__exit__(None,None,None)
        result['bindings_restored'] = all(obj.restored for obj in (captured,replay,candidate) if obj is not None)
        captured = replay = candidate = mlp = layer = None
        if runtime is not None:
            runtime.close(); runtime = None; gc.collect()
            result['failure_visual_owner_close_called'] = True
        result['elapsed_s_diagnostic_not_performance'] = time.monotonic()-started
        raw = (json.dumps(result,ensure_ascii=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
        temp = OUTPUT.with_suffix('.partial')
        with temp.open('xb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temp,OUTPUT)
    return result['gate_return_code']


if __name__ == '__main__': raise SystemExit(main())
