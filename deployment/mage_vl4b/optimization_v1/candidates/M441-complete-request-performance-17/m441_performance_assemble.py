import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
 assert sha(ROOT/'PACKAGE_MANIFEST.json')==expected
 old=Path('/home/ubuntu/m441_complete_request_candidate_15')
 assert sha(old/'PACKAGE_MANIFEST.json')=='2eb2836acef1106a2afa980416d0201a07423516893a6f0897974e07cebf265c'
 om=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes());sources={}
 for r in om['files']:
  p=old/r['path'];assert not p.is_symlink() and sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];sources[r['sha256']]=p
 data=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_bytes())
 for r in data['files']:
  assert '/' not in r['path'] and '\\' not in r['path']
  p=ROOT/r['path']
  if not p.exists():
   q=sources[r['sha256']];assert sha(q)==r['sha256'];shutil.copyfile(q,p)
  assert not p.is_symlink() and sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
 assert {p.name for p in ROOT.iterdir()}=={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}
 print('M44117_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
