"""Manifest-first assembly only from one exact previously verified package."""
import hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m423_integrated_video_candidate_01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if len(sys.argv)!=2 or sha(HERE/'PACKAGE_MANIFEST.json')!=sys.argv[1]:raise RuntimeError('Exact new manifest required')
    if sha(OLD/'PACKAGE_MANIFEST.json')!='46bdb383609d5eeb30f6f4962cbb476f20e1ec52c9f5030a97bbf7077dd52495':raise RuntimeError('Old manifest differs')
    old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes());oldrows={r['path']:r for r in old['files']}
    m=json.loads((HERE/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:
        name=row['path']
        if Path(name).name!=name:raise RuntimeError('Flat whitelist required')
        p=HERE/name
        if not p.exists():
            if oldrows.get(name)!=row or sha(OLD/name)!=row['sha256']:raise RuntimeError('Missing new payload; cannot synthesize')
            shutil.copyfile(OLD/name,p)
        if p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Assembled file differs')
    if {p.name for p in HERE.iterdir()}!={r['path'] for r in m['files']}|{'PACKAGE_MANIFEST.json'} or len(m['files'])!=m['file_count'] or sum(r['bytes'] for r in m['files'])!=m['total_bytes']:raise RuntimeError('Closure differs')
    print('M425_ASSEMBLY_PASS',sys.argv[1],m['file_count'],m['total_bytes'])
if __name__=='__main__':main()
