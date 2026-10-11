"""Default-off, CPU-only cumulative visual MLP oracle; one live layer scope.

Reuse M409 arithmetic unchanged. No PL/DMA imports, tensor history or wire
payload history. The original Attention/GELU/norm/boundaries still execute.
"""
import hashlib
import numpy as np
from m409_ftz_reference import SoftwareMLPBinding

SELECTED = tuple(range(2, 24))


def prefix_evidence(vision, progress_cls, boundary_cls, linear_cls, torch):
    rows = {}
    for index in (0, 1):
        outer = vision.encoder.layers[index]
        if type(outer) is not progress_cls or outer.index != index:
            raise RuntimeError('Original BF16 progress identity differs')
        inner = outer.layer
        if type(inner) is boundary_cls or type(inner).__name__ != 'MageVLVisionEncoderLayer':
            raise RuntimeError('Original BF16 prefix must have no conversion wrapper')
        for name in ('layer_norm1', 'layer_norm2'):
            if getattr(inner, name).weight.dtype != torch.bfloat16:
                raise RuntimeError('Original BF16 prefix norm precision differs')
        for part, shape in (('fc1', (1024, 4096)), ('fc2', (4096, 1024))):
            mod = getattr(inner.mlp, part)
            if type(mod) is not linear_cls or mod.name != f'encoder.layers.{index}.mlp.{part}' or (mod.in_features, mod.out_features) != shape or mod.output_dtype != torch.bfloat16 or mod.bias is None or mod.bias.dtype != torch.bfloat16:
                raise RuntimeError('Original BF16 prefix Linear identity/precision differs')
        rows[str(index)] = dict(progress=type(outer).__name__, encoder=type(inner).__name__,
            conversion_wrapper=False, target_dtype='torch.bfloat16', output_dtype='torch.bfloat16')
    return rows


def resolve(vision, progress_cls, boundary_cls, linear_cls, torch):
    if len(vision.encoder.layers) != 24:
        raise RuntimeError('Frozen 24-layer topology required')
    prefix_evidence(vision, progress_cls, boundary_cls, linear_cls, torch)
    targets = {}; evidence = {}
    for index, outer in enumerate(vision.encoder.layers):
        if type(outer) is not progress_cls or outer.index != index:
            raise RuntimeError('Progress index/type differs')
        if index < 2:
            continue
        boundary = outer.layer
        wanted = torch.float32
        if type(boundary) is not boundary_cls or boundary.target_dtype != wanted or boundary.output_dtype != torch.bfloat16:
            raise RuntimeError('Frozen two-layer BF16 prefix/boundary differs')
        inner = boundary.layer
        if type(inner).__name__ != 'MageVLVisionEncoderLayer':
            raise RuntimeError('Actual encoder type differs')
        if index not in SELECTED:
            continue
        matrices = {}
        for part, shape in (('fc1', (1024, 4096)), ('fc2', (4096, 1024))):
            mod = getattr(inner.mlp, part)
            if type(mod) is not linear_cls or mod.name != f'encoder.layers.{index}.mlp.{part}' or (mod.in_features, mod.out_features) != shape:
                raise RuntimeError('Actual Linear identity/geometry differs')
            if mod.output_dtype != torch.float32 or mod.bias is None or mod.bias.dtype != torch.float32 or tuple(mod.bias.shape) != (shape[1],):
                raise RuntimeError('FP32 PS bias/precision differs')
            if mod.store.entries[mod.name]['module'] != 'model.visual.' + mod.name:
                raise RuntimeError('CPU-store/PL-layout name binding differs')
            matrices[part] = dict(name=mod.name, shape=list(shape), bias_sha256=hashlib.sha256(mod.bias.detach().numpy().tobytes()).hexdigest())
        targets[index] = inner
        evidence[str(index)] = dict(target_dtype=str(wanted), output_dtype=str(boundary.output_dtype), matrices=matrices)
    return targets, evidence


