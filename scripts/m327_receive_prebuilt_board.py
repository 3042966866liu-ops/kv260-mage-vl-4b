#!/usr/bin/env python3
"""Extract one hash-locked prebuilt archive to a new, independent KV260 path."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import subprocess
import tarfile


DEST = Path('/home/ubuntu/tellme_release_install_20260926')
TEMP_ADDRESS = '192.168.0.2/24'
PEER = '192.168.0.10'
PORT = 49328


class HashingReader:
    def __init__(self, source):
        self.source = source
        self.h = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        block = self.source.read(size)
        self.h.update(block)
        self.count += len(block)
        return block


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--expected-bytes', type=int, required=True)
    p.add_argument('--expected-manifest-sha256', required=True)
    args = p.parse_args()
    if os.geteuid() != 0 or DEST.exists() or len(args.expected_sha256) != 64:
        raise RuntimeError('root, clean destination and exact archive identity required')
    free = shutil.disk_usage('/home/ubuntu').free
    if free < 4_500_000_000:
        raise RuntimeError(f'insufficient independent install space: {free}')
    before = subprocess.check_output(['ip', '-4', '-o', 'addr', 'show', 'dev', 'eth0'], text=True)
    if TEMP_ADDRESS.split('/')[0] in before:
        raise RuntimeError('temporary address already present')
    added = False
    try:
        subprocess.run(['ip', 'addr', 'add', TEMP_ADDRESS, 'dev', 'eth0'], check=True)
        added = True
        DEST.mkdir(parents=True)
        count = 0
        with socket.create_connection((PEER, PORT), timeout=30) as conn:
            conn.settimeout(600)
            with conn.makefile('rb') as source:
                reader = HashingReader(source)
                with tarfile.open(mode='r|', fileobj=reader) as tar:
                    for member in tar:
                        rel = PurePosixPath(member.name)
                        if (not member.isfile() or rel.is_absolute() or '..' in rel.parts or
                            not rel.parts or member.size > 4_500_000_000):
                            raise RuntimeError(f'unsafe tar member: {member.name}')
                        target = DEST.joinpath(*rel.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with tar.extractfile(member) as inp, target.open('xb') as out:
                            shutil.copyfileobj(inp, out, length=4 << 20)
                        if target.stat().st_size != member.size:
                            raise RuntimeError(f'extracted size mismatch: {member.name}')
                        count += 1
                while reader.read(4 << 20):
                    pass
        if reader.count != args.expected_bytes or reader.h.hexdigest() != args.expected_sha256:
            raise RuntimeError(f'archive identity mismatch: {reader.count} {reader.h.hexdigest()}')
        manifest = DEST / 'INSTALL_PACKAGE_MANIFEST.json'
        with manifest.open('rb') as f:
            actual_manifest = hashlib.sha256(f.read()).hexdigest()
        if actual_manifest != args.expected_manifest_sha256:
            raise RuntimeError('installed manifest identity mismatch')
        verifier = DEST / 'scripts/verify_prebuilt_package.py'
        result = subprocess.run(['/usr/local/share/pynq-venv/bin/python3', str(verifier)],
                                cwd=DEST, check=False)
        if result.returncode != 0:
            raise RuntimeError('installed file verification failed')
        record = {'status': 'PASS_INSTALLED_FILES_NOT_YET_EXECUTED',
                  'directory': str(DEST), 'archive_sha256': args.expected_sha256,
                  'manifest_sha256': actual_manifest, 'tar_members': count}
        (DEST / 'INSTALL_BOARD_RESULT.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        print('M327_PREBUILT_INSTALL_FILES_PASS', flush=True)
    finally:
        if added:
            subprocess.run(['ip', 'addr', 'del', TEMP_ADDRESS, 'dev', 'eth0'], check=True)


if __name__ == '__main__':
    main()
