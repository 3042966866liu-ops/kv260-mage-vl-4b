#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path

def sha(path):
 d=hashlib.sha256();d.update(path.read_bytes());return d.hexdigest()

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--expected-manifest-sha256',required=True);a=p.parse_args()
mp=a.root/'PACKAGE_MANIFEST.json';m=json.loads(mp.read_text())
if sha(mp)!=a.expected_manifest_sha256:raise RuntimeError('M208 manifest hash mismatch')
expected={x['path']:x for x in m['files']};actual={str(x.relative_to(a.root)).replace('\\','/') for x in a.root.rglob('*') if x.is_file() and x.name!='PACKAGE_MANIFEST.json'}
if m.get('gate')!='M208-M207-FP32-W4-GEMM-bootstrap' or m.get('status')!='PASS' or actual!=set(expected):raise RuntimeError('M208 identity/closure mismatch')
for name,item in expected.items():
 path=a.root/name
 if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError(f'M208 member mismatch: {name}')
print('M208_BOOTSTRAP_VERIFY_PASS')

