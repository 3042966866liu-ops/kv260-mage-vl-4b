#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 q=argparse.ArgumentParser();q.add_argument('--root',type=Path,required=True);q.add_argument('--expected-manifest-sha256',required=True);a=q.parse_args();mp=a.root/'PACKAGE_MANIFEST.json'
 if sha256(mp)!=a.expected_manifest_sha256:raise RuntimeError('M198 manifest hash mismatch')
 m=json.loads(mp.read_text());expected={x['path'] for x in m['files']}|{'PACKAGE_MANIFEST.json'};actual={x.name for x in a.root.iterdir() if x.is_file()}
 if m.get('gate')!='M198-M197-FP32-block-PS-vision-bootstrap' or m.get('status')!='PASS' or actual!=expected:raise RuntimeError('M198 identity/closure mismatch')
 for x in m['files']:
  p=a.root/x['path']
  if p.stat().st_size!=x['bytes'] or sha256(p)!=x['sha256']:raise RuntimeError(f"M198 member mismatch: {x['path']}")
 print('M198_BOOTSTRAP_VERIFY_PASS');return 0
if __name__=='__main__':raise SystemExit(main())
