"""Full original-chain arithmetic oracle for deterministic nonzero T32 input."""
import hashlib
import numpy as np
from m120_group_reference import group_reference


def activation(groups):
    values=(np.arange(32*groups*64,dtype=np.int32)%31-15).astype(np.float32)
    return (values*np.float32(0.002)).reshape(32,groups*64)


def decode_records(raw,groups,rows,bits):
    blocks=rows//8
    records=np.frombuffer(raw,np.uint8).reshape(groups,blocks,1+4*bits,16)
    tags=records[:,:,0,:].copy().view('<u2').reshape(groups,blocks,8)
    data=records[:,:,1:,:].copy().reshape(groups,blocks,8,8*bits)
    lane=np.arange(64,dtype=np.int32)
    if bits==2:
        codes=((data[...,lane>>2]>>((lane&3)*2))&3).astype(np.int16)
        zeros=np.where(tags&0x8000,-1,-2)
    elif bits==4:
        codes=((data[...,lane>>1]>>((lane&1)*4))&15).astype(np.int16)
        zeros=np.where(tags&0x8000,-7,-8)
    else:raise ValueError('Invalid frozen bit width')
    codes=(codes+zeros[...,None]).astype(np.int8).reshape(groups,rows,64)
    scales=(tags&np.uint16(0x7fff)).copy().view('<f2').reshape(groups,rows)
    if not np.isfinite(scales).all():raise ValueError('Nonfinite original weight scale')
    return codes,scales


def full_reference(chain,windows,base_words,packet):
    groups=int(chain['groups']);bits=int(chain['bits']);count=len(chain['descriptors'])
    records=np.frombuffer(packet[count*16:],np.uint8).reshape(groups,32,80)
    codes=records[:,:,:64].copy().view(np.int8).transpose(1,0,2)
    scales=records[:,:,64:66].copy().view('<f2').reshape(groups,32).T.copy()
    outputs=[]
    for descriptor in chain['descriptors']:
        rows=int(descriptor['rows_per_shard']);blocks=rows//8
        offset=(int(descriptor['encoded_u64'],16)&0xffffffff)-base_words
        start=offset*16;size=groups*blocks*(1+4*bits)*16
        shards=[]
        for window in windows:
            payload=window[start:start+size]
            if len(payload)!=size:raise ValueError('Reference window short')
            weights,weight_scales=decode_records(payload,groups,rows,bits)
            result=group_reference(codes,scales,weights,weight_scales,dot_mode='fp32_exact')
            if not np.isfinite(result).all():raise ValueError('Diagnostic reference would need retry')
            # Existing M157 FTZ: only FP16 subnormal lanes become signed zero.
            u=result.view('<u2').copy()
            mask=((u&0x7c00)==0)&((u&0x03ff)!=0)
            u[mask]&=np.uint16(0x8000)
            shards.append(u)
        data=np.stack(shards,axis=1).reshape(32,4,blocks,4,2).transpose(2,0,1,3,4)
        wire=np.zeros((blocks,32,4,4,4),'<u2')
        wire[...,0]=data[...,0];wire[...,2]=data[...,1]
        outputs.append(wire.tobytes())
    raw=b''.join(outputs)
    if len(raw)!=int(chain['output_bytes']):raise ValueError('Full reference output size differs')
    return raw


def digest(raw):return hashlib.sha256(raw).hexdigest()
