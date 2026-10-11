"""One approved pinned LAN transfer, isolated install, automatic address cleanup."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
from decoder_dependency import NAME, SHA, SIZE, MAGIC, exact
from measurement import sha256, write_json

ROOT = Path('/home/ubuntu/tellme_m120_m89x2_20260901')
BASE = ROOT / 'optimization_v1'
PYTHON = '/usr/local/share/pynq-venv/bin/python'
ADDRESS = '192.168.0.2/24'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    manifest = here / 'PACKAGE_MANIFEST.json'
    if sha256(manifest) != args.manifest_sha256:
        raise RuntimeError('Bootstrap manifest changed')
    rows = json.loads(manifest.read_text())['files']
    if {p.name for p in here.iterdir()} != {r['path'] for r in rows} | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Bootstrap closure mismatch')
    for row in rows:
        p = (here / row['path']).resolve()
        p.relative_to(here)
        if sha256(p) != row['sha256'] or p.stat().st_size != row['bytes']:
            raise RuntimeError('Bootstrap file mismatch')
    target = BASE / 'dependencies/opencv411_arm64_v1'
    partial = BASE / 'dependencies/opencv411_arm64_v1.partial'
    output = BASE / 'results/decoder_dependency01.json'
    if output.exists() or target.exists() or partial.exists():
        raise RuntimeError('Immutable install attempt already exists')
    result = dict(status='FAIL', scope='isolated decoder provision, not model inference',
                  overlay_loaded=False, stable_runtime_modified=False, errors=[])
    start = time.perf_counter()
    fd, connection, added = None, None, False
    try:
        if os.geteuid() != 0:
            raise RuntimeError('Authorized root required')
        fd = os.open('/tmp/tellme_kv260_execution.lock',os.O_RDWR|os.O_CREAT,0o600)
        fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        if Path('/sys/class/net/eth0/carrier').read_text().strip() != '1':
            raise RuntimeError('Ethernet carrier absent')
        before = subprocess.check_output(['ip','-j','address','show','dev','eth0'], text=True)
        result['address_before'] = json.loads(before)
        result['route_before'] = subprocess.check_output(['ip','-j','route'],text=True)
        addresses = result['address_before'][0]['addr_info']
        if not any(x.get('local')=='192.168.0.2' and x['prefixlen']==24 for x in addresses):
            subprocess.run(['ip','address','add',ADDRESS,'dev','eth0'],check=True,timeout=5)
            added=True
        if shutil.disk_usage(BASE).free < 512*1024*1024:
            raise RuntimeError('Less than512MiB free for isolated dependency')
        partial.mkdir(parents=True)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(('192.168.0.2',8769)); listener.listen(1); listener.settimeout(180)
            print('OP00_DECODER_RECEIVER_READY 192.168.0.2:8769',flush=True)
            connection,peer=listener.accept()
        connection.settimeout(120)
        if peer[0]!='192.168.0.10' or exact(connection,len(MAGIC))!=MAGIC:
            raise RuntimeError('Peer/protocol mismatch')
        size=struct.unpack('!I',exact(connection,4))[0]
        if size>1024:
            raise RuntimeError('Metadata oversized')
        metadata=json.loads(exact(connection,size))
        if metadata != dict(name=NAME,bytes=SIZE,sha256=SHA):
            raise RuntimeError('Wheel identity mismatch')
        wheel=partial/NAME
        remaining=SIZE
        with wheel.open('xb') as stream:
            while remaining:
                data=connection.recv(min(1024*1024,remaining))
                if not data: raise RuntimeError('Wheel EOF')
                stream.write(data); remaining-=len(data)
            stream.flush(); os.fsync(stream.fileno())
        if sha256(wheel)!=SHA:
            raise RuntimeError('Wheel hash mismatch')
        connection.sendall(b'PINNED_WHEEL_RECEIVED\n')
        connection.close(); connection=None
        print('OP00_DECODER_WHEEL_SHA_PASS',flush=True)
        site=partial/'site'
        install=subprocess.run([PYTHON,'-m','pip','install','--no-index','--no-deps','--no-cache-dir',
            '--no-compile','--target',str(site),str(wheel)],capture_output=True,text=True,timeout=300)
        result['pip_output']=install.stdout+install.stderr
        if install.returncode:
            raise RuntimeError('Isolated decoder pip failed: '+str(install.returncode))
        # Fingerprint every installed file; never alter or upgrade M190 dependencies.
        files=[dict(path=p.relative_to(partial).as_posix(),bytes=p.stat().st_size,sha256=sha256(p))
               for p in sorted(site.rglob('*')) if p.is_file()]
        write_json(partial/'INSTALLED_MANIFEST.json',dict(files=files,file_count=len(files),wheel_sha256=SHA))
        partial.rename(target)
        env=os.environ.copy()
        env.update(PYTHONPATH=str(target/'site')+':'+str(ROOT/'m190_mage_runtime'),
                   PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
        probe=BASE/'OP00-import-decode-01'
        # No model/device is active; let the child acquire its own exclusive lock.
        os.close(fd)
        fd=None
        run=subprocess.run([PYTHON,str(probe/'op00_import_decode_probe.py'),
            '--manifest-sha256','762f3a26e3c82c3ae1b61b282ea398c9754859d220c9a2bbe9f25d6b232b84d3',
            '--result',str(BASE/'results/import_decode02.json')],env=env,text=True,capture_output=True,timeout=120)
        result['probe_output']=run.stdout+run.stderr
        result['probe_exit_code']=run.returncode
        if run.returncode:
            raise RuntimeError('Installed decoder raw-input probe failed')
        result['probe']=json.loads((BASE/'results/import_decode02.json').read_text())
        result.update(status='PASS',wheel_sha256=SHA,isolated_site=str(target/'site'),
            installed_manifest_sha256=sha256(target/'INSTALLED_MANIFEST.json'),installed_file_count=len(files))
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if connection is not None: connection.close()
        if added:
            cleanup=subprocess.run(['ip','address','del',ADDRESS,'dev','eth0'],capture_output=True,text=True,timeout=5)
            result['temporary_address_cleanup_exit']=cleanup.returncode
            if cleanup.returncode:
                result['status']='FAIL'; result['errors'].append('Temporary address cleanup failed')
        result['address_after']=json.loads(subprocess.check_output(['ip','-j','address','show','dev','eth0'],text=True))
        result['route_after']=subprocess.check_output(['ip','-j','route'],text=True)
        if result.get('route_before')!=result['route_after']:
            result['status']='FAIL';result['errors'].append('Network routes not restored')
        if fd is not None: os.close(fd)
        result['elapsed_s']=time.perf_counter()-start
        write_json(output,result)
        print('OP00_DECODER_JSON_BEGIN',flush=True)
        print(json.dumps(result,allow_nan=False),flush=True)
        print('OP00_DECODER_JSON_END',flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
