"""Frozen release bootstrap before any third-party import; retain -I isolation."""
import hashlib,json,runpy,sys
from pathlib import Path
assert sys.flags.isolated
here=Path(__file__).resolve().parent
reuse=Path('/home/ubuntu/m368_staged_video_candidate_03')
if hashlib.sha256((reuse/'PACKAGE_MANIFEST.json').read_bytes()).hexdigest()!='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66':raise RuntimeError('Reused bootstrap manifest differs')
for row in json.loads((reuse/'PACKAGE_MANIFEST.json').read_bytes())['files']:
    p=reuse/row['path']
    if p.is_symlink() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Bootstrap payload differs')
sys.path[:0]=[str(here),str(reuse)]
from frozen_video_identity import module_paths
sys.path[:0]=[str(p) for p in module_paths()]
sys.argv=[str(here/'m441_video_gate.py')]+sys.argv[1:]
runpy.run_path(str(here/'m441_video_gate.py'),run_name='__main__')
