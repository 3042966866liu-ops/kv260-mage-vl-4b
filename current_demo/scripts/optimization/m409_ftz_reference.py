"""PS software oracle adapter; exact retained T32/ordered-FP32/FP16/FTZ math.

Never executes hardware. The caller supplies frozen weight windows and the
actual original host pack/parser/initial-shift functions. Quality is a separate
comparison against original CPU FP32 outputs, not asserted by this adapter.
"""
import hashlib
import numpy as np
from m355_reference import full_reference


def linear_reference(chain, values, windows, initial_shift, pack, parse, *, raw_sink=None):
    x = np.asarray(values)
    if x.dtype != np.float32 or x.ndim != 2 or not 0 < len(x) <= 392 or x.shape[1] != chain['groups']*64 or not np.isfinite(x).all():
        raise ValueError('Actual bounded complete FP32 input required')
    if len(windows) != 4 or any(len(w) != chain['stage_bytes_per_shard'] for w in windows):
        raise ValueError('Exact four contiguous W4 staging windows required')
    width = max(d['row_start']+d['valid_rows'] for d in chain['descriptors'])
    answer = np.full((len(x),width),np.nan,np.float32)
    batches = []
    base = chain['stage_base_words']
    for start in range(0,len(x),32):
        block = x[start:start+32]
        first = initial_shift(block)
        if type(first) is not int or not 0 <= first <= 6: raise RuntimeError('Original shift range differs')
        attempts = []
        for shift in range(first,-1,-1):
            packet = pack(chain,block,base,activation_scale_shift=shift)
            attempts.append(shift)
            try:
                raw = full_reference(chain,windows,base,packet)
            except ValueError as error:
                if str(error) != 'Diagnostic reference would need retry': raise
                continue
            outputs = parse(chain,raw,output_scale_shift=shift)
            result = outputs[chain['module']]
            if result.shape != (32,width) or not np.isfinite(result).all():
                raise RuntimeError('Oracle output geometry/finite differs')
            if raw_sink is not None: raw_sink(start,shift,packet,raw)
            answer[start:start+len(block)] = result[:len(block)]
            batches.append(dict(start=start,rows=len(block),initial_shift=first,attempted_shifts=attempts,
                selected_shift=shift,input_max_abs=float(np.max(np.abs(block))),
                packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),
                input_bytes=len(packet),output_bytes=len(raw),logical_calls=1,physical_reference_attempts=len(attempts)))
            break
        else: raise FloatingPointError('Original adaptive finite-retry exhausted; no clipping/fallback')
    if not np.isfinite(answer).all(): raise RuntimeError('Incomplete output')
    return answer,batches


class SoftwareMLPBinding:
    """Override only two instance forwards; preserve the actual MLP/GELU function."""
    def __init__(self, torch, mlp, chains, windows, initial_shift, pack, parse, raw_sink=None):
        self.torch,self.mlp = torch,mlp
        self.chains,self.windows = chains,windows
        self.initial_shift,self.pack,self.parse,self.raw_sink = initial_shift,pack,parse,raw_sink
        self.previous = []; self.calls = {}; self.batches = {}; self.restored = False

    def bind(self, part):
        module = getattr(self.mlp,part)
        if module.output_dtype != self.torch.float32 or module.bias is None:
            raise RuntimeError('Original FP32 state and PS bias required')
        owned = 'forward' in module.__dict__; original = module.__dict__.get('forward')
        self.previous.append((module,owned,original))
        def forward(values):
            self.calls[part] = self.calls.get(part,0)+1
            if self.calls[part] != 1: raise RuntimeError('Only one isolated MLP segment permitted')
            arr = values.detach().cpu().numpy()
            native_batch = arr.ndim == 3 and arr.shape[0] == 1
            if native_batch: arr = arr[0]
            elif arr.ndim != 2:
                raise ValueError('Only original matrix or native single-batch matrix permitted')
            sink = None if self.raw_sink is None else lambda *args:self.raw_sink(part,*args)
            output, rows = linear_reference(self.chains[part],arr,self.windows[part],self.initial_shift,
                                            self.pack,self.parse,raw_sink=sink)
            self.batches[part] = rows
            # Existing PL does not implement bias. Keep the original FP32 PS bias
            # add as an explicit part of the candidate, before the original GELU.
            result = self.torch.from_numpy(output) + module.bias.to(self.torch.float32)
            return result.unsqueeze(0) if native_batch else result
        module.forward = forward

    def __enter__(self):
        try:
            self.bind('fc1'); self.bind('fc2')
        except BaseException:
            self.__exit__(None,None,None); raise
        return self

    def __exit__(self,*args):
        for module,owned,original in reversed(self.previous):
            if owned: module.forward = original
            else: del module.__dict__['forward']
        self.restored = all(('forward' in m.__dict__) == owned and
                            (not owned or m.__dict__['forward'] is original) for m,owned,original in self.previous)
        self.previous.clear()
        if not self.restored: raise RuntimeError('Original instance forwards not restored')
        return False
