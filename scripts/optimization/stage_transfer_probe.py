"""Bounded read/copy/sync probe, no overlay load, DMA or model execution."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/home/ubuntu/tellme_m120_m89x2_20260901')
BASE=ROOT/'optimization_v1';STABLE=ROOT/'m175_m120_fixed_text_candidate'
SYS_SHA='cc63e7288c455ae848edd495325f4d53392f79d0c01c4135c7fd4e54dc78a194'
STABLE_SHA='406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_package(path,expected):
    manifest=path/'PACKAGE_MANIFEST.json'
    if digest(manifest)!=expected:raise RuntimeError('Package identity mismatch')
    data=json.loads(manifest.read_text());rows=data['files']
    actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and p!=manifest}
    if actual!={r['path'] for r in rows} or len(rows)!=data['file_count']:raise RuntimeError('Package members differ')
    if sum(r['bytes'] for r in rows)!=data['total_bytes']:raise RuntimeError('Package bytes differ')
    for row in rows:
        member=(path/row['path']).resolve();member.relative_to(path.resolve())
        if member.stat().st_size!=row['bytes'] or digest(member)!=row['sha256']:raise RuntimeError('Member changed')


def read_exact(path,offset,size,target=None):
    with path.open('rb',buffering=0) as stream:
        stream.seek(offset)
        if target is None:
            value=stream.read(size)
            if len(value)!=size:raise RuntimeError('Short file read')
            return value
        view=memoryview(target).cast('B')[:size];count=0
        while count<size:
            n=stream.readinto(view[count:])
            if not n:raise RuntimeError('Short readinto')
            count+=n


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--result',type=Path,required=True);args=parser.parse_args()
    here=Path(__file__).resolve().parent;verify_package(here,args.manifest_sha256)
    prior=BASE/'OP01-SYS-02';verify_package(prior,SYS_SHA)
    config=json.loads((prior/'sys_config.json').read_text())
    sys.path[:0]=[str(prior)]+[str(ROOT/p) for p in config['python_path']]
    from measurement import write_json
    from op00_stable_probe import service_stopped
    if args.result.exists():raise RuntimeError('Immutable result exists')
    result=dict(status='FAIL',scope='Bounded warm-cache transfer microbenchmark only',records=[],errors=[],
                overlay_loaded=False,dma_launched=False,model_executed=False)
    buffer=None;fd=None
    try:
        if os.geteuid()!=0:raise RuntimeError('Root required for CMA probe')
        fd=os.open('/tmp/tellme_kv260_execution.lock',os.O_RDWR|os.O_CREAT,0o600)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result['service_before']=service_stopped()
        result['boot_before']=digest('/boot/firmware/boot.scr.uimg');result['cmdline_before']=Path('/proc/cmdline').read_text()
        preflight=subprocess.run([sys.executable,str(STABLE/'runtime/m120_board_env_preflight.py'),
            '--candidate',str(STABLE),'--expected-package-manifest-sha256',STABLE_SHA,
            '--result',str(args.result.with_name(args.result.stem+'_environment.json'))],check=True,timeout=60)
        import numpy as np
        import board_runtime as runtime
        from pynq import allocate
        contract=json.loads((STABLE/'contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json').read_text())
        layout_root=ROOT/'m120_fulltext_weights_0x4D395832/language_fourport'
        layout_path=layout_root/'SIXPORT_LAYOUT_MANIFEST.json'
        if digest(layout_path)!=contract['source_manifest_sha256']:raise RuntimeError('Layout manifest mismatch')
        layout=runtime.VerifiedLayout(layout_root,json.loads(layout_path.read_text()),digest(layout_path))
        selected=[c for c in contract['chains'] if c['layer']==0 and c['family'] in ('q','gate_up','mlp_down')]
        if len(selected)!=3:raise RuntimeError('Probe family selection differs')
        windows=[(c,*runtime.chain_window(layout,c)) for c in selected]
        maximum=max(n for _,_,n in windows)
        if not 0<maximum<=8*1024*1024:raise RuntimeError('Probe allocation outside bound')
        buffer=allocate((maximum,),dtype=np.uint8)
        address=int(buffer.physical_address)
        if address+maximum>0x80000000:raise RuntimeError('CMA not in low DDR')
        result.update(buffer_bytes=maximum,physical_address=hex(address),
            coherent=bool(getattr(buffer,'coherent',False)),cacheable=getattr(buffer,'cacheable',None),
            package_manifest_sha256=args.manifest_sha256,layout_manifest_sha256=digest(layout_path))
        for chain,base_words,size in windows:
            for shard,row in enumerate(layout.manifest['files']):
                path=layout_root/row['path']
                if path.stat().st_size!=row['bytes']:raise RuntimeError('Shard size changed')
                offset=base_words*16;start=time.perf_counter()
                reference=read_exact(path,offset,size);first_read_s=time.perf_counter()-start
                reference_sha=hashlib.sha256(reference).hexdigest()
                cpu=np.empty(size,np.uint8);cpu.fill(0)
                start=time.perf_counter();cpu[:]=np.frombuffer(reference,np.uint8);cpu_copy_s=time.perf_counter()-start
                for repeat in range(3):
                    modes=('read_copy','readinto') if repeat%2==0 else ('readinto','read_copy')
                    for mode in modes:
                        start=time.perf_counter()
                        if mode=='read_copy':
                            payload=read_exact(path,offset,size);read_s=time.perf_counter()-start
                            start=time.perf_counter();buffer[:size]=np.frombuffer(payload,np.uint8);copy_s=time.perf_counter()-start
                        else:
                            read_exact(path,offset,size,buffer);read_s=time.perf_counter()-start;copy_s=None
                        start=time.perf_counter();buffer.sync_to_device();sync_s=time.perf_counter()-start
                        actual=hashlib.sha256(memoryview(buffer)[:size]).hexdigest()
                        if actual!=reference_sha:raise RuntimeError('CMA byte mismatch')
                        result['records'].append(dict(family=chain['family'],shard=shard,repeat=repeat,mode=mode,
                            bytes=size,offset=offset,sha256=reference_sha,read_s=read_s,copy_s=copy_s,sync_s=sync_s,
                            first_read_s=first_read_s,cpu_copy_s=cpu_copy_s,total_s=read_s+(copy_s or 0)+sync_s,
                            byte_exact=True,cache_condition='reference read before AB; no dropped caches'))
                print('OP01_STAGE_PROGRESS '+chain['family']+' shard='+str(shard),flush=True)
        result['status']='MEASURED'
    except Exception as exc:
        import traceback
        result['errors'].append(repr(exc));result['traceback']=traceback.format_exc()
    finally:
        if buffer is not None:
            try:buffer.freebuffer();result['buffer_released']=True
            except Exception as exc:result['status']='FAIL';result['errors'].append('free:'+repr(exc))
        result['boot_unchanged']=result.get('boot_before')==digest('/boot/firmware/boot.scr.uimg')
        result['cmdline_unchanged']=result.get('cmdline_before')==Path('/proc/cmdline').read_text()
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:result['status']='FAIL'
        write_json(args.result,result)
        print('OP01_STAGE_JSON_BEGIN');print(json.dumps(result));print('OP01_STAGE_JSON_END',flush=True)
        if fd is not None:os.close(fd)
    return 0 if result['status']=='MEASURED' else 1


if __name__=='__main__':raise SystemExit(main())
