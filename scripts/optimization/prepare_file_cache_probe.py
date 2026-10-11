import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-stage-transfer/attempt_01/result.json'
data=json.loads(source.read_text())['board_result']
rows=[r for r in data['records'] if r['family']=='gate_up' and r['repeat']==0 and r['mode']=='read_copy']
if len(rows)!=4 or not all(r['byte_exact'] for r in rows):raise RuntimeError('Missing verified real windows')
target=base/'runs/OP01-file-cache-probe-01/plan.json'
if target.exists():raise RuntimeError('Plan already frozen')
write_json(target,dict(source_sha256=sha256(source),layout_sha256=data['layout_manifest_sha256'],
    windows=[{k:r[k] for k in ('shard','offset','bytes','sha256')} for r in rows]))
print(sha256(target))
