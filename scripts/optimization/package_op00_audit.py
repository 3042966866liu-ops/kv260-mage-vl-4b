"""Create new clean whitelist package; never copy old package trees."""
import json
from pathlib import Path
import shutil
from measurement import sha256, write_json

root = Path(__file__).resolve().parents[2]
output = root / 'deployment/mage_vl4b/optimization_v1/candidates/OP00-audit-01'
output.mkdir(exist_ok=False)
items = []
for name in ('op00_board_audit.py', 'run_op00_board_audit.sh'):
    source = Path(__file__).with_name(name)
    data = source.read_bytes().replace(b'\r\n', b'\n')
    destination = output / name
    destination.write_bytes(data)
    items.append({'path': name, 'bytes': len(data), 'sha256': sha256(destination)})
write_json(output / 'PACKAGE_MANIFEST.json', {'schema_version': 1, 'files': items,
           'file_count': len(items), 'total_bytes': sum(x['bytes'] for x in items)})
print(json.dumps({'package': str(output), 'manifest_sha256': sha256(output / 'PACKAGE_MANIFEST.json'),
                  'files': items}))
