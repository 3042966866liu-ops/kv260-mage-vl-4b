"""Clean tiny code package; only record identities of existing large weights."""
import json
from pathlib import Path
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b'
out = BASE / 'optimization_v1/candidates/OP00-model-inventory-01'
packages = {
    'm175_m120_fixed_text_candidate': BASE / 'm175_m120_fixed_text_candidate',
    'm181_m120_video_board_candidate': BASE / 'm181_m120_video_board_candidate',
    'm242_m241_fixed_text_delta': BASE / 'm242_m241_fixed_text_board_candidate',
    'm227_runtime_base_patch': ROOT / 'tmp/m227_runtime_base/m227_runtime_base_patch',
    'm223_realtime_delta': ROOT / 'tmp/m223_realtime/m223_realtime_delta',
    'm218_dual_source_delta': ROOT / 'tmp/m218_dual_source/m218_dual_source_delta',
}
targets = {'packages': [dict(board_name=k, sha256=sha256(v / 'PACKAGE_MANIFEST.json'),
    allow_ready=k == 'm181_m120_video_board_candidate') for k,v in packages.items()],
    'layouts': [
        dict(board_path='m120_fulltext_weights_0x4D395832/language_fourport',
             sha256='12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d'),
        dict(board_path='m120_fulltext_weights_0x4D395832/lmhead_fourport',
             sha256='a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef')],
    'python_path': ['m227_runtime_base_patch', 'm242_m241_fixed_text_delta',
        'm223_realtime_delta', 'm218_dual_source_delta', 'm181_m120_video_board_candidate',
        'm175_m120_fixed_text_candidate/runtime', 'm175_m120_fixed_text_candidate/runtime/support']}
out.mkdir(exist_ok=False)
for name in ('op00_model_inventory.py', 'measurement.py'):
    (out / name).write_bytes(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n'))
write_json(out / 'inventory_targets.json', targets)
files = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in sorted(out.iterdir())]
write_json(out / 'PACKAGE_MANIFEST.json', dict(files=files, file_count=len(files), total_bytes=sum(x['bytes'] for x in files)))
print(json.dumps(dict(path=str(out), manifest_sha256=sha256(out / 'PACKAGE_MANIFEST.json'),files=files)))
