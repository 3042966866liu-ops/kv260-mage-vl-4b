"""Actual late11 provider with frozen native wrappers, explicit fake DMA and narrow weights."""
import ast
import copy
import hashlib
import tempfile
import __future__
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import sys
import numpy as np
from m432_request_visual import VisualProvider
from m428_saved_features import tensor
from m431_window_component import Buffer
from m431_borrowed_visual import SIZES


def component(root, fixture_root):
    import torch
    source = Path(__file__).with_name('test_m430_timing.py')
    fn = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(n, ast.FunctionDef) and n.name == 'component')
    setup = copy.deepcopy(fn)
    stop = next(i for i, n in enumerate(setup.body) if isinstance(n, ast.With))
    setup.name = 'setup'
    setup.body = setup.body[:stop] + [ast.Return(value=ast.Call(func=ast.Name(id='locals', ctx=ast.Load()), args=[], keywords=[]))]
    namespace = dict(Path=Path, ast=ast, __future__=__future__, hashlib=hashlib, json=__import__('json'), sys=sys,
                     threading=threading, time=time, SimpleNamespace=SimpleNamespace, np=np)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[setup], type_ignores=[])), str(source), 'exec'), namespace)
    q = namespace['setup'](root)
    layers, targets, cases, host, initial, forward, wire, capture = (q[k] for k in ('layers', 'targets', 'cases', 'host', 'initial', 'forward', 'wire', 'CaptureScope'))
    boundaries = []
    with torch.inference_mode():
        original = forward().float().detach().numpy()[0]
        with capture(torch, layers, targets, tuple(range(13, 24)), 'software', lambda i: cases[i], initial, host,
                     lambda i, a: boundaries.append(dict(layer=i, candidate=tensor(a))), lambda *x: None) as oracle:
            software = forward().float().detach().numpy()[0]
    refs = copy.deepcopy(oracle.batches)
    assert len(wire) == 286 and len(boundaries) == 24 and q['clean']()
    arrays = [Buffer(n) for n in SIZES]
    kernel = SimpleNamespace(writes=[])
    kernel.write = lambda r, v: kernel.writes.append((r, v))
    rt = SimpleNamespace(staged_buffers=arrays[:4], input_buffer=arrays[4], output_buffer=arrays[5], output_buffer_alt=arrays[6],
                         kernel=kernel, _programmed_config=123, _programmed_weight_addresses=(1, 2, 3, 4))
    policy = SimpleNamespace(sealed=True, buffer_bytes=list(SIZES), ever=True, completed=True, active=False, build=0x4d333537)
    policy.safe = lambda: not policy.active and policy.completed
    pending = {}; fail_layer = None; submitted = []
    def capture_policy(label, check):
        if label.startswith('before-visual-submit:'):
            _, i, part = label.split(':'); pending['layer'], pending['part'] = int(i), part
    policy.capture = capture_policy
    def receive(buffer, nbytes):
        pending['buffer'], pending['nbytes'] = buffer, nbytes
    rt.dma = SimpleNamespace(recvchannel=SimpleNamespace(transfer=receive), sendchannel=SimpleNamespace(transfer=lambda *a, **k: None))
    snapshot = dict(ap_ctrl=4, ap_return=0x4d333537, mm2s_dmasr=4098, s2mm_dmasr=4098,
                    kernel_read_error='', return_read_error='', dma_read_error='')
    def wait(*unused):
        i, part = pending['layer'], pending['part']
        if i == fail_layer:
            raise TimeoutError('Explicit fake active layer14 DMA timeout')
        ref = refs[str(i)][part][len(submitted) % 13]
        key = (i, part, ref['start'], ref['selected_shift'])
        packet, raw = wire[key]
        assert bytes(memoryview(arrays[4])[:len(packet)]) == packet and pending['nbytes'] == len(raw)
        for b, expected in zip(arrays[:4], cases[i]['windows'][part]):
            assert bytes(memoryview(b)[:len(expected)]) == expected
        pending['buffer'][:len(raw)] = np.frombuffer(raw, np.uint8)
        submitted.append(key)
        return copy.deepcopy(snapshot)
    base = SimpleNamespace(REG_POINTERS=(16, 28, 40, 52), REG_CONFIG=64, REG_AP_CTRL=0,
                           physical_address=lambda b: id(b), write_u64=lambda k, r, v: k.write(r, v), wait_transaction=wait)
    values = dict(pixel_values=np.zeros(1, np.float32), image_grid_thw=np.zeros(1, np.int32), patch_positions=np.zeros(1, np.int32))
    with tempfile.TemporaryDirectory(dir=fixture_root, prefix='m432-provider-') as temp:
        folder = Path(temp); windows = {}
        for i in range(13, 24):
            windows[i] = {}
            for part in ('fc1', 'fc2'):
                rows = []
                for port, data in enumerate(cases[i]['windows'][part]):
                    name = f'{i}_{part}_{port}'; (folder / name).write_bytes(data)
                    rows.append(dict(relative_file=name, file_bytes=len(data), bytes=len(data), offset=0))
                windows[i][part] = rows
        def create():
            provider = VisualProvider.__new__(VisualProvider)
            record = dict(integrated_visual=[], visual_staging=[], visual_transactions=[], borrowed_extra_DMA=0, vision_forward_calls=0)
            def visual(*unused):
                assert record.get('vision_request_active') is True
                record['vision_forward_calls'] += 1
                return forward().float().detach().numpy()[0]
            vision = SimpleNamespace(vision=SimpleNamespace(encoder=SimpleNamespace(layers=layers)))
            # A callable facade keeps the actual provider's full nested model path.
            class Facade:
                def __init__(self): self.vision = vision.vision
                def __call__(self, *args): return visual(*args)
            provider.engine = SimpleNamespace(vision=Facade())
            provider.runtime, provider.policy, provider.base, provider.result = rt, policy, base, record
            provider.targets, provider.torch, provider.host, provider.initial = targets, torch, host, initial
            provider.cases = {i: cases[i]['chains'] for i in range(13, 24)}
            provider.windows, provider.reference, provider.root = windows, refs, folder
            provider.frames = np.zeros((4, 1, 1, 3), np.uint8); provider.preprocess = lambda *x: values
            provider.sources = dict(visual=dict(preprocessed={k: tensor(v) for k, v in sorted(values.items())}))
            provider.accepted = dict(boundary_comparison=boundaries)
            provider.plan = dict(features=[dict(tensor=tensor(x)) for x in (original, software)])
            provider.current_owner = provider.current_scope = None; provider.disposed = False
            return provider
        p = create()
        with torch.inference_mode():
            assert tensor(p(0)) == tensor(original)
            rt._programmed_config = 0x11223344
            assert tensor(p(1)) == tensor(software)
        assert len(submitted) == 286 and p.result['visual_matched_wire_batches'] == 286 and len(p.result['integrated_boundaries']) == 24
        assert len(p.result['visual_staging']) == 22 and p.result['peak_live_visual_layer_scopes'] == 1 and q['clean']()
        assert tuple(id(x) for x in arrays) == tuple(id(x) for x in tuple(rt.staged_buffers) + (rt.input_buffer, rt.output_buffer, rt.output_buffer_alt))
        assert rt._programmed_config is None and rt._programmed_weight_addresses is None and not policy.active
        p.dispose(); assert p.disposed and p.targets is None
        submitted.clear(); fail_layer = 14
        bad = create(); bad.result['integrated_visual'] = [tensor(original)]
        with torch.inference_mode():
            try: bad(1)
            except TimeoutError: pass
            else: raise AssertionError('Active DMA failure not propagated')
        assert policy.active and bad.current_owner is not None and bad.current_owner.retained and q['clean']()
        try: bad.dispose()
        except RuntimeError: pass
        else: raise AssertionError('Active owner disposed')
    return dict(actual_provider_call=True, frozen_native24_wrappers_encoder_M207_and_binding=True,
                synthetic_narrow_MLP_weights_and_attention=True, fake_DMA_MMIO_memory=True,
                complete286_input_output_packets_and24_boundaries_exact=True, stages=22,
                original_array_bytes=sum(SIZES), extra_DMA_allocate_or_free_calls=0,
                one_live_layer_scope=True, static_cache_invalidated=True, successful_disposal=True,
                active_second_layer_timeout_preserves_original_owner_and_restores_bindings=True,
                no_board_or_complete_runtime_capacity_or_model_quality_or_performance=True)
