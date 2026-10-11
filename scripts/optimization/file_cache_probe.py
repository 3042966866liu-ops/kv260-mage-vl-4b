"""Read-only, bounded real packed-weight window probe. No torch/PYNQ imports."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot():
    io={k:int(v) for k,v in (line.split(':') for line in Path('/proc/self/io').read_text().splitlines())}
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return dict(**io,minflt=usage.ru_minflt,majflt=usage.ru_majflt)


def resident(path,offset,size):
    # PROT_NONE observes residency without touching/faulting weight pages.
    page=os.sysconf('SC_PAGE_SIZE');aligned=offset//page*page
    length=offset+size-aligned;pages=(length+page-1)//page
    libc=ctypes.CDLL(None,use_errno=True)
    libc.mmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_long]
    libc.mmap.restype=ctypes.c_void_p
    libc.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p]
    libc.munmap.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    with path.open('rb',buffering=0) as stream:
        address=libc.mmap(None,length,0,2,stream.fileno(),aligned)
        if address==ctypes.c_void_p(-1).value:raise OSError(ctypes.get_errno(),'mmap')
        try:
            vector=(ctypes.c_ubyte*pages)()
            if libc.mincore(address,length,vector)!=0:raise OSError(ctypes.get_errno(),'mincore')
            return dict(pages=pages,resident_pages=sum(int(v)&1 for v in vector),page_bytes=page)
        finally:
            if libc.munmap(address,length)!=0:raise OSError(ctypes.get_errno(),'munmap')


def main():
    script_sha,plan_sha=sys.argv[1:]
    if digest(__file__)!=script_sha:raise RuntimeError('Probe identity mismatch')
    here=Path(__file__).resolve().parent;plan_path=here/'plan.json'
    if digest(plan_path)!=plan_sha:raise RuntimeError('Plan identity mismatch')
    plan=json.loads(plan_path.read_text());output=here/'result.json'
    if output.exists():raise RuntimeError('Immutable result exists')
    result=dict(status='FAIL',scope='Read-only file/cache microprobe; idle process, not inference performance',
                script_sha256=script_sha,plan_sha256=plan_sha,records=[],errors=[],
                overlay_loaded=False,model_executed=False,cache_evicted=False)
    try:
        root=Path('/home/ubuntu/tellme_m120_m89x2_20260901/m120_fulltext_weights_0x4D395832/language_fourport')
        manifest=root/'SIXPORT_LAYOUT_MANIFEST.json'
        if digest(manifest)!=plan['layout_sha256']:raise RuntimeError('Layout identity mismatch')
        layout=json.loads(manifest.read_text())
        if len(plan['windows'])!=4:raise RuntimeError('Expected four gate_up windows')
        result['meminfo_before']=Path('/proc/meminfo').read_text()
        for item in plan['windows']:
            shard=item['shard'];member=layout['files'][shard]
            if member['path']!=f'weights{shard}.bin':raise RuntimeError('Wrong shard')
            path=root/member['path'];size=item['bytes'];offset=item['offset']
            if path.stat().st_size!=member['bytes'] or not 0<size<=8*1024*1024 or offset<0 or offset+size>member['bytes']:
                raise RuntimeError('File size/window bound')
            reference=None
            for repeat in range(3):
                before_resident=resident(path,offset,size)
                before=snapshot();start=time.perf_counter_ns()
                with path.open('rb',buffering=0) as stream:
                    stream.seek(offset);payload=stream.read(size)
                elapsed=time.perf_counter_ns()-start;after=snapshot()
                if len(payload)!=size or hashlib.sha256(payload).hexdigest()!=item['sha256']:
                    raise RuntimeError('Real weight window bytes differ')
                result['records'].append(dict(shard=shard,repeat=repeat,bytes=size,offset=offset,
                    sha256=item['sha256'],read_s=elapsed/1e9,
                    io_delta={k:after[k]-before[k] for k in before},
                    residency_before=before_resident,residency_after=resident(path,offset,size),byte_exact=True))
                del payload
        result['status']='MEASURED'
    except Exception as exc:result['errors'].append(repr(exc))
    temporary=output.with_suffix('.partial')
    temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');os.replace(temporary,output)
    print('FILE_CACHE_JSON_BEGIN');print(json.dumps(result));print('FILE_CACHE_JSON_END',flush=True)
    return 0 if result['status']=='MEASURED' else 1


if __name__=='__main__':raise SystemExit(main())
