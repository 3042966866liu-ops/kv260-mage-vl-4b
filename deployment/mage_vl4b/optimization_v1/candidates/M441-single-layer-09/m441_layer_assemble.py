import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
 m=ROOT/'PACKAGE_MANIFEST.json'
 if sha(m)!=expected:raise RuntimeError('Manifest differs')
 data=json.loads(m.read_text(encoding='utf-8'))
 old=Path('/home/ubuntu/m363_common_load_observer_01')
 if sha(old/'PACKAGE_MANIFEST.json')!='006dff41790e8adda44c85a3b93383b93e7089243a6079f88de397f2a48e6b74':raise RuntimeError('Pinned old package differs')
 source={r['sha256']:old/r['path'] for r in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']}
 saved=Path('/home/ubuntu/m441_board_evidence_01/Compare/BOARD_RESULT.json')
 if sha(saved)!='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d':raise RuntimeError('Saved original compare differs')
 source[sha(saved)]=saved
 for row in data['files']:
  if '/' in row['path'] or '\\' in row['path']:raise RuntimeError('Flat whitelist required')
  p=ROOT/row['path']
  if not p.exists():
   src=source.get(row['sha256'])
   if src is None or sha(src)!=row['sha256']:raise RuntimeError('Missing exact reused payload')
   shutil.copyfile(src,p)
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Payload changed')
 if {p.name for p in ROOT.iterdir()}!={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
 print('M441L_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
