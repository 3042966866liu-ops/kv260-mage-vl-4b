"""Unchanged late-visual M455 packet arithmetic, batched exact integer dot.

The PS/GELU operations stay on CPU. CUDA supplies only exact bounded integer
dot products and ordered separate FP32 products/adds, as the frozen local oracle.
This is software numerical evidence, never a board execution or timing claim.
"""
import importlib.util
from types import SimpleNamespace
from common import *

class LateOracle:
    def __init__(self,torch,protocol):
        from generate_flap522 import FrozenCheckpoint
        from adaptive.language_mlp_probe import PackedChain
        from adaptive.language_mlp_kernel_fp1602 import MIN_ROUND_UP_BITS
        self.torch=torch;self.minimum=MIN_ROUND_UP_BITS
        assert torch.cuda.is_available(),'Frozen CUDA oracle required; no math fallback'
        private=OPT/'candidates/M455-original94-layout-performance-05'
        spec=importlib.util.spec_from_file_location('_PS3072_frozen_M455_loader',private/'m455_private_runtime_loader01.py')
        loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
        self.factory=loader.load_private(private/'private_runtime',protocol['private_manifest_sha256'],namespace='_m455_PS3072_software')
        self.base=self.factory['base'];self.contract=self.factory['contract'];self.prepare=self.factory['runtime_class']._prepare_block
        cp=FrozenCheckpoint(read(OPT/'contracts/config.json'))
        rows={int(r['key'].split('_')[1]):r for r in read(PACKAGE/'TWENTYTWO_LAYER_PLAN.json')['layers'] if r['key'].startswith('vision')}
        assert set(rows)=={14,15,21}
        self.chains={};self.crops={};self.r1={}
        for i in range(13,24):
            name='model.visual.encoder.layers.'+str(i)+'.mlp.'
            if i in rows:
                row=rows[i];file=PACKAGE/row['codes']['path'];assert sha(file)==row['codes']['sha256']
                with np.load(file,allow_pickle=False) as z:
                    pairs={part:(z[part+'_codes'].copy(),z[part+'_scales'].copy()) for part in ('fc1','fc2')}
                # Original kept groups are recoverable exactly from the frozen plan or NPZ.
                with np.load(file,allow_pickle=False) as z:
                    candidates=[k for k in z.files if 'kept' in k or 'keep' in k]
                    if candidates:
                        kept=np.array(z[candidates[0]],np.int64).reshape(-1)
                    else:
                        original=cp.packed(name+'fc1')[0]
                        c,s=pairs['fc1'];groups=[]
                        for group in range(64):
                            block=original[0][group*64:(group+1)*64];sc=original[1][group*64:(group+1)*64]
                            for j in range(56):
                                if c[j*64:(j+1)*64].tobytes()==block.tobytes() and s[j*64:(j+1)*64].tobytes()==sc.tobytes():groups.append(group)
                        assert len(groups)==56;kept=np.array(groups,np.int64)
                if len(kept)==56:kept=(kept[:,None]*64+np.arange(64)).reshape(-1)
                assert kept.shape==(3584,) and np.array_equal(kept,np.unique(kept))
                self.crops[i]=kept
                file=PACKAGE/row['R1']['path'];assert sha(file)==row['R1']['sha256'];self.r1[i]=np.frombuffer(file.read_bytes(),np.float32).copy()
            else:
                pairs={}
                for part in ('fc1','fc2'):
                    pair,bits=cp.packed(name+part);assert bits==4;pairs[part]=pair
            for part,(c,s) in pairs.items():
                chain=PackedChain([(name+part,c,s)],device='cuda')
                chain.dense=self.factory['modules']['m455_runtime_abi01'].convert_chain(chain.chain)
                self.chains[i,part]=chain
        self.trace=[]

    def _batch(self,chain,blocks,shifts):
        torch=self.torch;packets=[];aq=[];sq=[];dense=chain.dense;count=len(chain.decoded);groups=dense['groups']
        for block,shift in zip(blocks,shifts):
            packet=self.prepare(dense,np.ascontiguousarray(block),0,0,int(shift)).packet
            rec=np.frombuffer(packet[count*16:],np.uint8).reshape(groups,32,80)
            aq.append(rec[:,:,:64].copy().view(np.int8).transpose(1,0,2))
            sq.append(rec[:,:,64:66].copy().view('<f2').reshape(groups,32).T.copy())
            packets.append(packet)
        aa=torch.from_numpy(np.concatenate(aq)).to('cuda',dtype=torch.float32)
        scales=torch.from_numpy(np.concatenate(sq)).to('cuda');all_bits=[]
        # Integer products sum to <2^24, so GEMM ordering cannot change dots.
        for descriptor,(codes,ws) in zip(dense['descriptors'],chain.decoded):
            dots=torch.bmm(aa.permute(1,0,2).contiguous(),codes.transpose(1,2).contiguous())
            acc=torch.zeros((len(blocks)*32,codes.shape[1]),device='cuda',dtype=torch.float32)
            for group in range(groups):
                term=dots[group]*scales[:,group:group+1].float()
                term=term*ws[group].float().unsqueeze(0)
                acc=acc+term
            a=acc.cpu().numpy();assert np.isfinite(a).all()
            u=np.ascontiguousarray(a).view(np.uint32)
            with np.errstate(over='ignore'):bits=a.astype('<f2').view('<u2').copy()
            tiny=(u&np.uint32(0x7fffffff))<self.minimum
            bits[tiny]=((u[tiny]>>16)&np.uint32(0x8000)).astype(np.uint16)
            all_bits.append(bits.reshape(len(blocks),32,codes.shape[1]))
        result=[]
        for j,(packet,shift) in enumerate(zip(packets,shifts)):
            parts=[]
            for descriptor,bits in zip(dense['descriptors'],all_bits):
                n=descriptor['rows_per_shard']//8
                parts.append(bits[j].reshape(32,4,n,4,2).transpose(2,0,1,3,4).copy().tobytes())
            wire=b''.join(parts);assert len(wire)==dense['output_bytes']
            outputs=self.contract.parse_chain_output(dense,wire,output_scale_shift=int(shift))
            finite=self.base.M120BoardRuntime._written_outputs_finite(dense,outputs)
            result.append((outputs,dict(shift=int(shift),finite=bool(finite),packet_sha256=hashlib.sha256(packet).hexdigest(),wire_sha256=hashlib.sha256(wire).hexdigest())))
        return result

    def run(self,index,part,x):
        chain=self.chains[index,part];x=np.ascontiguousarray(x,dtype=np.float32)
        assert x.shape==(392,chain.chain['groups']*64) and np.isfinite(x).all()
        blocks=[x[s:s+32] for s in range(0,392,32)]
        shifts=[self.base.M120BoardRuntime._initial_scale_shift(b) for b in blocks]
        outputs=self._batch(chain,blocks,shifts);answer=[]
        name=chain.chain['descriptors'][0]['module']
        for j,(a,proof) in enumerate(outputs):
            attempts=[proof]
            if not proof['finite']:
                for shift in range(shifts[j]-1,-1,-1):
                    a,proof=self._batch(chain,[blocks[j]],[shift])[0];attempts.append(proof)
                    if proof['finite']:break
            assert proof['finite'],'Original adaptive policy exhausted; no clip/fallback'
            y=a[name][:len(blocks[j])].copy();assert np.isfinite(y).all();answer.append(y)
            self.trace.append(dict(layer=index,part=part,start=j*32,rows=len(y),initial_shift=shifts[j],attempts=attempts))
        return np.concatenate(answer)

    def bind(self,runtime):
        torch=self.torch;previous=[]
        for i in range(13,24):
            mlp=inner(runtime,i).mlp
            for part in ('fc1','fc2'):
                mod=getattr(mlp,part);owned='forward' in mod.__dict__;old=mod.__dict__.get('forward');previous.append((mod,owned,old))
                assert mod.output_dtype==torch.float32 and mod.bias.dtype==torch.float32
                bias=mod.bias.detach().float().numpy().copy()
                if i in self.crops and part=='fc1':bias=bias[self.crops[i]].copy()
                def forward(values,i=i,part=part,bias=bias):
                    a=values.detach().float().numpy();native=a.ndim==3
                    if native:assert a.shape[0]==1;a=a[0]
                    y=np.add(self.run(i,part,a),bias,dtype=np.float32)
                    if i in self.r1 and part=='fc2':y=np.add(y,self.r1[i],dtype=np.float32)
                    return torch.from_numpy(y[None] if native else y)
                mod.forward=forward
        return previous

    @staticmethod
    def restore(previous):
        for mod,owned,old in reversed(previous):
            if owned:mod.forward=old
            else:del mod.__dict__['forward']
        assert all(('forward' in m.__dict__)==o and (not o or m.__dict__['forward'] is v) for m,o,v in previous)
