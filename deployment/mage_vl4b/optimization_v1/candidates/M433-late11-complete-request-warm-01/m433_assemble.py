"""Whitelisted same-SHA immutable source copy; no model, board or external assets."""
import hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m432_late11_integrated_candidate_02')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
expected='37579ee6572d076a547842ba868c04a3797dd2a0375724c2a6fce333a9b9a0ee'
if sha(OLD/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Old immutable packet identity differs')
original=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
for row in original['files']:
    p=OLD/row['path']
    if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Old payload differs')
m=json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes());byname={r['path']:r for r in original['files']}
for r in m['files']:
    p=HERE/r['path']
    if '/' in r['path'] or '\\' in r['path'] or Path(r['path']).name!=r['path']:raise RuntimeError('Path outside flat whitelist')
    if not p.exists():
        if byname.get(r['path'])!=r:raise RuntimeError('Missing changed file cannot reuse old source')
        shutil.copyfile(OLD/r['path'],p)
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Final payload differs')
names={x['path'] for x in m['files']}
if len(names)!=m['file_count'] or sum(r['bytes'] for r in m['files'])!=m['total_bytes'] or {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Final exact closure differs')
if len(sys.argv)!=2 or sha(HERE/'PACKAGE_MANIFEST.json')!=sys.argv[1]:raise RuntimeError('Manifest argument differs')
print('M433_ASSEMBLY_PASS',sys.argv[1],m['file_count'],m['total_bytes'])
