"""Clean whitelist staging, stable hardware untouched; upload/import is separate."""
import ast
import argparse
import json
from pathlib import Path
from measurement import sha256,write_json
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
parser=argparse.ArgumentParser()
parser.add_argument('--revision',type=int,choices=range(1,100),required=True)
args=parser.parse_args()
OUT=BASE/f'candidates/OP01-SYS-{args.revision:02d}'
files=('op01_board_sys.py','op01_support.py','measurement.py','board_safety.py','sys_request.py',
       'causal_generation.py','sys_video_input.py','video_contract_v2.py','numerical_capture.py',
       'decode_trace.py','decode_diagnostic.py','decode_checkpoint.py','transfer_trace.py','run_board_sys.sh')
mapping={name:Path(__file__).with_name(name) for name in files}
stable_probe=BASE/'candidates/OP00-stable-probe-03'
for name in ('op00_stable_probe.py','m120_board_common.py'):mapping[name]=stable_probe/name
for name,path in mapping.items():
    if name.endswith('.py'):ast.parse(path.read_text(encoding='utf-8'))
config=json.loads((BASE/'candidates/OP00-import-decode-01/probe_config.json').read_text())
config['python_path'].insert(0,'optimization_v1/dependencies/opencv411_arm64_v1/site')
packages={
    'm175_m120_fixed_text_candidate':'deployment/mage_vl4b/m175_m120_fixed_text_candidate',
    'm181_m120_video_board_candidate':'deployment/mage_vl4b/m181_m120_video_board_candidate',
    'm242_m241_fixed_text_delta':'deployment/mage_vl4b/m242_m241_fixed_text_board_candidate',
    'm227_runtime_base_patch':'tmp/m227_runtime_base/m227_runtime_base_patch',
    'm223_realtime_delta':'tmp/m223_realtime/m223_realtime_delta',
    'm218_dual_source_delta':'tmp/m218_dual_source/m218_dual_source_delta'}
config['package_manifest_hashes']={name:sha256(ROOT/path/'PACKAGE_MANIFEST.json') for name,path in packages.items()}
config['classification']='SYS2 development diagnostic only; no numerical or performance acceptance'
OUT.mkdir(exist_ok=False)
for name,path in mapping.items():(OUT/name).write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
write_json(OUT/'sys_config.json',config)
rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha256(p)) for p in sorted(OUT.iterdir())]
write_json(OUT/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
print(json.dumps(dict(package=str(OUT),files=len(rows),bytes=sum(r['bytes'] for r in rows),
                     manifest_sha256=sha256(OUT/'PACKAGE_MANIFEST.json'))))
