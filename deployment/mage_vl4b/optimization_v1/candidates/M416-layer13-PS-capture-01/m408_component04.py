"""Real Torch CPU fixture checks; not real-model or FPGA evidence."""
import numpy as np
from m408_mlp_capture04 import Capture, qdq_matrix, compare


def component(torch, quantize, linear_cls=None):
    shapes = {k: (3, 128 if k in ('fc1', 'gelu') else 64) for k in
              ('input', 'fc1', 'gelu', 'fc2', 'output')}
    class Store:
        def decode(self, name):
            n, k = (128, 64) if name == 'fc1' else (64, 128)
            return ((np.arange(n*k, dtype=np.int32).reshape(n, k) % 17 - 8) * np.float32(.001)).astype(np.float32)
    store = Store()
    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__()
            if linear_cls is not None:
                self.fc1 = linear_cls(torch, store, 'fc1', 64, 128, False, torch.float32)
                self.fc2 = linear_cls(torch, store, 'fc2', 128, 64, False, torch.float32)
            else:
                self.fc1, self.fc2 = torch.nn.Linear(64, 128), torch.nn.Linear(128, 64)
                with torch.no_grad():
                    self.fc1.weight.copy_(torch.from_numpy(store.decode('fc1')))
                    self.fc2.weight.copy_(torch.from_numpy(store.decode('fc2')))
                    self.fc1.bias.zero_(); self.fc2.bias.zero_()
        def forward(self, x): return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
    mlp = MLP()
    x = torch.from_numpy(((np.arange(192, dtype=np.int32) % 31 - 15).astype(np.float32) * np.float32(.013)).reshape(3, 64))
    before = [(m, tuple(m._forward_hooks), tuple(m._forward_pre_hooks)) for m in mlp.modules()]
    with torch.inference_mode():
        gold = mlp(x)
        with Capture(mlp, shapes=shapes) as capture: answer = mlp(x)
        capture.require_complete()
        assert capture.restored and torch.equal(gold, answer)
        seen = {}
        def qdq(key, value):
            arr, batches = qdq_matrix(value.numpy(), quantize)
            seen[key] = batches
            return torch.from_numpy(arr)
        with Capture(mlp, shapes=shapes, qdq=qdq) as candidate: mlp(x)
        candidate.require_complete()
        comparison, passed = compare(capture.values, candidate.values)
        assert candidate.restored and passed and set(seen) == {'input', 'gelu'}
    # Exception and duplicate call must restore all actual instance hooks.
    old = mlp.fc2.forward
    def fail(*args): raise RuntimeError('M408 intentional original exception')
    mlp.fc2.forward = fail
    try:
        try:
            with Capture(mlp, shapes=shapes): mlp(x)
        except RuntimeError as e: assert 'intentional' in str(e)
        else: raise AssertionError('Exception not propagated')
    finally: mlp.fc2.forward = old
    try:
        with Capture(mlp, shapes=shapes): mlp(x); mlp(x)
    except RuntimeError as e: assert 'Duplicate target' in str(e)
    else: raise AssertionError('Unbounded historical capture accepted')
    assert all(tuple(m._forward_hooks) == post and tuple(m._forward_pre_hooks) == pre
               for m, post, pre in before)
    bads = [np.full((3, 64), np.nan, np.float32), np.full((3, 64), 1e-30, np.float32),
            np.ones((3, 63), np.float32), np.ones((393, 64), np.float32), np.ones((3, 64), np.float64)]
    rejects = 0
    for value in bads:
        try: qdq_matrix(value, quantize)
        except (ValueError, FloatingPointError): rejects += 1
        else: raise AssertionError('Invalid quantization accepted')
    value = (np.arange(392*64, dtype=np.int32) % 29 - 14).astype(np.float32).reshape(392, 64) * np.float32(.125)
    restored, batches = qdq_matrix(value, quantize)
    assert [x['rows'] for x in batches] == [32]*12 + [8] and np.isfinite(restored).all()
    zeros, _ = qdq_matrix(np.zeros((8, 64), np.float32), quantize)
    assert not zeros.any()
    return dict(real_torch_CPU=True, actual_M207_class=linear_cls is not None,
        exact_original_fixture=True, qdq_fixture_screen=passed, comparison=comparison,
        exception_and_duplicate_restoration=True, original_hooks_restored=True,
        rejects=rejects, full_392_T32_geometry=True, zero_groups=True,
        real_model_or_PL_evidence=False)


if __name__ == '__main__':
    import ast, hashlib, importlib.util, json, sys
    from pathlib import Path
    from types import SimpleNamespace
    import torch
    root = Path(__file__).resolve().parents[2]
    path = root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
    spec = importlib.util.spec_from_file_location('frozen_contract', path)
    host = importlib.util.module_from_spec(spec); sys.modules[spec.name] = host; spec.loader.exec_module(host)
    source = root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py'
    tree = ast.parse(source.read_text(encoding='utf-8-sig'))
    cls = next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name == 'M207FP32GemmW4Linear')
    ns = dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(source),'exec'),ns)
    result = component(torch, host.quantize_t32, ns['M207FP32GemmW4Linear'])
    result['actual_frozen_class_AST_executed'] = True
    result['actual_frozen_class_file_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    print(json.dumps(result, allow_nan=False))
