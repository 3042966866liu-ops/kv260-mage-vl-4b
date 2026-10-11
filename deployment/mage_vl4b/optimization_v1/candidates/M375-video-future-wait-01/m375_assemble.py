import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m369_light_video_candidate_01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
    if sha(ROOT/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Manifest differs')
    if sha(OLD/'PACKAGE_MANIFEST.json')!='dc22fc6c4e8718832877640f7cd768dda12bf63c8e057239ad1fa902295fdd73':raise RuntimeError('Prior identity differs')
    new=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    bysha={r['sha256']:r for r in old['files']}
    for row in new['files']:
        if '/' in row['path'] or chr(92) in row['path']:raise RuntimeError('Flat whitelist')
        target=ROOT/row['path']
        if not target.exists():
            source=bysha.get(row['sha256'])
            if source is None:raise RuntimeError('Missing new payload')
            p=OLD/source['path']
            if sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise RuntimeError('Prior payload differs')
            shutil.copyfile(p,target)
        if sha(target)!=row['sha256'] or target.stat().st_size!=row['bytes']:raise RuntimeError('Payload differs')
    if {p.name for p in ROOT.iterdir()}!={r['path'] for r in new['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
    print('M375_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
