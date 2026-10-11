"""Read existing kernel metadata only. No asset reads, faults, allocation or PL."""
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time

sys.dont_write_bytecode = True
OUT = Path('/home/ubuntu/m364_cma_metadata_evidence_01/BOARD_RESULT.json')
LIMIT = 4 << 20
BITS = {0:'LOCKED',1:'ERROR',2:'REFERENCED',3:'UPTODATE',4:'DIRTY',5:'LRU',6:'ACTIVE',7:'SLAB',8:'WRITEBACK',9:'RECLAIM',10:'BUDDY',11:'MMAP',12:'ANON',13:'SWAPCACHE',14:'SWAPBACKED',15:'COMPOUND_HEAD',16:'COMPOUND_TAIL',17:'HUGE',18:'UNEVICTABLE',19:'HWPOISON',20:'NOPAGE',21:'KSM',22:'THP',23:'OFFLINE',24:'ZERO_PAGE',25:'IDLE',26:'PGTABLE'}

def read(path, limit=262144):
    try:
        with open(path, 'rb') as f:
            raw = f.read(limit + 1)
        return dict(available=True, truncated=len(raw)>limit, text=raw[:limit].decode('utf-8',errors='replace'))
    except OSError as e:
        return dict(available=False, error=type(e).__name__+': '+str(e))

