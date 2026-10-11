"""Assemble pinned identical helper bytes from existing M363; no gate execution."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zlib
import os
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
        if not target.exists() and row['path'] in ('VIDEO_EXPECTED.json','VISUAL_EXPECTED.json'):
            compressed=ROOT/(row['path']+'.zlib')
            compressed_row=next(r for r in new['files'] if r['path']==compressed.name)
            if sha(compressed)!=compressed_row['sha256'] or compressed.stat().st_size!=compressed_row['bytes']:raise RuntimeError('Compressed reference identity differs')
            decoder=zlib.decompressobj();raw=decoder.decompress(compressed.read_bytes(),row['bytes']+1)
            if len(raw)!=row['bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('Reference expansion bounds/SHA differs')
            temporary=target.with_name(target.name+'.expand-part')
            with temporary.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,target)
        if not target.exists():
            srcrow=bysha.get(row['sha256'])
            if srcrow is None:raise RuntimeError('New payload missing')
            src=OLD/srcrow['path']
            if sha(src)!=row['sha256']:raise RuntimeError('Prior payload differs')
            shutil.copyfile(src,target)
        if target.stat().st_size!=row['bytes'] or sha(target)!=row['sha256']:raise RuntimeError('Assembled payload differs')
    if {p.name for p in ROOT.iterdir()}!={x['path'] for x in new['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
    print('M368_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
