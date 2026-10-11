#!/usr/bin/env python3
"""Receive and verify the exact M327 old-7B tar stream; do not delete source."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import tarfile


HOST = '192.168.0.10'
PORT = 49327
BOARD = '192.168.0.2'


def exact(sock, count):
    buf = bytearray()
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise EOFError('premature transfer EOF')
        buf.extend(chunk)
    return bytes(buf)


def hash_tar(archive, manifest):
    expected = {x['path']: x for x in manifest['files']}
    seen = set()
    with tarfile.open(archive, 'r:') as tar:
        for member in tar:
            prefix = 'tellme_qwen25_7b/'
            if not member.isfile() or not member.name.startswith(prefix):
                raise RuntimeError(f'unexpected tar member: {member.name}')
            rel = member.name[len(prefix):]
            if rel not in expected or rel in seen or member.size != expected[rel]['bytes']:
                raise RuntimeError(f'tar member mismatch: {rel}')
            h = hashlib.sha256()
            source = tar.extractfile(member)
            for block in iter(lambda: source.read(4 << 20), b''):
                h.update(block)
            if h.hexdigest() != expected[rel]['sha256']:
                raise RuntimeError(f'tar member hash mismatch: {rel}')
            seen.add(rel)
    if seen != set(expected):
        raise RuntimeError('tar file set mismatch')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directory', required=True, type=Path)
    args = p.parse_args()
    dest = args.directory.resolve()
    if dest.exists():
        p.error('refusing to overwrite backup directory')
    dest.mkdir(parents=True)
    archive = dest / 'tellme_qwen25_7b.tar'
    manifest_path = dest / 'SOURCE_MANIFEST.json'
    result_path = dest / 'BACKUP_RESULT.json'
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(600)
        print(f'M327_RECEIVER_READY {HOST}:{PORT}', flush=True)
        conn, address = server.accept()
        with conn:
            if address[0] != BOARD:
                raise RuntimeError(f'unexpected peer: {address[0]}')
            conn.settimeout(600)
            length = struct.unpack('!Q', exact(conn, 8))[0]
            if length > 1_000_000:
                raise RuntimeError('oversized manifest')
            raw = exact(conn, length)
            manifest = json.loads(raw)
            if (manifest.get('schema') != 'm327-old7b-backup-v1' or
                manifest.get('source') != '/home/ubuntu/tellme_qwen25_7b' or
                manifest.get('file_count') != 62):
                raise RuntimeError('unexpected source manifest')
            manifest_path.write_bytes(raw)
            h = hashlib.sha256()
            total = 0
            with archive.open('xb') as out:
                while True:
                    block = conn.recv(4 << 20)
                    if not block:
                        break
                    out.write(block)
                    h.update(block)
                    total += len(block)
            print(f'M327_RECEIVED_BYTES {total}', flush=True)
    hash_tar(archive, manifest)
    result = {'status': 'PASS_BACKUP_VERIFIED', 'source': manifest['source'],
              'archive': str(archive), 'archive_bytes': total, 'archive_sha256': h.hexdigest(),
              'manifest_sha256': hashlib.sha256(raw).hexdigest(),
              'file_count': manifest['file_count'], 'source_bytes': manifest['total_bytes']}
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    print('M327_BACKUP_VERIFIED_PASS', flush=True)


if __name__ == '__main__':
    main()
