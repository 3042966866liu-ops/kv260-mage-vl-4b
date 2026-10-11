"""Default-off, immutable CPU-only environment observation and saved export."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from m404_warm_conditions import PROTOCOL_SHA, read_environment

HERE = Path(__file__).resolve().parent
OUTPUT = Path('/home/ubuntu/m404_environment_observation_01/RESULT.json')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(expected):
    if sha(HERE / 'PACKAGE_MANIFEST.json') != expected: raise RuntimeError('Probe manifest SHA differs')
    manifest = json.loads((HERE / 'PACKAGE_MANIFEST.json').read_bytes())
    names = {r['path'] for r in manifest['files']}
    if len(names) != manifest['file_count'] or {p.name for p in HERE.iterdir()} != names | {'PACKAGE_MANIFEST.json'}:
        raise RuntimeError('Probe whitelist differs')
    for row in manifest['files']:
        p = HERE / row['path']
        if p.name != row['path'] or p.is_symlink() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Probe payload differs')
    if sum(r['bytes'] for r in manifest['files']) != manifest['total_bytes']: raise RuntimeError('Probe byte count differs')
    prerequisite = json.loads((HERE / 'PROTOCOL_PREREQUISITE.json').read_bytes())
    if prerequisite['protocol_sha256'] != PROTOCOL_SHA: raise RuntimeError('Protocol identity differs')


def export():
    if os.geteuid() != 0: raise RuntimeError('Root saved export required')
    raw = OUTPUT.read_bytes()
    parts = [raw[i:i+900] for i in range(0, len(raw), 900)]
    print('M404_ENV_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
    for i, part in enumerate(parts):
        print(f'M404_ENV_RESULT_CHUNK={i}/{len(parts)}:' + base64.b64encode(part).decode('ascii'), flush=True)
        time.sleep(.025)


def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'Collect': export(); return 0
    if len(sys.argv) != 3 or sys.argv[2] != '--enable-readonly-observation':
        raise RuntimeError('Environment observation disabled by default')
    if os.geteuid() != 0: raise RuntimeError('Root observation required')
    verify(sys.argv[1])
    if OUTPUT.parent.exists(): raise RuntimeError('Original observation exists; Collect only')
    started = time.monotonic()
    env = read_environment()
    result = dict(status='OBSERVED_WARM_ENVIRONMENT' if not env['observability_issues'] else 'WARM_ENVIRONMENT_UNPROVEN',
                  manifest_sha256=sys.argv[1], protocol_sha256=PROTOCOL_SHA, environment=env,
                  elapsed_s=time.monotonic()-started, overlay_loaded=False, dma_allocations=0,
                  model_forward_calls=0, fpga_transactions=0, cache_changes=False,
                  numerical_pass=False, performance_pass=False, formal_promotion_allowed=False)
    raw = (json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False)+'\n').encode('utf-8')
    OUTPUT.parent.mkdir()
    temp = OUTPUT.with_suffix('.partial')
    with temp.open('xb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(temp, OUTPUT)
    export()
    return 0


if __name__ == '__main__': raise SystemExit(main())
