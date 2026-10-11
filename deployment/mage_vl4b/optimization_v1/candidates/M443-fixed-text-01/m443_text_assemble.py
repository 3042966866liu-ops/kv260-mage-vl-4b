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
 print('M443T_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
SOURCES=[('/home/ubuntu/m441_fixed_text_candidate_09', '6311242d1659ec4ca8ef3faf2c0cc3d8c6f6028ea97de25e5c5974bb9b84afc6'), ('/home/ubuntu/m443_single_layer_candidate_01', 'db646a370a63b0520cbf9cdd56bfad6bb09f448b06935ba8011a1d0a42ad77ec'), ('/home/ubuntu/m443_candidate_01', '6b1942e566e78d229f0c62a69d3a1b05c00bce474fff314ecedfe014a65e50f8')]
PROOFS=[('/home/ubuntu/m443_single_layer_evidence_01/B1/load-memory.json', '5737bce9f3fd47a618d8bc0d1c67263972187ba2e4aad2cf75382fa3090af2b4'), ('/home/ubuntu/m443_board_evidence_01/BuildID/BOARD_RESULT.json', '403b8549a7ea6444b89cedd551ed553ba32b8d9c93caedde9c187fc7347a3599'), ('/home/ubuntu/m443_board_evidence_01/Chain/BOARD_RESULT.json', 'e3d0bbf6e1c16c2d5d7d3efecc479093919ea8a800e702a3823b906dc0ff416b')]
if __name__=='__main__':main(sys.argv[1])
