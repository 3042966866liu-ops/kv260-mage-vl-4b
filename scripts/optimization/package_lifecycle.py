"""Freeze isolated lifecycle candidate; never alter existing REPLAY01 package."""
import ast
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
prior=base/'candidates/OP01-REPLAY-01'
manifest=json.loads((prior/'PACKAGE_MANIFEST.json').read_text())
mapping={r['path']:prior/r['path'] for r in manifest['files']}
for row in manifest['files']:
    if sha256(mapping[row['path']])!=row['sha256']:raise RuntimeError('Prior package changed')
for name in ('board_decode_replay.py','lifecycle_experiment.py','lifecycle_trial.py','lifecycle_reads.py',
             'memory_lifecycle.py','video_contract_v2.py','sys_video_input.py'):
    mapping[name]=Path(__file__).with_name(name)
mapping['lifecycle_read_plan.json']=base/'runs/OP01-lifecycle-read-plan/plan.json'
out=base/'candidates/OP01-LIFECYCLE-01'
for name,path in mapping.items():
    if name.endswith('.py'):ast.parse(path.read_text())
out.mkdir(exist_ok=False)
for name,path in mapping.items():(out/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(out.iterdir())]
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
print(json.dumps(dict(files=len(rows),bytes=sum(r['bytes'] for r in rows),manifest_sha256=sha256(out/'PACKAGE_MANIFEST.json'))))
