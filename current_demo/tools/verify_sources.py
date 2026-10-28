"""Verify exported source identity only; never import project/hardware modules."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'SOURCE_MANIFEST.json').read_bytes());count=0;total=0
for row in m['files']:
    p=root/row['path'];assert p.resolve().is_relative_to(root)
    b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
    total+=len(b)
    if p.suffix=='.py':compile(b,str(p),'exec');count+=1
assert len(m['files'])==m['file_count'] and total==m['total_bytes']
print('PASS',m['file_count'],'original files;',count,'Python sources compiled; no board/model execution.')
