"""Bounded module-local capture and A8-only rejection screen. No PL emulation."""
from contextlib import AbstractContextManager
import hashlib
import numpy as np
from m407_mlp_contract import metrics, local_screen


SHAPES = {'residual': (392, 1024), 'input': (392, 1024),
          'fc1': (392, 4096), 'gelu': (392, 4096), 'fc2': (392, 1024),
          'output': (392, 1024)}


def array(value):
    x = value.detach().cpu().numpy()
    if x.dtype != np.float32 or x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError('Original finite FP32 matrix required')
    return np.ascontiguousarray(x).copy()


class Capture(AbstractContextManager):
    """Instance hooks only; never replace a class method or save historical tensors."""
    def __init__(self, mlp, norm=None, shapes=None, qdq=None):
        self.mlp, self.norm, self.qdq = mlp, norm, qdq
        self.shapes = shapes or SHAPES
        self.values, self.counts, self.handles = {}, {}, []
        self.hook_keys = []
        self.restored = False

    def save(self, key, value):
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] != 1:
            raise RuntimeError('Duplicate target call; bounded capture refused')
        x = array(value)
        if tuple(x.shape) != self.shapes[key]:
            raise ValueError('Target matrix shape differs: ' + key)
        self.values[key] = x

    def pre(self, key):
        def hook(module, args):
            if len(args) != 1: raise ValueError('Unexpected target arguments')
            self.save(key, args[0])
            if self.qdq is not None and key in ('input', 'gelu'):
                return (self.qdq(key, args[0]),)
        return hook

    def post(self, key):
        def hook(module, args, result): self.save(key, result)
        return hook

    def add(self, module, pre, hook):
        table = module._forward_pre_hooks if pre else module._forward_hooks
        original = tuple(table.keys())
        handle = module.register_forward_pre_hook(hook) if pre else module.register_forward_hook(hook)
        self.handles.append(handle)
        self.hook_keys.append((module, pre, original))

    def __enter__(self):
        try:
            if self.norm is not None: self.add(self.norm, True, self.pre('residual'))
            self.add(self.mlp.fc1, True, self.pre('input'))
            self.add(self.mlp.fc1, False, self.post('fc1'))
            self.add(self.mlp.fc2, True, self.pre('gelu'))
            self.add(self.mlp.fc2, False, self.post('fc2'))
            self.add(self.mlp, False, self.post('output'))
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *unused):
        for handle in reversed(self.handles): handle.remove()
        self.handles.clear()
        self.restored = all(tuple((m._forward_pre_hooks if pre else m._forward_hooks).keys()) == before
                            for m, pre, before in self.hook_keys)
        self.hook_keys.clear()
        if not self.restored: raise RuntimeError('Target hook bindings not restored')
        return False

    def require_complete(self):
        keys = set(self.shapes) - ({'residual'} if self.norm is None else set())
        if set(self.values) != keys or any(x != 1 for x in self.counts.values()):
            raise RuntimeError('Target capture incomplete')
        if not np.array_equal(self.values['output'].view(np.uint32), self.values['fc2'].view(np.uint32)):
            raise RuntimeError('MLP has an unexpected consumer after fc2')
        if sum(x.nbytes for x in self.values.values()) > (32 << 20):
            raise RuntimeError('Capture memory budget exceeded')


def qdq_matrix(x, quantize):
    """Original G64 scale-first FP16 quantizer in original T32 batches, shift=0."""
    x = np.asarray(x)
    if x.dtype != np.float32 or x.ndim != 2 or not 0 < x.shape[0] <= 392 or x.shape[1] % 64 or not np.isfinite(x).all():
        raise ValueError('Finite bounded FP32 G64 matrix required')
    result = np.empty_like(x)
    batches = []
    for start in range(0, len(x), 32):
        source = x[start:start+32]
        groups = source.shape[1] // 64
        maximum = np.max(np.abs(source.reshape(len(source), groups, 64)), axis=2)
        with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
            safe = np.where(maximum == 0, np.float16(1), (maximum / np.float32(127)).astype('<f2'))
            if not np.isfinite(safe).all() or np.any(safe <= 0):
                raise FloatingPointError('A8 FP16 scale nonfinite or underflow; no clipping repair')
            rounded = np.rint(source.reshape(len(source), groups, 64) / safe.astype(np.float32)[..., None])
            if np.any(np.abs(rounded) > 127): raise FloatingPointError('A8 unexpected clipping')
            records, codes, scales = quantize(source, groups, 0)
            if not np.array_equal(codes[:len(source)], rounded.astype(np.int8)):
                raise RuntimeError('Original quantizer code contract differs')
            if not np.array_equal(scales[:len(source)].view(np.uint16), safe.view(np.uint16)):
                raise RuntimeError('Original FP16 scale contract differs')
            if np.any(codes[len(source):]) or np.any(records[:, :, 66:]):
                raise RuntimeError('Original padding/reserved fields differ')
            result[start:start+len(source)] = (codes[:len(source)].astype(np.float32) *
                                             scales[:len(source)].astype(np.float32)[..., None]).reshape(source.shape)
        batches.append(dict(start=start, rows=len(source), groups=groups, shift=0, clipped=0,
            codes_sha256=hashlib.sha256(codes.tobytes()).hexdigest(),
            scales_sha256=hashlib.sha256(scales.tobytes()).hexdigest()))
    return result, batches


def compare(reference, candidate):
    report = {key: metrics(reference[key], candidate[key]) for key in ('fc1', 'gelu', 'fc2', 'output')}
    if 'residual' in reference:
        report['residual_sum'] = metrics(reference['residual'] + reference['output'],
                                         reference['residual'] + candidate['output'])
    return report, all(local_screen(value) for value in report.values())
