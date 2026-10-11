"""Clean SYS05 staging using hash-verified unchanged SYS04 members."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if digest(Path(__file__))!=sys.argv[1]:raise RuntimeError('Stager identity mismatch')
root=Path('/home/ubuntu/tellme_m120_m89x2_20260901/optimization_v1')
old=root/'OP01-SYS-04';new=root/'OP01-SYS-05'
incoming=Path('/home/ubuntu/sys05_delta')
manifest=incoming/'PACKAGE_MANIFEST.json'
if digest(manifest)!=sys.argv[2]:raise RuntimeError('Target manifest mismatch')
data=json.loads(manifest.read_text());rows=data['files']
if len(rows)!=data['file_count'] or sum(r['bytes'] for r in rows)!=data['total_bytes']:raise RuntimeError('Manifest totals')
sources=[]
for row in rows:
    name=row['path']
    if Path(name).name!=name:raise RuntimeError('Non-flat package path')
    src=incoming/name if name=='transfer_trace.py' else old/name
    if src.is_symlink() or src.stat().st_size!=row['bytes'] or digest(src)!=row['sha256']:
        raise RuntimeError('Source identity mismatch: '+name)
    sources.append((src,name))
new.mkdir(exist_ok=False)
for src,name in sources:shutil.copyfile(src,new/name)
shutil.copyfile(manifest,new/'PACKAGE_MANIFEST.json')
for row in rows:
    if digest(new/row['path'])!=row['sha256']:raise RuntimeError('Destination identity mismatch')
print('SYS05_DELTA_STAGE_PASS files='+str(len(rows))+' manifest='+digest(new/'PACKAGE_MANIFEST.json'))
