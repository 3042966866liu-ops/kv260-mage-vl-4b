"""Package stable-only load/restore probe with unchanged hardware prerequisites."""
import ast
import argparse
import json
from pathlib import Path
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b'
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', choices=('01', '02', '03'), required=True)
args = parser.parse_args()
output = BASE / f'optimization_v1/candidates/OP00-stable-probe-{args.attempt}'
art = BASE / 'm120_m89x2_board_candidate'
expected_manifest = '88c532e286fe0ef5df2d02b9f96726a3ff5e5527b3da4b03a28c6e7dc91048ba'
if sha256(art / 'ARTIFACT_MANIFEST.json') != expected_manifest:
    raise RuntimeError('Stable artifact manifest changed')
for row in json.loads((art / 'ARTIFACT_MANIFEST.json').read_text()):
    path = art / row['path']
    if path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
        raise RuntimeError('Stable artifact changed')
evidence = []
for name in ('M130_M120_NUMERICAL_CSIM_RESULT.json', 'M134_M120_RTL_COSIM_GATE_RESULT.json',
             'M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json'):
    path = BASE / name
    data = json.loads(path.read_text())
    if not data['status'].startswith('PASS'):
        raise RuntimeError('Existing hardware prerequisite not PASS')
    evidence.append({'path': str(path.relative_to(ROOT)), 'sha256': sha256(path), 'status': data['status']})
mapping = {name: Path(__file__).with_name(name) for name in
           ('op00_stable_probe.py', 'run_op00_stable_probe.sh', 'measurement.py', 'board_safety.py')}
mapping['m120_board_env_preflight.py'] = BASE / 'm175_m120_fixed_text_candidate/runtime/m120_board_env_preflight.py'
mapping['m120_board_common.py'] = BASE / 'm120_text4b_board_candidate/runtime/m120_board_common.py'
for name, source in mapping.items():
    if name.endswith('.py'):
        ast.parse(source.read_text(encoding='utf-8'))
output.mkdir(exist_ok=False)
items = []
for name, source in mapping.items():
    dest = output / name
    dest.write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
    items.append({'path': name, 'bytes': dest.stat().st_size, 'sha256': sha256(dest)})
write_json(output / 'PACKAGE_MANIFEST.json', dict(schema_version=1, files=items, file_count=len(items),
           total_bytes=sum(x['bytes'] for x in items), unchanged_hardware_prerequisites=evidence,
           stable_artifact_manifest_sha256=expected_manifest))
print(json.dumps(dict(package=str(output), manifest_sha256=sha256(output / 'PACKAGE_MANIFEST.json'),
                     file_count=len(items), total_bytes=sum(x['bytes'] for x in items))))
