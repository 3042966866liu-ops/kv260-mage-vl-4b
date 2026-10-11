import ast
import json
from pathlib import Path
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
output = BASE / 'candidates/OP00-import-decode-01'
old = json.loads((BASE / 'candidates/OP00-model-inventory-01/inventory_targets.json').read_text())
dataset = BASE / 'datasets/dev_bootstrap_v1'
config = dict(previous_board_result_sha256=sha256(BASE / 'gates/G00-model-inventory/attempt_01/board_raw.json'),
    python_path=['m190_mage_runtime'] + old['python_path'],
    imports=['numpy', 'tokenizers', 'torch', 'transformers', 'PIL', 'm238_prefill_runtime',
             'm241_video_language_runtime', 'm222_vectorized_w4_runtime'],
    video_sha256=sha256(dataset / 'dev-0001.mp4'),
    question='In which direction does the red circle move, left to right or right to left?')
mapping = {name: Path(__file__).with_name(name) for name in ('op00_import_decode_probe.py',
    'run_import_decode_probe.sh', 'measurement.py', 'sys_video_input.py')}
mapping['dev-0001.mp4'] = dataset / 'dev-0001.mp4'
for name, source in mapping.items():
    if name.endswith('.py'):
        ast.parse(source.read_text())
output.mkdir(exist_ok=False)
write_json(output / 'probe_config.json', config)
for name, source in mapping.items():
    content = source.read_bytes()
    (output / name).write_bytes(content.replace(b'\r\n', b'\n') if name.endswith(('.py','.sh')) else content)
records = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in sorted(output.iterdir())]
write_json(output / 'PACKAGE_MANIFEST.json', dict(files=records, file_count=len(records),
    total_bytes=sum(r['bytes'] for r in records), scope='read-only no Overlay/model'))
print(json.dumps(dict(package=str(output), manifest_sha256=sha256(output / 'PACKAGE_MANIFEST.json'))))
