"""Real A53 CPU component on saved RTL packets; never imports a PL driver."""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
RESULT = Path('/home/ubuntu/m442_a53_component_evidence_01/BOARD_RESULT.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(manifest_sha):
    if sha(HERE / 'PACKAGE_MANIFEST.json') != manifest_sha:
        raise RuntimeError('Exact package manifest differs')
    manifest = json.loads((HERE / 'PACKAGE_MANIFEST.json').read_bytes())
    actual = {p.name for p in HERE.iterdir() if p.is_file()}
    expected = {r['path'] for r in manifest['files']} | {'PACKAGE_MANIFEST.json'}
    if actual != expected or manifest['file_count'] != len(manifest['files']) or manifest['total_bytes'] != sum(r['bytes'] for r in manifest['files']):
        raise RuntimeError('Exact package whitelist/count differs')
    for row in manifest['files']:
        if '/' in row['path'] or '\\' in row['path'] or (HERE / row['path']).is_symlink():
            raise RuntimeError('Unsafe member path')
        p = HERE / row['path']
        if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise RuntimeError('Member SHA differs: ' + row['path'])


def export():
    raw = RESULT.read_bytes()
    record = json.loads(raw)
    print('M442C_RESULT_SHA256=' + hashlib.sha256(raw).hexdigest(), flush=True)
    print('M442C_SAVED_GATE_RC=' + str(record['gate_return_code']), flush=True)
    chunks = [raw[i:i+900] for i in range(0, len(raw), 900)]
    for i, chunk in enumerate(chunks):
        print('M442C_RESULT_CHUNK=' + str(i) + '/' + str(len(chunks)) + ':' + base64.b64encode(chunk).decode('ascii'), flush=True)


def main():
    if sys.argv[1:] == ['Collect']:
        export()
        return json.loads(RESULT.read_bytes())['gate_return_code']
    if len(sys.argv) != 4 or sys.argv[1] != 'Run' or sys.argv[3] != '--enable-cpu-component':
        raise RuntimeError('Explicit CPU-only gate required')
    if RESULT.parent.exists():
        raise RuntimeError('Existing attempt: collect only')
    RESULT.parent.mkdir(mode=0o700)
    started = time.monotonic()
    result = dict(status='FAIL_M442_A53_COMPONENT01', gate_return_code=1, manifest_sha256=sys.argv[2], errors=[],
                  board_cpu=True, numerical_pass=False, complete_request_performance_pass=False,
                  Overlay_calls=0, DMA_allocations=0, FPGA_transactions=0, model_requests=0,
                  evidence_scope='A53 CPU parser on saved actual M441 RTL bytes; scheduler uses explicit fake hardware and packing')
    try:
        verify(sys.argv[2])
        if os.geteuid() != 0 or platform.system() != 'Linux' or platform.machine().lower() not in ('aarch64', 'arm64'):
            raise RuntimeError('Actual root Linux A53 runtime required')
        from m442_verify_integration02 import run
        integration = run(HERE)
        if integration['actual_packet_comparisons'] != 99 or integration['all_fp16_bits_shifts'] != 11 or integration['partial_strided_checks'] != 81 or len(integration['pipeline_checks']) != 6:
            raise RuntimeError('CPU coverage differs')
        if any(r['parser_workers'] != 1 for r in integration['pipeline_checks']):
            raise RuntimeError('Parser worker contract differs')
        if time.monotonic() - started > 240:
            raise RuntimeError('CPU component budget exceeded')
        result.update(status='PASS_M442_A53_COMPONENT01', gate_return_code=0, numerical_pass=True,
                      integration=integration, platform=dict(system=platform.system(), machine=platform.machine(), euid=os.geteuid(), python=sys.version))
    except BaseException:
        result['errors'].append(traceback.format_exc())
    finally:
        from m441_host_io08 import atomic
        result['elapsed_s'] = time.monotonic() - started
        atomic(RESULT, (json.dumps(result, indent=2)+'\n').encode('utf-8'), immutable=True)
        export()
    return result['gate_return_code']


if __name__ == '__main__':
    raise SystemExit(main())