class RangeScope:
    """Bind just the entering layer; release its windows at its post hook.

    Hooks inspect complete original BF16 boundary outputs, converted to FP32
    only for diagnostics. Exceptions restore the active scope and every hook.
    """
    def __init__(self, torch, layers, targets, selected, mode, load_case,
                 initial, host, boundary_sink, checkpoint):
        selected = tuple(selected)
        if not selected or tuple(sorted(set(selected))) != selected or not set(selected) <= set(SELECTED):
            raise ValueError('Unique ascending frozen FP32 indices required')
        if mode not in ('original', 'software') or len(layers) != 24 or not set(selected) <= set(targets):
            raise ValueError('CPU-only original/software complete topology required')
        self.torch, self.layers, self.targets = torch, tuple(layers), targets
        self.selected, self.mode, self.load_case = selected, mode, load_case
        self.initial, self.host = initial, host
        self.sink, self.checkpoint = boundary_sink, checkpoint
        self.handles = []; self.hooks = []; self.active = None
        self.batches = {}; self.seen = []; self.restored = False
        self.peak_live_layer_scopes = 0; self.complete = False

    def before(self, index):
        if self.active is not None or index != len(self.seen):
            raise RuntimeError('Layer order or active scope differs')
        self.checkpoint('layer' + str(index) + ':before')
        if self.mode == 'software' and index in self.selected:
            case = self.load_case(index)
            binding = SoftwareMLPBinding(self.torch, self.targets[index].mlp,
                case['chains'], case['windows'], self.initial,
                self.host.pack_chain_input, self.host.parse_chain_output,
                raw_sink=lambda part, start, shift, packet, raw:
                    self.checkpoint('layer'+str(index)+':'+part+':batch'+str(start)))
            self.active = (index, binding)
            binding.__enter__()
            self.peak_live_layer_scopes = 1

    def release(self):
        if self.active is None:
            return
        index, binding = self.active
        binding.__exit__(None, None, None)
        self.active = None
        if not binding.restored:
            raise RuntimeError('Instance forwards not restored')
        self.batches[str(index)] = binding.batches

    def after(self, index, value):
        if index != len(self.seen):
            raise RuntimeError('Boundary order differs')
        if self.active is not None:
            active_index, binding = self.active
            if active_index != index or binding.calls != {'fc1': 1, 'fc2': 1}:
                raise RuntimeError('Exactly two selected Linear calls required')
            if any([r['rows'] for r in binding.batches.get(k, [])] != [32]*12 + [8] for k in ('fc1', 'fc2')):
                raise RuntimeError('Original392-row T32 partition differs')
            self.release()
        output = value[0] if isinstance(value, tuple) else value
        if tuple(output.shape) != (1, 392, 1024) or output.dtype != self.torch.bfloat16:
            raise RuntimeError('Original complete BF16 boundary shape differs')
        arr = output.detach().float().cpu().numpy()[0]
        if arr.dtype != np.float32 or not np.isfinite(arr).all():
            raise RuntimeError('Finite boundary required')
        self.sink(index, arr)
        self.seen.append(index)
        self.checkpoint('layer' + str(index) + ':after')

    def __enter__(self):
        try:
            for i, layer in enumerate(self.layers):
                self.hooks.append((layer, tuple(layer._forward_pre_hooks), tuple(layer._forward_hooks)))
                self.handles.append(layer.register_forward_pre_hook(lambda m, a, i=i: self.before(i)))
                self.handles.append(layer.register_forward_hook(lambda m, a, v, i=i: self.after(i, v)))
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *unused):
        try:
            self.release()
        finally:
            for handle in reversed(self.handles): handle.remove()
            self.handles.clear()
            self.restored = all(tuple(m._forward_pre_hooks) == a and tuple(m._forward_hooks) == b for m, a, b in self.hooks)
            self.hooks.clear(); self.layers = (); self.targets = None
        if not self.restored:
            raise RuntimeError('Boundary hooks not restored')
        self.complete = self.seen == list(range(24)) and (self.mode == 'original' or set(self.batches) == set(map(str, self.selected)))
        return False
