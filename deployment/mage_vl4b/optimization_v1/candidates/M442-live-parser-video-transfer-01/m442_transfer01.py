"""Bounded specific-peer artifact transfer only; never runs FPGA/model code."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import socket
import struct
import subprocess
import time

MAGIC=b'TELLME_M441_V1\n'
BOARD='192.168.0.2';PC='192.168.0.10';PORT=8777
DESTINATION=Path('/home/ubuntu/m442_live_parser_video_01')
EVIDENCE=Path('/home/ubuntu/m442_live_parser_video_transfer_evidence_01')

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):digest.update(block)
    return digest.hexdigest()

def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.partial')
    with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)

def encoded(value):return (json.dumps(value,ensure_ascii=True,indent=2)+'\n').encode('utf-8')

def export_saved():
    if os.geteuid()!=0:raise RuntimeError('Root required for transfer evidence export')
    raw=(EVIDENCE/'RESULT.json').read_bytes();result=json.loads(raw)
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M441_TRANSFER_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i,part in enumerate(parts):
        print('M441_TRANSFER_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'),flush=True)
    return 0 if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY' else 1

def valid_entries(spec):
    rows=spec['files']
    if not isinstance(rows,list) or not 1<=len(rows)<=128 or spec['file_count']!=len(rows):raise ValueError('File count differs')
    if len({r['path'] for r in rows})!=len(rows):raise ValueError('Duplicate member')
    for row in rows:
        name=row['path'];parts=PurePosixPath(name).parts
        if not isinstance(name,str) or name.startswith('/') or '\\' in name or ':' in name or not parts or any(p in ('','..','.','__pycache__') for p in parts) or name!=PurePosixPath(name).as_posix() or name.endswith(('.pyc','.partial','.log')):raise ValueError('Unsafe member path')
        if type(row['bytes']) is not int or not 0<=row['bytes']<=128<<20 or len(row['sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['sha256']):raise ValueError('Unsafe member identity')
    total=sum(r['bytes'] for r in rows)
    if not 0<total<=256<<20 or spec['total_bytes']!=total:raise ValueError('Byte count differs')
    return rows

def verify_directory(directory,digest,manifest_name='PACKAGE_MANIFEST.json'):
    manifest=directory/manifest_name
    if sha(manifest)!=digest:raise ValueError('Exact manifest SHA differs')
    spec=json.loads(manifest.read_text(encoding='utf-8'));rows=valid_entries(spec)
    expected={r['path'] for r in rows}
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p!=manifest}
    if expected!=actual:raise ValueError('Exact directory whitelist differs')
    for r in rows:
        path=directory/r['path'];path.resolve().relative_to(directory.resolve())
        if path.is_symlink() or path.stat().st_size!=r['bytes'] or sha(path)!=r['sha256']:raise ValueError('Exact member SHA differs')
    return spec

def exact(stream,count,deadline):
    if not 0<=count<=1<<20:raise ValueError('Read allocation bound')
    data=bytearray(count);view=memoryview(data);offset=0
    while offset<count:
        if time.monotonic()>deadline:raise TimeoutError('Total transfer budget exceeded')
        seen=stream.recv_into(view[offset:])
        if not seen:raise EOFError('Transfer EOF')
        offset+=seen
    return bytes(data)

def ip_json(*args):
    result=subprocess.run(['ip','-j',*args],check=True,capture_output=True,text=True,encoding='utf-8',timeout=10)
    return json.loads(result.stdout)

def default_routes():return ip_json('route','show','default')

def receive(bootstrap,digest):
    if os.geteuid()!=0:raise RuntimeError('Root required')
    verify_directory(bootstrap,digest)
    transport_raw=(bootstrap/'TRANSPORT_MANIFEST.json').read_bytes();transport=json.loads(transport_raw);rows=valid_entries(transport)
    if transport['schema']!='m441-specific-peer-transfer-v1':raise ValueError('Transport schema differs')
    if EVIDENCE.exists() or DESTINATION.exists() or DESTINATION.with_name(DESTINATION.name+'.transfer-partial').exists():raise RuntimeError('Existing transfer/destination; collect only')
    EVIDENCE.mkdir(mode=0o700)
    result=dict(status='FAIL_M441_ARTIFACT_TRANSFER',board_gate_executed=False,overlay_loaded=False,fpga_transactions=0,
        bootstrap_manifest_sha256=digest,transport_manifest_sha256=hashlib.sha256(transport_raw).hexdigest(),package_manifest_sha256=transport['package_manifest_sha256'],errors=[],added_address=False,temporary_address_restored=False,files=[])
    started=time.monotonic();deadline=started+600;added=False;staging=DESTINATION.with_name(DESTINATION.name+'.transfer-partial')
    before=routes_before=None
    try:
        if Path('/sys/class/net/eth0/carrier').read_text(encoding='utf-8').strip()!='1':raise RuntimeError('Ethernet carrier absent')
        before=ip_json('addr','show','dev','eth0');routes_before=default_routes()
        result['addresses_before']=before;result['default_routes_before']=routes_before
        present=any(a.get('local')==BOARD and a.get('prefixlen')==24 for link in before for a in link['addr_info'])
        if not present:
            if any(a.get('local')==BOARD for link in before for a in link['addr_info']):raise RuntimeError('Existing address prefix differs')
            subprocess.run(['ip','addr','add',BOARD+'/24','dev','eth0'],check=True,timeout=10);added=True;result['added_address']=True
        if default_routes()!=routes_before:raise RuntimeError('Default routes changed')
        if shutil.disk_usage(DESTINATION.parent).free<transport['total_bytes']+(128<<20):raise MemoryError('Disk reserve insufficient')
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.bind((BOARD,PORT));listener.listen(1);listener.settimeout(120)
            print('M441_RECEIVER_READY bind='+BOARD+' peer='+PC+' port='+str(PORT),flush=True)
            connection,peer=listener.accept()
        with connection:
            connection.settimeout(20)
            if peer[0]!=PC or exact(connection,len(MAGIC),deadline)!=MAGIC:raise ValueError('Specific peer/protocol differs')
            size=struct.unpack('!I',exact(connection,4,deadline))[0]
            if not 0<size<=1<<20 or exact(connection,size,deadline)!=transport_raw:raise ValueError('Frozen transport bytes differ')
            staging.mkdir(mode=0o700)
            for row in rows:
                size=struct.unpack('!H',exact(connection,2,deadline))[0]
                if not 0<size<=512:raise ValueError('Path frame bound')
                name=exact(connection,size,deadline).decode('utf-8');count=struct.unpack('!Q',exact(connection,8,deadline))[0]
                if name!=row['path'] or count!=row['bytes']:raise ValueError('Member order/identity differs')
                path=staging/name;path.parent.mkdir(parents=True,exist_ok=True);part=path.with_name(path.name+'.partial')
                digest_member=hashlib.sha256()
                with part.open('xb') as out:
                    remaining=count
                    while remaining:
                        block=exact(connection,min(1<<20,remaining),deadline);out.write(block);digest_member.update(block);remaining-=len(block)
                    out.flush();os.fsync(out.fileno())
                if digest_member.hexdigest()!=row['sha256'] or sha(part)!=row['sha256']:raise ValueError('Received SHA differs')
                os.replace(part,path);result['files'].append(row)
                print('M441_RECEIVED_MEMBER '+name+' bytes='+str(count),flush=True)
            if exact(connection,2,deadline)!=b'\0\0':raise ValueError('Final protocol marker differs')
            verify_directory(staging,transport['package_manifest_sha256']);os.replace(staging,DESTINATION)
            result['status']='PASS_M441_ARTIFACT_TRANSFER_ONLY'
            response=encoded(dict(status='PASS',package_manifest_sha256=transport['package_manifest_sha256']));connection.sendall(struct.pack('!I',len(response))+response)
    except BaseException as exc:result['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        if added:
            try:subprocess.run(['ip','addr','del',BOARD+'/24','dev','eth0'],check=True,timeout=10)
            except BaseException as exc:result['errors'].append('Temporary address cleanup: '+str(exc))
        if before is not None:
            try:
                after=ip_json('addr','show','dev','eth0');result['addresses_after']=after;result['default_routes_after']=default_routes()
                # Exact original address identities; dynamic lifetime countdowns
                # are not configuration changes.
                def identities(links):return sorted((a['family'],a['local'],a['prefixlen']) for link in links for a in link['addr_info'])
                result['temporary_address_restored']=identities(after)==identities(before) and result['default_routes_after']==routes_before
                if not result['temporary_address_restored']:result['errors'].append('Original network identity not restored')
            except BaseException as exc:result['errors'].append('Network readback: '+str(exc))
        if result['errors'] or not result['temporary_address_restored']:result['status']='FAIL_M441_ARTIFACT_TRANSFER'
        result['elapsed_s']=time.monotonic()-started
        atomic(EVIDENCE/'RESULT.json',encoded(result))
        export_saved()
    return 0 if result['status']=='PASS_M441_ARTIFACT_TRANSFER_ONLY' else 1

def send(candidate,digest,transport_path,result_path):
    if result_path.exists():raise RuntimeError('Existing sender result; inspect only')
    verify_directory(candidate,digest)
    raw=transport_path.read_bytes();spec=json.loads(raw);rows=valid_entries(spec)
    if spec['schema']!='m441-specific-peer-transfer-v1' or spec['package_manifest_sha256']!=digest:raise ValueError('Frozen transport identity differs')
    expected=[dict(path='PACKAGE_MANIFEST.json',bytes=(candidate/'PACKAGE_MANIFEST.json').stat().st_size,sha256=digest)]+json.loads((candidate/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']
    if rows!=expected:raise ValueError('Manifest-first exact transfer whitelist differs')
    started=time.monotonic();deadline=started+600
    result=dict(status='FAIL_M441_SENDER',specific_peer=BOARD,specific_source=PC,port=PORT,package_manifest_sha256=digest,transport_manifest_sha256=hashlib.sha256(raw).hexdigest(),files=[],errors=[],board_gate_executed=False)
    try:
        with socket.create_connection((BOARD,PORT),timeout=20,source_address=(PC,0)) as connection:
            connection.settimeout(20);connection.sendall(MAGIC+struct.pack('!I',len(raw))+raw)
            for row in rows:
                path=candidate/row['path'];before=path.stat();name=row['path'].encode('utf-8')
                if len(name)>512:raise ValueError('Member path too long')
                connection.sendall(struct.pack('!H',len(name))+name+struct.pack('!Q',row['bytes']))
                digest_sent=hashlib.sha256();count=0
                with path.open('rb') as f:
                    for block in iter(lambda:f.read(1<<20),b''):
                        if time.monotonic()>deadline:raise TimeoutError('Total send budget exceeded')
                        connection.sendall(block);digest_sent.update(block);count+=len(block)
                after=path.stat()
                if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or count!=row['bytes'] or digest_sent.hexdigest()!=row['sha256']:raise ValueError('Sent member identity/SHA changed')
                result['files'].append(row);print('M441_SENT_MEMBER '+row['path'],flush=True)
            connection.sendall(b'\0\0');size=struct.unpack('!I',exact(connection,4,deadline))[0]
            if not 0<size<=1<<20:raise ValueError('Response bound')
            response=json.loads(exact(connection,size,deadline));result['receiver_response']=response
            if response.get('status')!='PASS' or response.get('package_manifest_sha256')!=digest:raise ValueError('Receiver response rejected')
            result['status']='PASS_SPECIFIC_PEER_PAYLOAD_SENT_ONLY'
    except BaseException as exc:result['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        result['elapsed_s']=time.monotonic()-started;atomic(result_path,encoded(result));print(json.dumps(result),flush=True)
    return 0 if result['status']=='PASS_SPECIFIC_PEER_PAYLOAD_SENT_ONLY' else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['receive','send','collect']);ap.add_argument('directory',type=Path);ap.add_argument('manifest_sha');ap.add_argument('--transport',type=Path);ap.add_argument('--result',type=Path);a=ap.parse_args()
    if a.mode=='collect':
        verify_directory(a.directory.resolve(),a.manifest_sha)
        export_saved();raise SystemExit(0)
    if a.mode=='send':
        if a.transport is None or a.result is None:raise RuntimeError('Frozen transport/result required')
        raise SystemExit(send(a.directory.resolve(),a.manifest_sha,a.transport,a.result))
    raise SystemExit(receive(a.directory.resolve(),a.manifest_sha))
