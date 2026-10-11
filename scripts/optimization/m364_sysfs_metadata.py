"""Bounded read of existing CMA sysfs counters; no allocation test."""
import json
import os
from pathlib import Path
import sys
import time
import m364_cma_metadata as p
sys.dont_write_bytecode=True
p.OUT=Path('/home/ubuntu/m364_cma_sysfs_evidence_01/BOARD_RESULT.json')
FIELDS={'alloc_pages_success','alloc_pages_fail','release_pages','total_pages','used_pages','maxchunk','base_pfn','count','order_per_bit'}

def run(expected):
    if p.OUT.parent.exists():raise RuntimeError('Immutable evidence; Collect only')
    start=time.monotonic()
    r=dict(status='FAIL_SYSFS_METADATA',scope='read-only-kernel-metadata-no-runtime',manifest_sha256=expected,gate_return_code=1,reserve_bytes=64<<20,overlay_loads=0,model_forward_calls=0,fpga_transactions=0,real_asset_data_reads=0,cache_eviction=False,capacity_proven=False,file_page_ownership_proven=False,errors=[])
    try:
        p.verify_package(expected)
        if os.geteuid()!=0:raise RuntimeError('Root required')
        root=Path('/sys/kernel/mm/cma');areas=[]
        r['meminfo_before']=p.read('/proc/meminfo')
        if not root.is_dir():raise RuntimeError('Existing sysfs CMA interface absent')
        for area in sorted(root.iterdir()):
            if not area.is_dir():continue
            names=sorted(x.name for x in area.iterdir())
            areas.append(dict(name=area.name,existing_names=names,counters={name:p.read(area/name,4096) for name in names if name in FIELDS}))
        r['areas']=areas;r['meminfo_after']=p.read('/proc/meminfo');r['snapshot_not_atomic']=True
        r['status']='COMPLETE_EXISTING_CMA_SYSFS_COUNTERS';r['gate_return_code']=0
    except Exception as e:r['errors'].append(type(e).__name__+': '+str(e))
    r['elapsed_s']=time.monotonic()-start
    p.OUT.parent.mkdir(parents=True,exist_ok=False);temp=p.OUT.with_suffix('.part')
    with temp.open('wb') as f:f.write((json.dumps(r,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
    os.replace(temp,p.OUT);return r['gate_return_code']

if __name__=='__main__':
    if sys.argv[1:]==['Collect']:p.export()
    elif len(sys.argv)==3 and sys.argv[1]=='Run':raise SystemExit(run(sys.argv[2]))
    else:raise SystemExit('Default disabled; Run exact-sha | Collect')
