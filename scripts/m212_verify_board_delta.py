#!/usr/bin/env python3
"""Verify the exact M212 COM3 delta closure."""
import argparse, hashlib, json
from pathlib import Path

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--expected-manifest-sha256',required=True); a=p.parse_args()
manifest_path=a.root/'PACKAGE_MANIFEST.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
if sha(manifest_path)!=a.expected_manifest_sha256: raise RuntimeError('M212 package manifest hash mismatch')
expected={item['path']:item for item in manifest['files']}
actual={str(path.relative_to(a.root)).replace('\\','/') for path in a.root.rglob('*') if path.is_file() and path.name!='PACKAGE_MANIFEST.json'}
if manifest.get('gate')!='M212-live-service-board-delta' or manifest.get('status')!='PASS' or actual!=set(expected): raise RuntimeError('M212 package identity/closure mismatch')
for name,item in expected.items():
 path=a.root/name
 if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']: raise RuntimeError(f'M212 member mismatch: {name}')
if any('__pycache__' in name or name.endswith('.pyc') or name.endswith('.log') for name in actual): raise RuntimeError('M212 forbidden cache/log member')
print('M212_BOARD_DELTA_VERIFY_PASS')
