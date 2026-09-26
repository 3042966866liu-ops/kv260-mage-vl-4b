#!/usr/bin/env python3
"""Verify every first-install payload file against INSTALL_PACKAGE_MANIFEST.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    manifest_path = ROOT / 'INSTALL_PACKAGE_MANIFEST.json'
    if not manifest_path.is_file():
        print('BLOCKED: no first-install package manifest', file=sys.stderr)
        return 2
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    if data.get('schema') != 'kv260-mage-vl-4b-prebuilt-install-v1' or data.get('build_id') != '0x4D395832':
        print('BLOCKED: package identity mismatch', file=sys.stderr)
        return 2
    entries = data.get('files', [])
    if data.get('file_count') != len(entries) or data.get('total_bytes') != sum(e['bytes'] for e in entries):
        print('BLOCKED: package manifest counts mismatch', file=sys.stderr)
        return 2
    seen = set()
    problems = []
    for entry in entries:
        rel = entry['path']
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or rel in seen:
            problems.append(f'unsafe or duplicate path: {rel}')
            continue
        seen.add(rel)
        target = ROOT / path
        if target.is_symlink() or not target.is_file():
            problems.append(f'missing or symlink: {rel}')
        elif target.stat().st_size != entry['bytes'] or sha256(target) != entry['sha256']:
            problems.append(f'identity mismatch: {rel}')
    if problems:
        print(json.dumps({'status': 'FAIL', 'problems': problems}, indent=2))
        return 2
    print(json.dumps({'status': 'PASS_PACKAGE_FILES', 'build_id': data['build_id'],
                      'file_count': len(entries), 'payload_bytes': data['total_bytes']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
