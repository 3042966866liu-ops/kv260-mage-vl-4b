"""Reuse exact prior diagnostic payloads by SHA into a new whitelist directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

PRIOR=Path('/home/ubuntu/m362_common_load_observer_01')
TARGET=Path('/home/ubuntu/m363_common_load_observer_01')
PRIOR_SHA='f3d4d12125ae1a7a0ca79d388c0eee505afdac9de0a8c5279847594534c1d9fd'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def assemble():
    if os.geteuid()!=0:raise RuntimeError('Root required')
    expected=sys.argv[1]
    if sha(TARGET/'PACKAGE_MANIFEST.json')!=expected or sha(PRIOR/'PACKAGE_MANIFEST.json')!=PRIOR_SHA:raise RuntimeError('Exact manifests differ')
    old=json.loads((PRIOR/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));new=json.loads((TARGET/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    by_sha={}
    for row in old['files']:
        source=(PRIOR/row['path']).resolve();source.relative_to(PRIOR)
        if source.stat().st_size!=row['bytes'] or sha(source)!=row['sha256']:raise RuntimeError('Prior source identity differs')
        by_sha[row['sha256']]=source
    expected_paths={row['path'] for row in new['files']}|{'PACKAGE_MANIFEST.json'}
    for row in new['files']:
        if Path(row['path']).name!=row['path']:raise RuntimeError('Flat new whitelist required')
        target=TARGET/row['path']
        if not target.exists():
            source=by_sha.get(row['sha256'])
            if source is None:raise RuntimeError('New delta payload not uploaded: '+row['path'])
            shutil.copyfile(source,target)
        if target.stat().st_size!=row['bytes'] or sha(target)!=row['sha256']:raise RuntimeError('New target identity differs')
    if {p.name for p in TARGET.iterdir()}!=expected_paths or len(new['files'])!=new['file_count'] or sum(x['bytes'] for x in new['files'])!=new['total_bytes']:raise RuntimeError('Whitelist/count/bytes differs')
    print('M363_ASSEMBLY_PASS manifest_sha256='+expected+' files='+str(new['file_count'])+' bytes='+str(new['total_bytes']),flush=True)

if __name__=='__main__':assemble()
