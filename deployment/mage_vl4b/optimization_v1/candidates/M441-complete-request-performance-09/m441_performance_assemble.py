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
 old2=Path('/home/ubuntu/m366_staged_text_candidate_03')
 if sha(old2/'PACKAGE_MANIFEST.json')!='9434b439a23daa021c39086e43736b331225460eedaf261e2c70b3a6ff9545ca':raise RuntimeError('Pinned proven text package differs')
 source.update({r['sha256']:old2/r['path'] for r in json.loads((old2/'PACKAGE_MANIFEST.json').read_bytes())['files']})
 saved_layer=Path('/home/ubuntu/m441_single_layer_evidence_09/B1/load-memory.json')
 if sha(saved_layer)!='16b7aeb84dad97dbfbbdff06311becff9cf7866261316cc18dc296a97f0132e4':raise RuntimeError('Saved actual layer differs')
 source[sha(saved_layer)]=saved_layer
 old3=Path('/home/ubuntu/m432_late11_integrated_candidate_02')
 if sha(old3/'PACKAGE_MANIFEST.json')!='37579ee6572d076a547842ba868c04a3797dd2a0375724c2a6fce333a9b9a0ee':raise RuntimeError('Actual integrated source package differs')
 source.update({r['sha256']:old3/r['path'] for r in json.loads((old3/'PACKAGE_MANIFEST.json').read_bytes())['files']})
 saved_text=Path('/home/ubuntu/m441_fixed_text_evidence_09/B1/load-memory.json')
 if sha(saved_text)!='0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7':raise RuntimeError('Actual saved text differs')
 source[sha(saved_text)]=saved_text
 old4=Path('/home/ubuntu/m437_natural_IO_candidate_01')
 if sha(old4/'PACKAGE_MANIFEST.json')!='4ef52185d86e3b489f6a6d68afee4632964c5bb3f36cb5518ad779b9c39155d3':raise RuntimeError('Actual M437 package differs')
 source.update({r['sha256']:old4/r['path'] for r in json.loads((old4/'PACKAGE_MANIFEST.json').read_bytes())['files']})
 saved_video=Path('/home/ubuntu/m441_fixed_video_evidence_09/BOARD_RESULT.json')
 if sha(saved_video)!='defbb0fd59e9139e1f6c267a78aa066d25a19708c1e4a075032415b7b3ae95e8':raise RuntimeError('Actual saved video differs')
 source[sha(saved_video)]=saved_video



 for row in data['files']:
  if '/' in row['path'] or '\\' in row['path']:raise RuntimeError('Flat whitelist required')
  p=ROOT/row['path']
  if not p.exists():
   src=source.get(row['sha256'])
   if src is None or sha(src)!=row['sha256']:raise RuntimeError('Missing exact reused payload')
   shutil.copyfile(src,p)
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Payload changed')
 if {p.name for p in ROOT.iterdir()}!={r['path'] for r in data['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
 print('M441P_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
