import ast
import json
from pathlib import Path
import urllib.request
from decoder_dependency import NAME, SHA, SIZE, URL
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
downloads = BASE / 'dependencies'
downloads.mkdir(exist_ok=True)
wheel = downloads / NAME
if not wheel.exists():
    partial = wheel.with_suffix('.download')
    with urllib.request.urlopen(URL, timeout=30) as source, partial.open('xb') as target:
        size = 0
        while True:
            data = source.read(1024 * 1024)
            if not data:
                break
            size += len(data)
            if size > SIZE:
                raise RuntimeError('Dependency oversized')
            target.write(data)
    if partial.stat().st_size != SIZE or sha256(partial) != SHA:
        raise RuntimeError('Downloaded wheel identity mismatch')
    partial.rename(wheel)
if wheel.stat().st_size != SIZE or sha256(wheel) != SHA:
    raise RuntimeError('Pinned dependency changed')
output = BASE / 'candidates/OP00-decoder-dependency-01'
mapping = {name: Path(__file__).with_name(name) for name in ('decoder_dependency.py',
    'install_decoder_dependency.py', 'measurement.py', 'run_decoder_dependency.sh')}
for name, source in mapping.items():
    if name.endswith('.py'):
        ast.parse(source.read_text())
output.mkdir(exist_ok=False)
for name, source in mapping.items():
    (output / name).write_bytes(source.read_bytes().replace(b'\r\n',b'\n'))
rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in sorted(output.iterdir())]
write_json(output / 'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows)))
write_json(downloads / 'decoder_provenance.json',dict(name=NAME,url=URL,sha256=SHA,bytes=SIZE,
    metadata_source='https://pypi.org/pypi/opencv-python-headless/4.11.0.86/json',
    requires_numpy_for_python310='>=1.21.2; existing 1.26.4 retained', install='isolated --no-deps --no-index'))
print(json.dumps(dict(wheel=str(wheel),bytes=SIZE,sha256=SHA,bootstrap=str(output),manifest_sha256=sha256(output/'PACKAGE_MANIFEST.json'))))
