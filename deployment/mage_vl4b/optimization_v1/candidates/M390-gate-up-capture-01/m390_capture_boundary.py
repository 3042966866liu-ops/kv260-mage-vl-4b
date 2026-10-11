"""Bounded capture after the original synchronous layer0 gate_up family."""
import os
from pathlib import Path
import threading
import numpy as np
from m368_video_contract import tensor
from measurement import sha256


class CaptureBoundary(BaseException):
    """Expected control boundary, deliberately not swallowed by Exception."""


class GateUpCapture:
    def __init__(self, original, expected, policy, destination):
        self.original = original
        self.expected = expected[:4]
        if [(r['layer'], r['family']) for r in self.expected] != [
                (0, 'q'), (0, 'kv'), (0, 'attention_out'), (0, 'gate_up')]:
            raise RuntimeError('Original layer0 reference prefix differs')
        self.policy = policy
        self.destination = Path(destination)
        self.families = []
        self.fixtures = {}
        self.done = False
        self.attempted_after_boundary = []

    def __call__(self, layer, name, values):
        i = len(self.families)
        if self.done or i >= 4 or (layer, name) != (0, self.expected[i]['family']):
            self.attempted_after_boundary.append((layer, name))
            raise RuntimeError('No later family/head admitted')
        self.policy.capture('before-capture-family:'+name, True)
        output = self.original(layer, name, values)
        self.policy.capture('after-capture-family:'+name, True)
        row = dict(layer=layer, family=name, input=tensor(values),
                   output={k:tensor(v) for k,v in sorted(output.items())})
        if row != self.expected[i]:
            raise RuntimeError('Frozen layer0 full output hash differs: '+name)
        self.families.append(row)
        if name != 'gate_up':
            return output
        # No borrowed DMA buffers or pending parse/pack tasks may survive the
        # frozen synchronous family return before fixture serialization.
        if not self.policy.safe() or any(t.name.startswith(('m238-parse', 'm238-pack'))
                                         for t in threading.enumerate()):
            raise RuntimeError('Capture boundary completion/worker drain unproven')
        for short in ('gate', 'up'):
            value = output['model.language_model.layers.0.mlp.'+short+'_proj']
            if value.shape != (159,9728) or value.dtype != np.float32 or not value.flags.c_contiguous:
                raise RuntimeError('Actual gate/up geometry/layout differs')
            path = self.destination / (short+'.npy')
            if path.exists() or path.with_suffix('.npy.part').exists():
                raise RuntimeError('Immutable fixture exists')
            temp = path.with_suffix('.npy.part')
            with temp.open('xb') as handle:
                np.save(handle, value, allow_pickle=False)
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temp,path)
            self.fixtures[short] = dict(path=str(path), file_sha256=sha256(path),
                                        file_bytes=path.stat().st_size, tensor=tensor(value))
            self.policy.capture('after-actual-fixture-save:'+short, True)
        self.done = True
        raise CaptureBoundary()
