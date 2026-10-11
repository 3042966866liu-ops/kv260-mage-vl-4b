"""One original asset inspect, per-digest observations, no runtime or devices."""
import argparse
import ast
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import sys
import threading
import time
import traceback
from memory_lifecycle import memory_snapshot
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
OUT = Path('/home/ubuntu/m347_asset_memory_evidence_01/result.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name+'.part')
    with part.open('wb') as f:
        f.write((json.dumps(value, indent=2)+'\n').encode('utf-8')); f.flush(); os.fsync(f.fileno())
    os.replace(part, path)


def original_order(source):
    tree = ast.parse(source)
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('RUNTIME_BUNDLE_SHA','PILLOW_WHEEL_SHA'):
                    values[target.id] = ast.literal_eval(node.value)
    inspect = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='inspect')
    assign = next(n for n in inspect.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='expected' for t in n.targets))
    assert isinstance(assign.value, ast.Dict)
    items = []
    for key, value in zip(assign.value.keys, assign.value.values):
        name = ast.literal_eval(key)
        digest = values[value.id] if isinstance(value, ast.Name) else ast.literal_eval(value)
        items.append((name, digest))
    # inspect also checks candidate manifest after the fixed expected dictionary.
    items.append(('candidate_manifest', None))
    return items


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('manifest_sha'); args=parser.parse_args()
    if OUT.exists(): raise RuntimeError('Immutable result exists; collection only')
    result = dict(status='FAIL', gate_level='asset-hash-memory-diagnostic', build_id='0x4D395832',
                  errors=[], files=[], observations=[], overlay_loaded=False, model_forward_calls=0,
                  fpga_transactions=0, numerical_pass=False, performance_pass=False,
                  formal_promotion_allowed=False, cache_control='Natural existing cache; no cache clearing/advice/trim/GC; not a cold-start experiment',
                  budget_seconds=300, memory_capacity_proven=False,
                  prior_raw_sha256='cc04ea32daba54878a4ac0f63a7cd990db36e67d745c1e696adb806fd60e086a')
    stopped = threading.Event(); phase=['prerequisites']; lock=None; started=time.monotonic()
    def heartbeat():
        while not stopped.wait(30): print('M347_HEARTBEAT phase='+phase[0]+' elapsed_s='+str(round(time.monotonic()-started,1)), flush=True)
    threading.Thread(target=heartbeat,daemon=True).start()
    def observation(name):
        m=memory_snapshot()
        io={}
        for line in Path('/proc/self/io').read_text(encoding='utf-8').splitlines():
            k, _, v=line.partition(':'); io[k]=int(v)
        value=dict(name=name,elapsed_s=time.monotonic()-started,memory=m,process_io=io)
        result['observations'].append(value)
        return value
    try:
        if os.geteuid()!=0: raise RuntimeError('Same-terminal root required')
        manifest_path=HERE/'PACKAGE_MANIFEST.json'
        if sha(manifest_path)!=args.manifest_sha: raise RuntimeError('Package identity differs')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        expected={i['path'] for i in manifest['files']}
        actual={p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p!=manifest_path}
        if actual!=expected or len(expected)!=manifest['file_count']: raise RuntimeError('Whitelist/count differs')
        if sum(i['bytes'] for i in manifest['files'])!=manifest['total_bytes']: raise RuntimeError('Package byte count differs')
        for row in manifest['files']:
            p=(HERE/row['path']).resolve(); p.relative_to(HERE)
            if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']: raise RuntimeError('Package payload differs')
        result['manifest_sha256']=args.manifest_sha
        plan=json.loads((HERE/'ASSET_PLAN.json').read_text(encoding='utf-8'))
        if result['prior_raw_sha256']!=plan['prior_raw_sha256']: raise RuntimeError('Wrong prerequisite in frozen plan')
        if sha(Path('/home/ubuntu/m346_load_memory_evidence_01/load-memory.json'))!=plan['prior_raw_sha256']:
            raise RuntimeError('Exact predecessor board bytes differ')
        lock=os.open('/tmp/tellme_kv260_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',8001))
        for proc in Path('/proc').iterdir():
            if proc.name.isdigit() and int(proc.name)!=os.getpid():
                try: cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8',errors='replace')
                except (OSError,PermissionError): continue
                if any(x in cmd for x in ('m254_video_server.py','m276_m254_video_server.py','m333_video_server.py')):
                    raise RuntimeError('Project server is active: '+proc.name)
        source=RELEASE/'scripts/preflight.py'; config_path=RELEASE/'configs/deployment.example.json'
        if sha(source)!=plan['source_sha256'] or sha(config_path)!=plan['config_sha256']: raise RuntimeError('Original source/config drift')
        if sha(RELEASE/'INSTALL_PACKAGE_MANIFEST.json')!='fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e': raise RuntimeError('Installed manifest drift')
        spec=importlib.util.spec_from_file_location('original_release_preflight',source)
        original=importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
        config=json.loads(config_path.read_text(encoding='utf-8'))
        paths=original.required_paths(config)
        order=original_order(source.read_text(encoding='utf-8'))
        derived=[dict(name=n,path=paths[n].relative_to(RELEASE).as_posix(),sha256=h) for n,h in order]
        if derived!=plan['files']: raise RuntimeError('Exact original inspect path/order differs')
        ready=json.loads(paths['candidate_ready'].read_text(encoding='utf-8'))
        if sha(paths['candidate_ready'])!=plan['candidate_ready_sha256']: raise RuntimeError('Original ready evidence drift')
        expected_hashes=[h if h is not None else ready['package_manifest_sha256'] for _,h in order]
        # Stat every asset before hashing: bounded regular paths, no device/symlink reads.
        total=0; identities=[]
        for item in derived:
            p=RELEASE/item['path']; s=p.stat()
            if p.is_symlink() or not stat.S_ISREG(s.st_mode) or p.resolve()!=p or s.st_size>2*(1<<30):
                raise RuntimeError('Nonregular/escaped/oversized asset')
            p.relative_to(RELEASE); total+=s.st_size
            identities.append(dict(bytes=s.st_size,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),device=s.st_dev,inode=s.st_ino))
        if total>8*(1<<30): raise RuntimeError('Asset byte budget exceeded')
        result['planned_files']=len(derived); result['planned_asset_bytes']=total; result['euid']=os.geteuid()
        result['initial']=observation('before-original-asset-inspect')
        boot=Path('/boot/firmware/boot.scr.uimg'); boot_before=sha(boot)
        cmd_before=Path('/proc/cmdline').read_text(encoding='utf-8')
        digest=original.digest
        def observed_digest(path):
            index=len(result['files'])
            if time.monotonic()-started>300: raise RuntimeError('Bounded PS-only read budget exceeded before next asset')
            if index>=len(derived) or path!=RELEASE/derived[index]['path']: raise RuntimeError('Unexpected/duplicate asset hash call')
            phase[0]=derived[index]['name']
            before=observation('before:'+phase[0]); got=digest(path); after=observation('after:'+phase[0])
            row=dict(index=index,**derived[index],identity=identities[index],actual_sha256=got,
                     expected_sha256=expected_hashes[index],before=before,after=after,
                     cma_delta_bytes=after['memory']['system_bytes']['CmaFree']-before['memory']['system_bytes']['CmaFree'],
                     cached_delta_bytes=after['memory']['system_bytes']['Cached']-before['memory']['system_bytes']['Cached'],
                     rss_delta_bytes=after['memory']['process_bytes']['VmRSS']-before['memory']['process_bytes']['VmRSS'],
                     physical_read_bytes_delta=after['process_io']['read_bytes']-before['process_io']['read_bytes'])
            result['files'].append(row); atomic(OUT.parent/'progress.json',result)
            print('M347_ASSET '+json.dumps({k:row[k] for k in ('index','name','cma_delta_bytes','cached_delta_bytes','rss_delta_bytes','physical_read_bytes_delta')})+
                  ' cma_free_bytes='+str(after['memory']['system_bytes']['CmaFree']),flush=True)
            if got!=expected_hashes[index]: raise RuntimeError('Asset identity mismatch: '+phase[0])
            return got
        original.digest=observed_digest
        result['release_preflight']=original.inspect(config,port_check=True)
        if result['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT' or len(result['files'])!=len(derived): raise RuntimeError('Incomplete original asset inspect')
        result['final']=observation('after-original-asset-inspect')
        result['boot_unchanged']=sha(boot)==boot_before
        result['cmdline_unchanged']=Path('/proc/cmdline').read_text(encoding='utf-8')==cmd_before
        result['forbidden_imports']=[n for n in ('pynq','torch','board_runtime','video_server') if n in sys.modules]
        result['device_fds']=[]
        for fd in Path('/proc/self/fd').iterdir():
            try: target=os.readlink(fd)
            except FileNotFoundError: continue
            if target.startswith(('/dev/mem','/dev/uio','/dev/dri/')): result['device_fds'].append(target)
        if result['forbidden_imports'] or result['device_fds'] or not result['boot_unchanged'] or not result['cmdline_unchanged']: raise RuntimeError('Diagnostic scope violated')
        result['status']='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC'
    except BaseException as exc:
        result['errors'].append(type(exc).__name__+': '+str(exc)); result['traceback']=traceback.format_exc()
    finally:
        result['elapsed_s_diagnostic_not_performance']=time.monotonic()-started
        result['next_step']='Interpret per-file memory observations only; video CMA failure remains; no E2E/performance unlocked'
        atomic(OUT,result); raw=OUT.read_bytes(); print('M347_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
        chunks=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        for i,b in enumerate(chunks): print('M347_RESULT_CHUNK='+str(i)+'/'+str(len(chunks))+':'+base64.b64encode(b).decode(),flush=True)
        print('M347_SUMMARY='+json.dumps(dict(status=result['status'],errors=result['errors'])),flush=True)
        stopped.set()
        if lock is not None: os.close(lock)
    return 0 if result['status']=='PASS_ASSET_HASH_MEMORY_DIAGNOSTIC' else 1


if __name__=='__main__': raise SystemExit(main())
