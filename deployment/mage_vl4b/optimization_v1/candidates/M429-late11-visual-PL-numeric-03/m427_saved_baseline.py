"""Bounded immutable M426 original arrays; no replacement model execution."""
import hashlib,io,json,stat
from pathlib import Path
import numpy as np
BASELINE=Path('/home/ubuntu/m426_range_software_02')

def read_owned(path,size,expected=None):
    p=Path(path);before=p.lstat()
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink,s.st_uid)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=0 or before.st_size!=size or size>2<<20:raise ValueError('Saved baseline ownership/type/size differs')
    raw=p.read_bytes();after=p.lstat()
    if identity(before)!=identity(after) or len(raw)!=size or (expected is not None and hashlib.sha256(raw).hexdigest()!=expected):raise ValueError('Saved baseline identity/SHA differs')
    return raw

def source(plan):
    raw=read_owned(BASELINE/'BOARD_RESULT.json',plan['baseline_raw_bytes'],plan['baseline_raw_sha256']);r=json.loads(raw)
    if r['status']!='REJECT_M426_ALL22_FEATURE_RANGE' or type(r['gate_return_code']) is not int or r['gate_return_code'] or not r['original_reference_pass'] or not r['bindings_restored'] or not r['visual_owner_closed'] or r['selected_layers']!=list(range(2,24)) or r['overlay_loaded'] or r['dma_allocations'] or r['fpga_transactions']:raise ValueError('Complete original baseline prerequisite differs')
    return r

def array(name,expected,file_sha=None,folder=BASELINE):
    if name not in ['original_visual.npy']+[f'original_boundary_{i:02d}.npy' for i in range(24)]:raise ValueError('Frozen original array whitelist required')
    raw=read_owned(folder/name,expected['bytes']+128,file_sha);x=np.load(io.BytesIO(raw),allow_pickle=False)
    from m414_quality import tensor
    if tensor(x)!=expected:raise ValueError('Frozen complete original tensor differs')
    x.flags.writeable=False;return x

def feature(r):
    row=r['retained_features'][0]
    if row['path']!='original_visual.npy' or row['bytes']!=1003648:raise ValueError('Original feature file manifest differs')
    return array(row['path'],r['original_visual'],row['sha256'])

def boundary(r,index):
    row=r['boundary_comparison'][index]
    if row['layer']!=index:raise ValueError('Original all24 boundary order differs')
    return array(f'original_boundary_{index:02d}.npy',row['original'])
