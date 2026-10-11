"""Assemble frozen bytes from previously verified board packages/results only."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
 if os.geteuid()!=0 or sha(ROOT/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Root/exact manifest required')
 source={}
 for directory,digest in SOURCES:
  d=Path(directory);m=d/'PACKAGE_MANIFEST.json'
  if sha(m)!=digest:raise RuntimeError('Pinned source manifest changed')
  for row in json.loads(m.read_bytes())['files']:
   p=d/row['path']
   if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Pinned source member changed')
   source[row['sha256']]=p
 for path,digest in PROOFS:
  p=Path(path)
  if sha(p)!=digest:raise RuntimeError('Actual board proof changed')
  source[digest]=p
 data=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_bytes())
 for row in data['files']:
  if '/' in row['path'] or '\\' in row['path']:raise RuntimeError('Flat whitelist required')
  p=ROOT/row['path']
  if not p.exists():
   q=source.get(row['sha256'])
   if q is None or sha(q)!=row['sha256']:raise RuntimeError('Missing frozen source member')
   shutil.copyfile(q,p)
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Assembled member differs')
 if {p.name for p in ROOT.iterdir()}!={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist changed')
 print('M443P_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
SOURCES=[('/home/ubuntu/m441_complete_request_candidate_17', '7871bdfc31c78ac6ee9d5844813de886e7a5fde91ad43208bc141dc12ac655fb'), ('/home/ubuntu/m443_fixed_video_candidate_01', '35f57f99ae2923fbfd8c10c422b4377fcbbb552f1e4268ddba96857e44ffecf8')]
PROOFS=[('/home/ubuntu/m443_fixed_video_evidence_01/BOARD_RESULT.json', 'daa74aebef873ebcce6e27a4b7c4cc7ac31a0f1327de0fa12cda15c86d6af731')]
if __name__=='__main__':main(sys.argv[1])
