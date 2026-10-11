"""Unstaged late11 PL scope; requires externally verified saved wire references.

No resource allocation or Overlay control. Reuse actual unchanged PLMLPBinding
and RangeScope cleanup. The resource owner remains responsible for DMA safety.
"""
import hashlib
from m426_range02 import RangeScope
from m411_mlp_binding import PLMLPBinding

SELECTED = tuple(range(13, 24))


class SavedWireCheck:
    def __init__(self, references, submit):
        if set(references) != set(map(str, SELECTED)):
            raise ValueError('All eleven accepted layers required')
        self.references = references
        self.submit = submit
        self.seen = []
        sequence = []
        for index in SELECTED:
            parts = references[str(index)]
            if set(parts) != {'fc1', 'fc2'}:
                raise ValueError('Both saved MLP Linear references required')
            for part in ('fc1', 'fc2'):
                rows = parts[part]
                if len(rows) != 13:
                    raise ValueError('Full thirteen original T32 batches required')
                for n, row in enumerate(rows):
                    if (row['start'] != 32*n or row['rows'] != (32 if n < 12 else 8)
                            or row['attempted_shifts'] != [row['selected_shift']]
                            or row['initial_shift'] != row['selected_shift']
                            or row['physical_reference_attempts'] != 1):
                        raise ValueError('One-attempt saved reference required; no retry guessing')
                    if (type(row['selected_shift']) is not int or not 0 <= row['selected_shift'] <= 6
                            or any(type(row[k]) is not int or row[k] <= 0 for k in ('input_bytes', 'output_bytes'))
                            or any(type(row[k]) is not str or len(row[k]) != 64 or
                                   any(c not in '0123456789abcdef' for c in row[k])
                                   for k in ('packet_sha256', 'raw_sha256'))):
                        raise ValueError('Strict saved shift, geometry and SHA required')
                    sequence.append((index, part, 32*n, row['selected_shift']))
        self.expected_position = tuple(sequence)

    def __call__(self, index, part, chain, start, shift, packet):
        if index not in SELECTED or part not in ('fc1', 'fc2') or start % 32 or not 0 <= start < 392:
            raise ValueError('Frozen PL batch identity required')
        position = (index, part, start, shift)
        expected_position = self.expected_position
        if len(self.seen) >= len(expected_position) or position != expected_position[len(self.seen)]:
            raise ValueError('Exact saved PL batch sequence required')
        ref = self.references[str(index)][part][start//32]
        if len(packet) != ref['input_bytes'] or hashlib.sha256(packet).hexdigest() != ref['packet_sha256']:
            raise ValueError('Complete saved packet differs; no DMA submit')
        if chain['output_bytes'] != ref['output_bytes']:
            raise ValueError('Saved complete output geometry differs')
        raw = self.submit(index, part, chain, start, shift, packet)
        if len(raw) != ref['output_bytes'] or hashlib.sha256(raw).hexdigest() != ref['raw_sha256']:
            raise ValueError('Complete saved output wire differs')
        self.seen.append(position)
        return raw

    def require_complete(self):
        if len(self.seen) != 286:
            raise ValueError('Complete286 matched PL wire batches required')


class PLRangeScope(RangeScope):
    def __init__(self, torch, layers, targets, load_case, initial, host,
                 boundary_sink, checkpoint, stage, wire_check):
        super().__init__(torch, layers, targets, SELECTED, 'software', load_case,
                         initial, host, boundary_sink, checkpoint)
        self.stage = stage
        self.wire_check = wire_check

    def before(self, index):
        if self.active is not None or index != len(self.seen):
            raise RuntimeError('Layer order or active scope differs')
        self.checkpoint('layer'+str(index)+':before')
        if index in self.selected:
            case = self.load_case(index)
            binding = PLMLPBinding(self.torch, self.targets[index].mlp, case['chains'],
                self.initial, self.host,
                lambda part, chain: self.stage(index, part, chain),
                lambda part, chain, start, shift, packet:
                    self.wire_check(index, part, chain, start, shift, packet), expected=None)
            self.active = (index, binding)
            binding.__enter__()
            self.peak_live_layer_scopes = 1
