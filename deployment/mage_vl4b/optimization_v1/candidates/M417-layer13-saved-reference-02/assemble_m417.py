"""Hash-bound copies from one exact previously verified packet; no model imports."""
import hashlib,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m417_layer13_reference_candidate_01')
OLD_SHA='6b3969356ba876630ffd67fa276dd21ec1a14c5cc302a56e3888fce7baa70afc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if os.geteuid()!=0:raise RuntimeError('Root assembly required')
if len(sys.argv)!=2 or sha(HERE/'PACKAGE_MANIFEST.json')!=sys.argv[1]:raise RuntimeError('Target manifest differs')
if sha(OLD/'PACKAGE_MANIFEST.json')!=OLD_SHA:raise RuntimeError('Old manifest differs')
old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes());oldrows={r['path']:r for r in old['files']}
new=json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes())
for r in old['files']:
    p=OLD/r['path']
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Old packet drift')
for r in new['files']:
    name=r['path']
    if Path(name).name!=name:raise RuntimeError('Plain whitelist filename required')
    p=HERE/name
    if not p.exists():
        if name not in oldrows or oldrows[name]!=r:raise RuntimeError('Missing delta payload')
        part=p.with_suffix(p.suffix+'.assembly-part')
        with part.open('xb') as f:f.write((OLD/name).read_bytes());f.flush();os.fsync(f.fileno())
        os.replace(part,p)
    if p.is_symlink() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError('Target packet drift')
    print('M417_ASSEMBLED_FILE '+name+' '+r['sha256'],flush=True)
allowed={'PACKAGE_MANIFEST.json'}|{r['path'] for r in new['files']}
if {p.name for p in HERE.iterdir()}!=allowed:raise RuntimeError('Unexpected staging files')
print('M417_ASSEMBLY_PASS '+sys.argv[1]+' '+str(new['file_count'])+' '+str(new['total_bytes']),flush=True)
