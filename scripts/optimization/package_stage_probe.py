import ast
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2]
out=root/'deployment/mage_vl4b/optimization_v1/candidates/OP01-stage-01'
files=['stage_transfer_probe.py','run_stage_probe.sh']
ast.parse(Path(__file__).with_name(files[0]).read_text())
out.mkdir(exist_ok=False)
for name in files:(out/name).write_bytes(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(out.iterdir())]
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
print(sha256(out/'PACKAGE_MANIFEST.json'))
