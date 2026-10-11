#!/usr/bin/env python3
"""Stream an exact, recoverable old-Qwen directory backup to one PC peer.

No deletion occurs here. The temporary IPv4 address is removed in finally.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tarfile
import time


SOURCE = Path('/home/ubuntu/tellme_qwen25_7b')
TEMP_ADDRESS = '192.168.0.2/24'
PEER = '192.168.0.10'
PORT = 49327


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest():
    if SOURCE.resolve() != SOURCE or not SOURCE.is_dir() or SOURCE.is_symlink():
        raise RuntimeError('exact backup source not available')
    entries = []
    for path in sorted(SOURCE.rglob('*')):
        if path.is_symlink():
            raise RuntimeError(f'symlink not permitted: {path}')
        if path.is_file():
            entries.append({'path': path.relative_to(SOURCE).as_posix(),
                            'bytes': path.stat().st_size, 'sha256': digest(path)})
        elif not path.is_dir():
            raise RuntimeError(f'unsupported file type: {path}')
    if len(entries) != 62:
        raise RuntimeError(f'old-7B file count changed: {len(entries)}')
    return {'schema': 'm327-old7b-backup-v1', 'source': str(SOURCE),
            'file_count': len(entries), 'total_bytes': sum(x['bytes'] for x in entries),
            'files': entries}


class SocketWriter:
    def __init__(self, sock):
        self.sock = sock
        self.bytes_sent = 0

    def write(self, data):
        self.sock.sendall(data)
        self.bytes_sent += len(data)
        return len(data)

    def flush(self):
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--peer', default=PEER)
    p.add_argument('--port', type=int, default=PORT)
    args = p.parse_args()
    if os.geteuid() != 0 or args.peer != PEER or args.port != PORT:
        raise RuntimeError('requires root and exact approved peer/port')
    data = manifest()
    encoded = (json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n').encode()
    before = subprocess.check_output(['ip', '-4', '-o', 'addr', 'show', 'dev', 'eth0'], text=True)
    if TEMP_ADDRESS.split('/')[0] in before:
        raise RuntimeError('temporary address already present; refusing to alter it')
    added = False
    try:
        subprocess.run(['ip', 'addr', 'add', TEMP_ADDRESS, 'dev', 'eth0'], check=True)
        added = True
        with socket.create_connection((args.peer, args.port), timeout=30) as sock:
            sock.settimeout(600)
            sock.sendall(struct.pack('!Q', len(encoded)))
            sock.sendall(encoded)
            writer = SocketWriter(sock)
            with tarfile.open(mode='w|', fileobj=writer, format=tarfile.PAX_FORMAT) as tar:
                for item in data['files']:
                    path = SOURCE / item['path']
                    if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
                        raise RuntimeError(f'source changed before send: {item["path"]}')
                    info = tar.gettarinfo(str(path), arcname='tellme_qwen25_7b/' + item['path'])
                    if not info.isfile():
                        raise RuntimeError('source changed type')
                    with path.open('rb') as f:
                        tar.addfile(info, f)
            print(json.dumps({'status': 'SENT_NOT_YET_VERIFIED', 'manifest_sha256':
                              hashlib.sha256(encoded).hexdigest(), 'tar_bytes': writer.bytes_sent,
                              'source_bytes': data['total_bytes'], 'file_count': data['file_count']}), flush=True)
            print('M327_OLD7B_SENT_NOT_YET_VERIFIED', flush=True)
    finally:
        if added:
            subprocess.run(['ip', 'addr', 'del', TEMP_ADDRESS, 'dev', 'eth0'], check=True)


if __name__ == '__main__':
    main()
