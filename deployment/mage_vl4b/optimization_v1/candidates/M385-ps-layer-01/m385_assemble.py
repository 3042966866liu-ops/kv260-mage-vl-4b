"""Copy missing identical dependencies from an exact frozen prior package."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m384_ps_chain_candidate_01')
OLD_SHA='0b5996c5029d3a33da1c54c1e2e1d471a04259f5683cda463a450cfe84b1d4d3'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main(expected):
    if sha(HERE/'PACKAGE_MANIFEST.json')!=expected or sha(OLD/'PACKAGE_MANIFEST.json')!=OLD_SHA:raise RuntimeError('Manifest identity differs')
    manifest=json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    prior={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    names=set()
    for row in manifest['files']:
        name=row['path']
        if Path(name).name!=name or name in names:raise RuntimeError('Whitelist violation')
        names.add(name);path=HERE/name
        if not path.exists():
            if name not in prior or prior[name]!=row:raise RuntimeError('New payload missing')
            source=OLD/name
            if sha(source)!=row['sha256'] or source.stat().st_size!=row['bytes']:raise RuntimeError('Prior source differs')
            shutil.copyfile(source,path)
        if sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise RuntimeError('Payload differs')
    if len(names)!=manifest['file_count'] or sum(r['bytes'] for r in manifest['files'])!=manifest['total_bytes']:raise RuntimeError('Count/byte mismatch')
    if {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Extra files')
    print('M385_ASSEMBLY_SHA_PASS',expected,manifest['file_count'],manifest['total_bytes'],flush=True)
if __name__=='__main__':main(sys.argv[1])
