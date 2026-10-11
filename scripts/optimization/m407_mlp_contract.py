"""Default-off PS-vision MLP experiment contracts; no hardware imports/actions."""
import numpy as np

def chain_for(entry, index):
    rows, columns=map(int,entry['shape']);groups=int(entry['input_groups']);bits=int(entry['bits'])
    if bits!=4 or columns!=groups*64 or not 1<=groups<=152:
        raise ValueError('Existing W4/G64 kernel geometry required')
    tiles=entry['tiles']
    if not 1<=len(tiles)<=10:raise ValueError('Descriptor bound')
    descriptors=[];cursor=0;lo=None;hi=0
    for tile in tiles:
        start=int(tile['row_start']);valid=int(tile['valid_rows']);per=int(tile['rows_per_shard'])
        offsets=list(map(int,tile['shard_offsets']));size=int(tile['record_bytes_per_shard'])
        if start!=cursor or not 8<=per<=512 or per%8 or not 0<valid<=4*per:
            raise ValueError('Rows, ordering or maximum FIFO contract')
        if len(offsets)!=4 or len(set(offsets))!=1 or offsets[0]%16:
            raise ValueError('Four equal aligned shard windows required')
        if size!=groups*(per//8)*272:raise ValueError('Record byte geometry')
        offset=offsets[0];lo=offset if lo is None else min(lo,offset);hi=max(hi,offset+size)
        raw=(offset//16)|(per<<32)|(bits<<42)
        descriptors.append(dict(module=entry['module'],tile_index=int(tile['tile_index']),row_start=start,
            valid_rows=valid,rows_per_shard=per,offset_words=offset//16,encoded_u64=f'0x{raw:016x}',
            output_bytes=32*4*per*4,weight_bytes_per_shard=size,shard_stream_words=(per//8)*32*4))
        cursor+=valid
    if cursor!=rows:raise ValueError('Incomplete output rows')
    if hi-lo!=sum(d['weight_bytes_per_shard'] for d in descriptors):raise ValueError('Unexpected gap/overlap in staging window')
    return dict(chain_index=index,layer=None,family='vision_mlp',module=entry['module'],groups=groups,bits=bits,
        descriptor_count=len(descriptors),descriptors=descriptors,input_bytes=16*len(descriptors)+groups*32*80,
        output_bytes=sum(d['output_bytes'] for d in descriptors),config=f'0x{groups|(bits<<8)|(len(descriptors)<<16):08x}',
        stage_base_words=lo//16,stage_bytes_per_shard=hi-lo,expected_macros=32*rows*columns)

def metrics(reference,candidate):
    a=np.asarray(reference,np.float64);b=np.asarray(candidate,np.float64)
    if a.shape!=b.shape or a.ndim!=2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Finite complete same-shape outputs required')
    delta=b-a;norm=float(np.linalg.norm(a));other=float(np.linalg.norm(b))
    if norm==0 or other==0:raise ValueError('Cannot certify cosine for zero norm')
    norms=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
    if np.any(norms==0):raise ValueError('Zero token norm')
    return dict(shape=list(a.shape),cosine=float(np.sum(a*b)/(norm*other)),
        relative_l2=float(np.linalg.norm(delta)/norm),RMSE=float(np.sqrt(np.mean(delta**2))),
        max_abs=float(np.max(np.abs(delta))),min_token_cosine=float(np.min(np.sum(a*b,axis=1)/norms)))

def local_screen(value):
    # Preliminary rejection screen only; never semantic-quality certification.
    return bool(value['cosine']>=0.999 and value['relative_l2']<=0.02 and value['min_token_cosine']>=0.995)
