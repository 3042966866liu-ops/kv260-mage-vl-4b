import ast
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
out=base/'candidates/OP01-REPLAY-01'
names=['board_decode_replay.py','run_board_replay.sh','measurement.py','op01_support.py','board_safety.py',
       'decode_checkpoint.py','decode_trace.py','decode_diagnostic.py','decode_io_trace.py','transfer_trace.py','summarize_decode_trace.py']
mapping={n:Path(__file__).with_name(n) for n in names}
for name in ('op00_stable_probe.py','m120_board_common.py','sys_config.json'):
    mapping[name]=base/'candidates/OP01-SYS-05'/name
mapping['checkpoint_plan.json']=base/'runs/OP01-checkpoint-preflight-01/plan.json'
for name,path in mapping.items():
    if name.endswith('.py'):ast.parse(path.read_text())
out.mkdir(exist_ok=False)
for name,path in mapping.items():(out/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(out.iterdir())]
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
print(json.dumps(dict(package=str(out),manifest_sha256=sha256(out/'PACKAGE_MANIFEST.json'),files=len(rows))))
