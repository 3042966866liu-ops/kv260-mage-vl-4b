"""Independent complete W4/A8 language MLP execution scoring.

Project adapter: uses the existing M445 record builder, board packet/parser and
M120 ordered group oracle. This is software execution of the wire contract,
not a new FPGA measurement. No allocator, Candidate or convolution probe change.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/optimization'))
import m445_prepare_csim as existing
from m355_reference import decode_records
from m120_group_reference import group_reference
from contract_runtime import pack_chain_input, parse_chain_output


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def execution_error(output, reference):
    """FP64 squared relative Frobenius error; never average per-row ratios."""
    y = np.asarray(output); ref = np.asarray(reference)
    if y.shape != ref.shape or y.ndim != 2 or not y.size:
        raise ValueError('Matching nonempty [tokens, hidden] outputs required')
    if not np.isfinite(y).all() or not np.isfinite(ref).all():
        raise ValueError('Nonfinite outputs')
    y = y.astype(np.float64); ref = ref.astype(np.float64)
    numerator = float(np.sum((y-ref)**2)); denominator = float(np.sum(ref**2))
    if denominator == 0 and numerator != 0:
        raise ValueError('Nonzero error with zero reference energy')
    error = numerator/denominator if denominator else 0.0
    return dict(exec_err=error, relative_l2=float(np.sqrt(error)),
                error_energy=numerator, reference_energy=denominator)


@contextmanager
def exact_gemm(device):
    old = torch.backends.cuda.matmul.allow_tf32
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        with torch.no_grad(), torch.autocast(device_type=device.type, enabled=False):
            yield
    finally:
        torch.backends.cuda.matmul.allow_tf32 = old


class PackedChain:
    """Freeze W4 records, decode them, and execute actual T32 input/output wire."""
    def __init__(self, modules, *, device='cpu'):
        self.device = torch.device(device)
        if self.device.type not in ('cpu', 'cuda'):
            raise ValueError('Only explicit CPU oracle or CUDA exact-integer GEMM')
        if self.device.type == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('Requested CUDA unavailable; no fallback')
        names = [name for name, _, _ in modules]
        if not modules or len(names) != len(set(names)):
            raise ValueError('Distinct nonempty module names required')
        groups = modules[0][1].shape[1]
        for name, c, s in modules:
            c = np.asarray(c); s = np.asarray(s)
            if c.ndim != 3 or c.shape[1:] != (groups, 64) or c.shape[0] % 32:
                raise ValueError('W4 [rows multiple of 32,G,64] required')
            if not c.size or c.dtype != np.int8 or c.min() < -8 or c.max() > 8:
                raise ValueError('Signed W4 codes required')
            if np.any((c.min(-1) == -8) & (c.max(-1) == 8)):
                raise ValueError('W4 group has incompatible endpoint orientation')
            if s.shape != c.shape[:2] or s.dtype != np.float16:
                raise ValueError('Matching FP16 weight scales required')
            if not np.isfinite(s).all() or np.any(s <= 0):
                raise ValueError('Positive finite FP16 weight scales required')
        self.chain, self.windows = existing.make_chain(modules, groups)
        if len(self.chain['descriptors']) > 10 or groups > 152:
            raise ValueError('Original descriptor/group hardware bound exceeded')
        self.widths = {name: int(c.shape[0]) for name, c, _ in modules}
        self.decoded = []
        for descriptor in self.chain['descriptors']:
            rows = descriptor['rows_per_shard']; start = descriptor['offset_words']*16
            size = groups*(rows//8)*272
            shards = [decode_records(w[start:start+size], groups, rows, 4) for w in self.windows]
            c = np.concatenate([a for a, _ in shards], axis=1)
            s = np.concatenate([a for _, a in shards], axis=1)
            # Repacking must preserve both integer codes and scale bits.
            name = descriptor['module']; source = next(m for m in modules if m[0] == name)
            sl = slice(descriptor['row_start'], descriptor['row_start']+4*rows)
            if not np.array_equal(c.transpose(1,0,2), source[1][sl]):
                raise ValueError('W4 record round trip changed integer codes')
            if not np.array_equal(s.T.view(np.uint16), source[2][sl].view(np.uint16)):
                raise ValueError('W4 record round trip changed scale bits')
            if self.device.type == 'cuda':
                c = torch.from_numpy(c.copy()).to(self.device, dtype=torch.float32)
                s = torch.from_numpy(s.copy()).to(self.device)
            self.decoded.append((c, s))
        self.binding = dict(groups=groups, descriptors=len(self.decoded),
                            widths=self.widths, window_sha256=[digest(w) for w in self.windows],
                            weight_wire_bytes=sum(map(len, self.windows)))

    def run_t32(self, values):
        x = np.asarray(values)
        if x.dtype != np.float32 or x.ndim != 2 or not 0 < len(x) <= 32 or x.shape[1] != self.chain['groups']*64:
            raise ValueError('Finite FP32 [1..32,G*64] input required')
        if not np.isfinite(x).all():
            raise ValueError('Nonfinite input')
        # Reject underflow before the legacy quantizer could divide by zero.
        maximum = np.abs(x.reshape(len(x), -1, 64)).max(-1)
        scale = (maximum/np.float32(127)).astype(np.float16)
        if np.any((maximum != 0) & (scale == 0)) or not np.isfinite(scale).all():
            raise ValueError('A8 scale not representable in FP16')
        packet = pack_chain_input(self.chain, x)
        count = len(self.decoded); groups = self.chain['groups']
        records = np.frombuffer(packet[count*16:], np.uint8).reshape(groups,32,80)
        a = records[:,:,:64].copy().view(np.int8).transpose(1,0,2)
        sa = records[:,:,64:66].copy().view('<f2').reshape(groups,32).T.copy()
        if self.device.type == 'cuda':
            aa = torch.from_numpy(a.copy()).to(self.device, dtype=torch.float32)
            scales = torch.from_numpy(sa.copy()).to(self.device)
        wires = []
        with exact_gemm(self.device):
            for descriptor, (c, s) in zip(self.chain['descriptors'], self.decoded):
                if self.device.type == 'cpu':
                    half = group_reference(a, sa, c, s, dot_mode='fp32_exact')
                else:
                    # Each integer dot <=64*127*8, exact in FP32. Two separate
                    # multiplications, ordered addition; never fuse/reassociate.
                    dots = torch.bmm(aa.permute(1,0,2).contiguous(), c.transpose(1,2).contiguous())
                    z = torch.zeros((32,c.shape[1]), device=self.device, dtype=torch.float32)
                    for i in range(groups):
                        term = dots[i]*scales[:,i:i+1].float()
                        term = term*s[i].float().unsqueeze(0)
                        z = z+term
                    half = z.half().cpu().numpy()
                if not np.isfinite(half).all():
                    raise ValueError('Output overflow; no clipping or retry')
                bits = half.view('<u2').copy()
                subnormal = ((bits & 0x7c00) == 0) & ((bits & 0x03ff) != 0)
                bits[subnormal] &= np.uint16(0x8000)  # M157 signed FTZ
                blocks = descriptor['rows_per_shard']//8
                data = bits.reshape(32,4,blocks,4,2).transpose(2,0,1,3,4)
                wire = np.zeros((blocks,32,4,4,4), '<u2')
                wire[...,0] = data[...,0]; wire[...,2] = data[...,1]
                wires.append(wire.tobytes())
        wire = b''.join(wires)
        parsed = parse_chain_output(self.chain, wire)
        if set(parsed) != set(self.widths) or any(parsed[n].shape != (32,w) or not np.isfinite(parsed[n]).all() for n,w in self.widths.items()):
            raise ValueError('Incomplete parsed output')
        trace = dict(input_sha256=digest(x.tobytes()), packet_sha256=digest(packet),
                     output_wire_sha256=digest(wire), input_bytes=len(packet),
                     output_bytes=len(wire), valid_tokens=len(x), padded_tokens=32-len(x),
                     activation_dtype='int8', activation_scale_dtype='float16',
                     accumulator_dtype='float32', wire_output_dtype='float16_signed_FTZ',
                     parsed_dtype='float32', widths=self.widths)
        return {k:v[:len(x)].copy() for k,v in parsed.items()}, trace, wire


class LanguageMLPCandidate:
    """Three original W4 linears, or six already-quantized SVD factor linears.

    weights is [(signed_codes[O,I/64,64], fp16_scales[O,I/64]), ...].
    SVD order: gate_right,left; up_right,left; down_right,left. Factors must be
    quantized separately before construction; reconstruction is never executed.
    """
    def __init__(self, name, weights, *, factorized=False, hidden=2560, device='cpu'):
        self.name = name; self.hidden = hidden; self.factorized = factorized
        if hidden <= 0 or hidden % 64 or len(weights) != (6 if factorized else 3):
            raise ValueError('MLP geometry/number of stages differs')
        dims = [(c.shape[0],c.shape[1]*64) for c,s in weights]
        if factorized:
            (r,h),(d,r2),(ru,hu),(du,ru2),(rd,dd),(ho,rd2) = dims
            if h != hidden or hu != hidden or ho != hidden or d != du or dd != d or r != r2 or ru != ru2 or rd != rd2:
                raise ValueError('Broken SVD MLP connections')
            specs = [[('gate_rank',*weights[0]),('up_rank',*weights[2])],
                     [('gate',*weights[1])], [('up',*weights[3])],
                     [('down_rank',*weights[4])], [('down',*weights[5])]]
            if r != ru:
                raise ValueError('Shared Gate/Up right chain needs matching rank')
        else:
            (d,h),(du,hu),(ho,dd) = dims
            if (h,hu,ho) != (hidden,hidden,hidden) or d != du or d != dd:
                raise ValueError('Broken Gate/Up/Down MLP connections')
            specs = [[('gate',*weights[0]),('up',*weights[1])], [('down',*weights[2])]]
        self.width = d
        self.chains = [PackedChain(spec, device=device) for spec in specs]
        self.binding = dict(name=name, hidden=hidden, width=d, factorized=factorized,
                            linear_stages=len(weights), chains_per_t32=len(self.chains),
                            chains=[c.binding for c in self.chains])

    def execute(self, inputs):
        x = np.asarray(inputs)
        if x.dtype != np.float32 or x.ndim != 2 or len(x) == 0 or x.shape[1] != self.hidden or not np.isfinite(x).all():
            raise ValueError('Complete finite FP32 MLP input required')
        outputs = []; trace = []
        for start in range(0,len(x),32):
            traces = []
            def run(index, values):
                result, record, _ = self.chains[index].run_t32(values)
                traces.append(dict(chain=index, **record)); return result
            first = run(0, x[start:start+32])
            if self.factorized:
                g = run(1, first['gate_rank'])['gate']
                u = run(2, first['up_rank'])['up']
            else:
                g = first['gate']; u = first['up']
            # Exactly the original board PS expression, not Torch fused SiLU.
            with np.errstate(over='ignore'):
                act = (g/(np.float32(1)+np.exp(-g,dtype=np.float32)))*u
            if not np.isfinite(act).all():
                raise ValueError('Nonfinite FP32 SiLU times Up')
            if self.factorized:
                rank = run(3, act)['down_rank']; y = run(4,rank)['down']
            else:
                y = run(1, act)['down']
            if y.shape != (len(g),self.hidden):
                raise ValueError('Final hidden-dimensional interface differs')
            outputs.append(y)
            trace.append(dict(row_start=start, chains=traces, silu_dtype='float32',
                              silu_up_sha256=digest(act.tobytes())))
        return np.concatenate(outputs), trace


class LanguageMLPExecutionProbe:
    """Explicit diagnostic API. No automatic search or Pareto integration."""
    def __init__(self, original, inputs):
        if original.factorized:
            raise ValueError('Reference must be the original uncompressed MLP')
        self.original = original
        self.inputs = [np.array(x,copy=True) for x in inputs]
        if not self.inputs:
            raise ValueError('Empty input batch')
        self.references = []; self.reference_traces = []
        for x in self.inputs:
            y, trace = original.execute(x)
            y.setflags(write=False); x.setflags(write=False)
            self.references.append(y); self.reference_traces.append(trace)

    def score_exec(self, candidate):
        if candidate.hidden != self.original.hidden:
            raise ValueError('Candidate final interface differs')
        outputs = []; traces = []
        for x in self.inputs:
            y, trace = candidate.execute(x); outputs.append(y); traces.append(trace)
        return dict(candidate=candidate.binding,
                    metrics=execution_error(np.concatenate(outputs),np.concatenate(self.references)),
                    per_input=[execution_error(y,r) for y,r in zip(outputs,self.references)],
                    outputs=outputs, traces=traces)
