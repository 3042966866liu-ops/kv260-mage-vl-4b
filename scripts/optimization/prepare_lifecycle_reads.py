import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-full-file-scan/attempt_01/board_result.json'
assert sha256(source)=='1b5fe81a4fc17c57a6f0f93a2c6f51866193f147790839315750eb906791de4b'
data=json.loads(source.read_text())
assert data['status']=='MEASURED' and len(data['windows'])==648
rows=[]
for i,row in enumerate(data['windows']):
    first,second=(p['records'][i] for p in data['passes'])
    assert first['index']==second['index']==i and first['sha256']==second['sha256']
    rows.append(dict(**row,sha256=first['sha256']))
out=base/'runs/OP01-lifecycle-read-plan/plan.json'
if out.exists():raise RuntimeError('Immutable plan exists')
write_json(out,dict(source_sha256=sha256(source),windows=rows,passes=2,
    total_bytes_per_pass=sum(r['bytes'] for r in rows),classification='Preparation plan, not new measurement'))
print('LIFECYCLE_READ_PLAN_READY '+sha256(out))
