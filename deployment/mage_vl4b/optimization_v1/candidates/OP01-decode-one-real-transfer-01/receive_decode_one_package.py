"""One pinned experimental package, bounded LAN transfer, no overlay loading."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import time

BASE = Path('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1')
TARGET = BASE / 'OP01-decode-one-real-chain-01'
PARTIAL = BASE / 'OP01-decode-one-real-chain-01.partial'
ADDRESS = '192.168.0.2/24'
MAGIC = b'OP01_DECODE_ONE_PACKAGE_V1\n'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def exact(sock, size):
    data = b''
    while len(data) < size:
        block = sock.recv(size-len(data))
        if not block: raise RuntimeError('Early EOF')
        data += block
    return data


def unpack(archive, destination, members):
    expected = {x['path']: x for x in members}
    if len(expected) != len(members): raise ValueError('Duplicate expected member')
    with tarfile.open(archive, 'r:') as tar:
        entries = tar.getmembers()
        if len(entries) != len(expected) or {x.name for x in entries} != set(expected):
            raise ValueError('Archive whitelist mismatch')
        for item in entries:
            row = expected[item.name]
            path = (destination / item.name).resolve()
            path.relative_to(destination.resolve())
            if not item.isfile() or item.size != row['bytes']:
                raise ValueError('Invalid archive member')
            path.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with tar.extractfile(item) as source, path.open('xb') as target:
                for block in iter(lambda: source.read(1024*1024), b''):
                    target.write(block); h.update(block)
            if h.hexdigest() != row['sha256']: raise ValueError('Extracted hash mismatch')


def main():
    import fcntl
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract-sha256', required=True)
    args = parser.parse_args()
    contract_path = Path(__file__).with_name('TRANSFER_CONTRACT.json')
    if digest(contract_path) != args.contract_sha256: raise RuntimeError('Contract identity mismatch')
    contract = json.loads(contract_path.read_text())
    if contract['package_manifest_sha256'] != 'fa0254f5050f251ed72cb6f417bc0860e6cf1e9eed8b64bde3f32519744ac525':
        raise RuntimeError('Not the authorized candidate package')
    size = contract['archive_bytes']
    if not 0 < size < 64*1024*1024: raise RuntimeError('Transfer size outside bound')
    result_path = BASE / 'results/decode_one_real_transfer01.json'
    archive = BASE / 'transfers/decode_one_real_package01.tar'
    if any(p.exists() for p in (TARGET, PARTIAL, result_path, archive)):
        raise RuntimeError('Immutable transfer attempt already exists')
    result = dict(status='FAIL', overlay_loaded=False, errors=[])
    added, fd, connection = False, None, None
    try:
        if os.geteuid() != 0: raise RuntimeError('Root required for temporary address')
        fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if Path('/sys/class/net/eth0/carrier').read_text().strip() != '1':
            raise RuntimeError('Ethernet carrier absent')
        result['addresses_before'] = json.loads(subprocess.check_output(['ip','-j','address','show','dev','eth0'], text=True))
        result['routes_before'] = subprocess.check_output(['ip','-j','route'], text=True)
        addresses = result['addresses_before'][0]['addr_info']
        if not any(x.get('local') == '192.168.0.2' and x.get('prefixlen') == 24 for x in addresses):
            subprocess.run(['ip','address','add',ADDRESS,'dev','eth0'], check=True, timeout=5)
            added = True
        archive.parent.mkdir(parents=True, exist_ok=True)
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('192.168.0.2', 8769)); listener.listen(1); listener.settimeout(180)
            print('DECODE_ONE_RECEIVER_READY 192.168.0.2:8769', flush=True)
            connection, peer = listener.accept()
        connection.settimeout(30)
        if peer[0] != '192.168.0.10' or exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError('Peer/protocol mismatch')
        deadline, remaining = time.monotonic()+120, size
        with archive.open('xb') as stream:
            while remaining:
                if time.monotonic() > deadline: raise TimeoutError('Transfer total deadline')
                block = connection.recv(min(1024*1024, remaining))
                if not block: raise RuntimeError('Archive EOF')
                stream.write(block); remaining -= len(block)
            stream.flush(); os.fsync(stream.fileno())
        if digest(archive) != contract['archive_sha256']: raise RuntimeError('Archive SHA mismatch')
        PARTIAL.mkdir()
        unpack(archive, PARTIAL, contract['members'])
        if digest(PARTIAL / 'PACKAGE_MANIFEST.json') != contract['package_manifest_sha256']:
            raise RuntimeError('Extracted manifest mismatch')
        PARTIAL.rename(TARGET)
        result.update(status='PASS_TRANSFER_ONLY', package_manifest_sha256=contract['package_manifest_sha256'],
                      archive_sha256=contract['archive_sha256'], target=str(TARGET))
        connection.sendall(b'PINNED_PACKAGE_RECEIVED\n')
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if connection is not None: connection.close()
        if added:
            cleanup = subprocess.run(['ip','address','del',ADDRESS,'dev','eth0'], capture_output=True, text=True, timeout=5)
            result['address_cleanup_exit'] = cleanup.returncode
            if cleanup.returncode: result['status'] = 'FAIL'
        result['addresses_after'] = json.loads(subprocess.check_output(['ip','-j','address','show','dev','eth0'], text=True))
        result['routes_after'] = subprocess.check_output(['ip','-j','route'], text=True)
        if 'routes_before' in result and result['routes_after'] != result['routes_before']:
            result['status'] = 'FAIL'; result['errors'].append('Routes not restored')
        if fd is not None: os.close(fd)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        temp = result_path.with_suffix('.partial')
        temp.write_text(json.dumps(result, indent=2)+'\n'); temp.replace(result_path)
        print('DECODE_ONE_TRANSFER_JSON_BEGIN\n'+json.dumps(result)+'\nDECODE_ONE_TRANSFER_JSON_END', flush=True)
    return 0 if result['status'] == 'PASS_TRANSFER_ONLY' else 1


if __name__ == '__main__': raise SystemExit(main())
