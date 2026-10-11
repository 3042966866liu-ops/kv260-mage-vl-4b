#!/usr/bin/env python3
"""Remove only the user-authorized old Qwen 7B directory after verified backup."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


SOURCE = Path('/home/ubuntu/tellme_qwen25_7b')
STABLE = Path('/home/ubuntu/tellme_m120_m89x2_20260901')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--expected-source-manifest-sha256', required=True)
    p.add_argument('--verified-archive-sha256', required=True)
    args = p.parse_args()
    if os.geteuid() != 0 or SOURCE.resolve() != SOURCE or SOURCE.is_symlink() or not SOURCE.is_dir():
        raise RuntimeError('exact root-owned old-7B source check failed')
    if not STABLE.is_dir() or SOURCE == STABLE or STABLE in SOURCE.parents:
        raise RuntimeError('stable Mage-VL directory safety check failed')
    if len(args.verified_archive_sha256) != 64 or len(args.expected_source_manifest_sha256) != 64:
        raise RuntimeError('backup hash argument missing')
    processes = subprocess.check_output(['ps', '-eo', 'args'], text=True)
    for line in processes.splitlines():
        if str(SOURCE) in line and 'm327_remove_verified_old7b_board.py' not in line:
            raise RuntimeError('old-7B path still referenced by a process')
    entries = []
    for path in sorted(SOURCE.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('symlink appeared in old-7B source')
        if path.is_file():
            entries.append({'path': path.relative_to(SOURCE).as_posix(),
                            'bytes': path.stat().st_size, 'sha256': digest(path)})
        elif not path.is_dir():
            raise RuntimeError('unsupported file appeared in old-7B source')
    data = {'schema': 'm327-old7b-backup-v1', 'source': str(SOURCE),
            'file_count': len(entries), 'total_bytes': sum(x['bytes'] for x in entries),
            'files': entries}
    encoded = (json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n').encode()
    observed = hashlib.sha256(encoded).hexdigest()
    if len(entries) != 62 or observed != args.expected_source_manifest_sha256:
        raise RuntimeError('source changed since verified backup')
    shutil.rmtree(SOURCE)
    print(json.dumps({'status': 'REMOVED_AFTER_VERIFIED_BACKUP', 'path': str(SOURCE),
                      'file_count': len(entries), 'source_bytes': data['total_bytes'],
                      'source_manifest_sha256': observed,
                      'backup_archive_sha256': args.verified_archive_sha256}), flush=True)
    print('M327_OLD7B_REMOVE_PASS', flush=True)


if __name__ == '__main__':
    main()
