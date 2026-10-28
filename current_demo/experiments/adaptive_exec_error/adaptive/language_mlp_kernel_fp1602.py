"""Version 2: M462 vendor half boundary, preserving the historical v1 oracle.

Finite float32 outputs below magnitude bits 0x387ff000 flush to signed zero.
At/above that boundary, ordinary RNE half conversion applies. This slightly
differs from IEEE half rounding followed by subnormal flushing, and from
flushing all unrounded values below 2**-14. See M481 vendor-grid evidence.
No factor, quantizer, accumulation, packet or hardware change is made.
"""
import copy
import numpy as np
import torch
from .language_mlp_probe import PackedChain,exact_gemm,digest
from contract_runtime import pack_chain_input,parse_chain_output

CONTRACT='m462-fp32-to-half-vendor-boundary-02'
MIN_ROUND_UP_BITS=np.uint32(0x387ff000)

def kernel_half_bits(value):
    x=np.asarray(value)
    if x.dtype!=np.float32 or not np.isfinite(x).all():
        raise ValueError('Finite FP32 accumulator required')
    raw=np.ascontiguousarray(x).view(np.uint32)
    with np.errstate(over='ignore'):bits=x.astype('<f2').view('<u2').copy()
    tiny=(raw&np.uint32(0x7fffffff))<MIN_ROUND_UP_BITS
    bits[tiny]=((raw[tiny]>>16)&np.uint32(0x8000)).astype(np.uint16)
    if np.any((bits&0x7c00)==0x7c00):raise ValueError('Output overflow; no clipping or retry')
    return bits

class KernelPackedChain(PackedChain):
    @classmethod
    def from_legacy(cls,chain):
        if type(chain) is not PackedChain:raise ValueError('Unmodified v1 PackedChain required')
        obj=cls.__new__(cls);obj.__dict__=chain.__dict__.copy()
        obj.binding=copy.deepcopy(chain.binding);obj.binding['output_conversion_contract']=CONTRACT
        return obj

    def run_t32(self,values):
        x=np.asarray(values)
        if x.dtype!=np.float32 or x.ndim!=2 or not 0<len(x)<=32 or x.shape[1]!=self.chain['groups']*64 or not np.isfinite(x).all():
            raise ValueError('Finite FP32 [1..32,G*64] required')
        maximum=np.abs(x.reshape(len(x),-1,64)).max(-1)
        scale=(maximum/np.float32(127)).astype(np.float16)
        if np.any((maximum!=0)&(scale==0)) or not np.isfinite(scale).all():raise ValueError('A8 scale unrepresentable')
        packet=pack_chain_input(self.chain,x);count=len(self.decoded);groups=self.chain['groups']
        records=np.frombuffer(packet[count*16:],np.uint8).reshape(groups,32,80)
        a=records[:,:,:64].copy().view(np.int8).transpose(1,0,2)
        sa=records[:,:,64:66].copy().view('<f2').reshape(groups,32).T.copy()
        if self.device.type=='cuda':
            aa=torch.from_numpy(a.copy()).to(self.device,dtype=torch.float32)
            scales=torch.from_numpy(sa.copy()).to(self.device)
        wires=[]
        with exact_gemm(self.device):
            for descriptor,(c,s) in zip(self.chain['descriptors'],self.decoded):
                if self.device.type=='cuda':
                    dots=torch.bmm(aa.permute(1,0,2).contiguous(),c.transpose(1,2).contiguous())
                    z=torch.zeros((32,c.shape[1]),device=self.device,dtype=torch.float32)
                    for i in range(groups):
                        term=dots[i]*scales[:,i:i+1].float();term=term*s[i].float().unsqueeze(0);z=z+term
                    accum=z.cpu().numpy()
                else:
                    accum=np.zeros((32,c.shape[1]),np.float32)
                    for i in range(groups):
                        dots=a[:,i,:].astype(np.int32)@c[i].astype(np.int32).T
                        term=dots.astype(np.float32)*sa[:,i,None].astype(np.float32)
                        term=term*s[i,None,:].astype(np.float32);accum=accum+term
                bits=kernel_half_bits(accum);blocks=descriptor['rows_per_shard']//8
                data=bits.reshape(32,4,blocks,4,2).transpose(2,0,1,3,4)
                wire=np.zeros((blocks,32,4,4,4),'<u2');wire[...,0]=data[...,0];wire[...,2]=data[...,1];wires.append(wire.tobytes())
        wire=b''.join(wires);parsed=parse_chain_output(self.chain,wire)
        if set(parsed)!=set(self.widths) or any(parsed[n].shape!=(32,w) or not np.isfinite(parsed[n]).all() for n,w in self.widths.items()):
            raise ValueError('Incomplete parsed output')
        trace=dict(input_sha256=digest(x.tobytes()),packet_sha256=digest(packet),output_wire_sha256=digest(wire),
          input_bytes=len(packet),output_bytes=len(wire),valid_tokens=len(x),padded_tokens=32-len(x),activation_dtype='int8',
          activation_scale_dtype='float16',accumulator_dtype='float32',wire_output_dtype='float16_signed_FTZ',
          parsed_dtype='float32',widths=self.widths,output_conversion_contract=CONTRACT)
        return {k:v[:len(x)].copy() for k,v in parsed.items()},trace,wire

def with_kernel_boundary(mlp):
    """Return an independent graph view; never mutate an old object or file."""
    obj=copy.copy(mlp);obj.chains=[KernelPackedChain.from_legacy(c) for c in mlp.chains]
    obj.binding=copy.deepcopy(mlp.binding);obj.binding['output_conversion_contract']=CONTRACT
    obj.binding['chains']=[c.binding for c in obj.chains]
    return obj
