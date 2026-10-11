"""Copy missing identical dependencies from an exact frozen prior package."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
HERE=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m387_ps_video_candidate_01')
OLD_SHA='2613ed813ca8d873076b0a6443309242f9c0594e655e57dcfe4d1859839f4fbb'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main(expected):
    if sha(HERE/'PACKAGE_MANIFEST.json')!=expected or sha(OLD/'PACKAGE_MANIFEST.json')!=OLD_SHA:raise RuntimeError('Manifest identity differs')
    manifest=json.loads((HERE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    prior={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    secondary=Path('/home/ubuntu/m381_gate_up_performance_candidate_01')
    if sha(secondary/'PACKAGE_MANIFEST.json')!='d81b0bab5dea4eee0452e9815f6308fc7eedb283dfc6ec25f3b03da4e4ff1e82':raise RuntimeError('Secondary manifest differs')
    second={r['path']:r for r in json.loads((secondary/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    names=set()
    for row in manifest['files']:
        name=row['path']
        if Path(name).name!=name or name in names:raise RuntimeError('Whitelist violation')
        names.add(name);path=HERE/name
        if not path.exists():
            if prior.get(name)==row:source=OLD/name
            elif second.get(name)==row:source=secondary/name
            else:raise RuntimeError('New payload missing')
            if sha(source)!=row['sha256'] or source.stat().st_size!=row['bytes']:raise RuntimeError('Prior source differs')
            shutil.copyfile(source,path)
        if sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise RuntimeError('Payload differs')
    if len(names)!=manifest['file_count'] or sum(r['bytes'] for r in manifest['files'])!=manifest['total_bytes']:raise RuntimeError('Count/byte mismatch')
    if {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Extra files')
    print('M388_ASSEMBLY_SHA_PASS',expected,manifest['file_count'],manifest['total_bytes'],flush=True)
if __name__=='__main__':main(sys.argv[1])