def summarize(raw):
    if len(raw)%8: raise ValueError('Short kpageflags word')
    counts={name:0 for name in BITS.values()}
    counts.update(file_lru_candidate=0,anon_lru=0,zero_flags=0)
    for (v,) in struct.iter_unpack('=Q',raw):
        for bit,name in BITS.items(): counts[name]+=bool(v&(1<<bit))
        counts['file_lru_candidate']+=bool(v&(1<<5) and not v&((1<<12)|(1<<14)))
        counts['anon_lru']+=bool(v&(1<<5) and v&(1<<12))
        counts['zero_flags']+=v==0
    return dict(pages=len(raw)//8,flags_nonexclusive=counts,file_owner_proven=False)

def verify_package(expected):
    root=Path(__file__).resolve().parent
    manifest=root/'PACKAGE_MANIFEST.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=expected: raise ValueError('Manifest SHA differs')
    m=json.loads(manifest.read_text())
    if len(m['files'])!=m['file_count'] or sum(x['bytes'] for x in m['files'])!=m['total_bytes']: raise ValueError('Manifest count differs')
    if {p.name for p in root.iterdir()}!={x['path'] for x in m['files']}|{'PACKAGE_MANIFEST.json'}: raise ValueError('Package whitelist differs')
    for x in m['files']:
        if '/' in x['path'] or '\\' in x['path'] or x['path'] in ('.','..'): raise ValueError('Path rejected')
        b=(root/x['path']).read_bytes()
        if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']: raise ValueError('Payload SHA differs')

def export():
    raw=OUT.read_bytes();r=json.loads(raw)
    print('M364_RESULT_SHA256='+hashlib.sha256(raw).hexdigest())
    print('M364_SAVED_GATE_RC='+str(r['gate_return_code']))
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,b in enumerate(parts):print('M364_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(b).decode())

def run(expected):
    if OUT.parent.exists():raise RuntimeError('Immutable evidence exists; Collect only')
    started=time.monotonic()
    r=dict(status='FAIL_METADATA_PROBE',gate_return_code=1,manifest_sha256=expected,scope='read-only-kernel-metadata-no-runtime',overlay_loads=0,model_forward_calls=0,fpga_transactions=0,real_asset_data_reads=0,cache_eviction=False,reserve_bytes=64<<20,capacity_proven=False,file_page_ownership_proven=False,errors=[])
    try:
        verify_package(expected)
        if os.geteuid()!=0 or os.uname().sysname!='Linux':raise RuntimeError('Root Linux required')
        r['platform']=dict(uname=list(os.uname()),euid=os.geteuid(),page_size=os.sysconf('SC_PAGE_SIZE'),capabilities=read('/proc/self/status')['text'].split('CapEff:')[-1].splitlines()[0].strip())
        r['before']={p:read(p) for p in ('/proc/meminfo','/proc/vmstat','/proc/buddyinfo','/proc/pagetypeinfo','/proc/zoneinfo','/proc/self/mountinfo','/proc/cmdline')}
        r['existing_debugfs_cma']=[]
        debug=Path('/sys/kernel/debug/cma')
        r['cma_debugfs_directory_exists']=debug.is_dir()
        r['sysfs_cma_directory_exists']=Path('/sys/kernel/mm/cma').is_dir()
        r['page_owner_existing_file']=Path('/sys/kernel/debug/page_owner').exists()
        ranges=[]
        if debug.is_dir():
            for area in sorted(debug.iterdir()):
                if not area.is_dir():continue
                item=dict(name=area.name,metadata={key:read(area/key) for key in ('base_pfn','count','order_per_bit','bitmap')})
                nested=area/'ranges'
                if nested.is_dir():
                    item['ranges']=[dict(name=p.name,base_pfn=read(p/'base_pfn'),count=read(p/'count')) for p in sorted(nested.iterdir()) if p.is_dir()]
                r['existing_debugfs_cma'].append(item)
                sources=item.get('ranges') or [dict(base_pfn=item['metadata']['base_pfn'],count=item['metadata']['count'])]
                for s in sources:
                    try:
                        if not s['base_pfn']['available'] or not s['count']['available']:continue
                        base=int(s['base_pfn']['text'].strip(),0);count=int(s['count']['text'].strip(),0)
                        if base<=0 or count<=0:raise ValueError('Invalid physical range')
                        ranges.append((area.name,base,count))
                    except (KeyError,ValueError) as e:item['range_error']=str(e)
        r['cma_range_metadata_proven']=False
        r['range_flag_summaries']=[]
        if ranges:
            ordered=sorted(ranges,key=lambda x:x[1])
            if any(ordered[i-1][1]+ordered[i-1][2]>ordered[i][1] for i in range(1,len(ordered))):raise ValueError('Overlapping CMA ranges')
            total=sum(n for _,_,n in ranges)
            if total*8>LIMIT:raise ValueError('Physical metadata byte budget exceeded')
            mem=r['before']['/proc/meminfo']['text']
            cmatotal=int(next(x.split()[1] for x in mem.splitlines() if x.startswith('CmaTotal:')))*1024
            if total*r['platform']['page_size']!=cmatotal:raise ValueError('CMA ranges do not cover CmaTotal exactly')
            r['cma_range_metadata_proven']=True
            try:
                with open('/proc/kpageflags','rb',buffering=0) as f:
                    for name,base,count in ranges:
                        f.seek(base*8);raw=f.read(count*8)
                        if len(raw)!=count*8:raise ValueError('Short physical metadata read')
                        r['range_flag_summaries'].append(dict(area=name,base_pfn=base,count=count,summary=summarize(raw)))
            except OSError as e:r['kpageflags_error']=str(e)
        r['after']={p:read(p) for p in ('/proc/meminfo','/proc/vmstat')}
        r['snapshot_not_atomic']=True
        r['status']='COMPLETE_KERNEL_METADATA_ONLY' if r['range_flag_summaries'] else 'PARTIAL_KERNEL_METADATA_CMA_PFN_UNAVAILABLE'
        r['gate_return_code']=0
    except Exception as e:r['errors'].append(type(e).__name__+': '+str(e))
    r['elapsed_s']=time.monotonic()-started
    if r['elapsed_s']>30:r['errors'].append('Read-only budget exceeded');r['gate_return_code']=1;r['status']='FAIL_METADATA_PROBE'
    OUT.parent.mkdir(parents=True,exist_ok=False)
    temp=OUT.with_suffix('.part')
    with temp.open('wb') as f:f.write((json.dumps(r,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
    os.replace(temp,OUT)
    return r['gate_return_code']

if __name__=='__main__':
    if sys.argv[1:]==['Collect']:export()
    elif len(sys.argv)==3 and sys.argv[1]=='Run':raise SystemExit(run(sys.argv[2]))
    else:raise SystemExit('Default disabled; Run exact-manifest-sha | Collect')
