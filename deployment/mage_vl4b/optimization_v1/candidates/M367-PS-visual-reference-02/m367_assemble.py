"""Assemble pinned identical helper bytes from existing M363; no gate execution."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m366_staged_text_candidate_03')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
    manifest=ROOT/'PACKAGE_MANIFEST.json'
    if sha(manifest)!=expected:raise RuntimeError('Manifest differs')
    new=json.loads(manifest.read_text());old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text())
    if sha(OLD/'PACKAGE_MANIFEST.json')!='9434b439a23daa021c39086e43736b331225460eedaf261e2c70b3a6ff9545ca':raise RuntimeError('Prior package differs')
    bysha={x['sha256']:x for x in old['files']}
    for row in new['files']:
        if '/' in row['path'] or '\\' in row['path']:raise RuntimeError('Flat whitelist required')
        target=ROOT/row['path']
        if not target.exists():
            srcrow=bysha.get(row['sha256'])
            if srcrow is None:raise RuntimeError('New payload missing')
            src=OLD/srcrow['path']
            if sha(src)!=row['sha256']:raise RuntimeError('Prior payload differs')
            shutil.copyfile(src,target)
        if target.stat().st_size!=row['bytes'] or sha(target)!=row['sha256']:raise RuntimeError('Assembled payload differs')
    if {p.name for p in ROOT.iterdir()}!={x['path'] for x in new['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
    print('M367_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
