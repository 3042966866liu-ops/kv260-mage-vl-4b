"""Exact immutable saved-input/weight binding before any FPGA resource."""
import hashlib,json,stat
from pathlib import Path
import numpy as np

def read_exact(path,size,digest,*,offset=None,file_size=None):
    def identity():
        s=path.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise RuntimeError('Plain sole-linked artifact required')
        return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
    before=identity()
    if before[2]!=(size if file_size is None else file_size):raise RuntimeError('File byte size differs')
    with path.open('rb') as f:
        if offset is not None:f.seek(offset)
        raw=f.read(size)
    if identity()!=before or len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('Saved byte identity differs')
    return raw

def load_case(spec,mode,root,host):
    folder=Path(spec['reference_directory'])
    blob=read_exact(folder/'RESULT.json',spec['reference_result_bytes'],spec['reference_raw_sha256'])
    r=json.loads(blob)
    if r['status']!='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE' or r['gate_return_code'] or not r['local_exact_arithmetic_screen_pass'] or not r['bindings_restored'] or not r['visual_owner_closed'] or r['logical_reference_calls']!=26:raise RuntimeError('Exact software prerequisite rejected')
    selected=spec['cases'][mode];chain=selected['chain'];part=selected['part'];batch=r['reference_batches'][part][0]
    if batch['start']!=0 or batch['rows']!=32 or batch['selected_shift']!=selected['shift']:raise RuntimeError('Selected reference batch differs')
    packet_name=f'{part}_000_shift{selected["shift"]}.packet';raw_name=f'{part}_000_shift{selected["shift"]}.raw'
    packet=read_exact(folder/packet_name,chain['input_bytes'],batch['packet_sha256'])
    golden=read_exact(folder/raw_name,chain['output_bytes'],batch['raw_sha256'])
    key='input' if part=='fc1' else 'gelu';a=next(x for x in r['artifacts'] if x['path']==key+'.npy')
    data=read_exact(folder/a['path'],a['bytes'],a['sha256'])
    import io
    values=np.load(io.BytesIO(data),allow_pickle=False)
    meta=r['candidate_tensors'][key]
    if values.dtype!=np.float32 or list(values.shape)!=meta['shape'] or values.shape!=(392,chain['groups']*64) or not np.isfinite(values).all() or hashlib.sha256(values.tobytes()).hexdigest()!=meta['sha256']:raise RuntimeError('Actual saved activation differs')
    if host.pack_chain_input(chain,values[:32],chain['stage_base_words'],activation_scale_shift=selected['shift'])!=packet:raise RuntimeError('Original stable pack differs')
    windows=[]
    for row in selected['windows']:
        p=root/row['relative_file']
        windows.append(read_exact(p,row['bytes'],row['sha256'],offset=row['offset'],file_size=row['file_bytes']))
    if [dict(path=x['path'],offset=x['offset'],bytes=x['bytes'],sha256=x['sha256']) for x in selected['windows']]!=r['windows'][part]:raise RuntimeError('Frozen original windows differ')
    return chain,packet,golden,windows,dict(reference_raw_sha256=spec['reference_raw_sha256'],part=part,
        selected_shift=selected['shift'],packet_sha256=batch['packet_sha256'],raw_sha256=batch['raw_sha256'])
