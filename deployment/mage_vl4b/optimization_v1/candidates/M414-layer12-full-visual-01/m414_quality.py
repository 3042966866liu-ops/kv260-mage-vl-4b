"""Finite fixed-input final visual-feature screen, not semantic accuracy."""
import hashlib
import os
import numpy as np

THRESHOLDS = dict(maximum_relative_l2=.02, minimum_cosine=.999,
                  minimum_token_cosine=.995)

def tensor(value):
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all():
        raise FloatingPointError('Nonfinite complete tensor')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())

def visual_quality(reference, candidate):
    from m407_mlp_contract import metrics
    for x in (reference, candidate):
        if x.shape != (98, 2560) or x.dtype != np.float32:
            raise ValueError('Original complete98x2560 FP32 feature contract required')
    value = metrics(reference, candidate)
    passed = (value['relative_l2'] <= THRESHOLDS['maximum_relative_l2'] and
              value['cosine'] >= THRESHOLDS['minimum_cosine'] and
              value['min_token_cosine'] >= THRESHOLDS['minimum_token_cosine'])
    return dict(metrics=value, thresholds=THRESHOLDS, feature_screen_pass=bool(passed),
                semantic_accuracy_proven=False)

def save_features(folder, values):
    rows=[]
    for name in ('original','candidate'):
        value=values[name]
        if value.shape!=(98,2560) or value.dtype!=np.float32:
            raise ValueError('Only two bounded original visual features may be saved')
        target=folder/(name+'_visual.npy');partial=target.with_suffix('.partial')
        if target.exists():raise RuntimeError('Retained features immutable')
        with partial.open('xb') as f:
            np.save(f,value,allow_pickle=False);f.flush();os.fsync(f.fileno())
        os.replace(partial,target)
        rows.append(dict(path=target.name,file_bytes=target.stat().st_size,
                         file_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tensor=tensor(value)))
    if sum(x['file_bytes'] for x in rows)>3<<20:raise RuntimeError('Bounded two feature files exceeded')
    return rows

class VisualChecks:
    """Observe all24 actual layers, restore hooks, retain no historical tensors."""
    def __init__(self, vision, budget, checkpoints, phase):
        self.layers = tuple(vision.encoder.layers)
        if len(self.layers) != 24:
            raise RuntimeError('Original24 visual layers required')
        self.budget, self.checkpoints, self.phase = budget, checkpoints, phase
        self.handles = []; self.original = []; self.restored = False
    def __enter__(self):
        try:
            for i, layer in enumerate(self.layers):
                self.original.append((layer, tuple(layer._forward_pre_hooks), tuple(layer._forward_hooks)))
                def pre(module, args, index=i):
                    self.checkpoints.append(self.budget.check(self.phase[0]+':layer'+str(index)+':before'))
                def post(module, args, value, index=i):
                    self.checkpoints.append(self.budget.check(self.phase[0]+':layer'+str(index)+':after'))
                self.handles.append(layer.register_forward_pre_hook(pre))
                self.handles.append(layer.register_forward_hook(post))
        except BaseException:
            self.__exit__(None, None, None); raise
        return self
    def __exit__(self, *unused):
        for h in reversed(self.handles): h.remove()
        self.handles.clear()
        self.restored = all(tuple(m._forward_pre_hooks)==a and tuple(m._forward_hooks)==b
                            for m,a,b in self.original)
        self.original.clear(); self.layers = ()
        if not self.restored: raise RuntimeError('Visual boundary hooks not restored')
        return False
