"""One CPU-only native run or saved-result collection; never retries a run."""
import base64
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(ROOT / 'scripts/optimization')]
from generate_flap522 import read, sha
from prepare_adaptive522 import save, synchronized
import m511n_gate_control01 as prior

R = ROOT / 'deployment/mage_vl4b/optimization_v1/runs'
PKG = ROOT / 'deployment/mage_vl4b/optimization_v1/candidates/M522-sparse-native-reference-02'
LOG = ROOT / 'tmp/m522w_native03'
OUT = R / 'M522-sparse-native-board-reference-03'
PREP = R / 'M522-native-control-preparation-03/RESULT.json'
REMOTE = '/dev/shm/m522_native_import_fix03'
PATCH = ROOT / 'deployment/mage_vl4b/optimization_v1/candidates/M522-native-import-fix-03'
UART = ROOT / 'scripts/m455_original94_uart03.ps1'


def prepare():
    assert not PREP.exists()
    files = [Path(__file__), UART, R / 'M522-sparse-native-admission-01/RESULT.json',
             R / 'M522-sparse-ram-transfer-preparation-02/RESULT.json',
             PKG / 'PACKAGE_MANIFEST.json', *[f for f in PATCH.iterdir() if f.is_file()]]
    save(PREP, dict(status='FROZEN_M522_NATIVE_CPU_ONE_RUN_CONTROL',
        frozen={f.relative_to(ROOT).as_posix():sha(f) for f in files},
        manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
        remote=REMOTE, bound_s=3900, Overlay=0, DMA=0,
        on_missing_prompt='Stop without sending credentials or a command',
        on_existing_attempt='Collect saved output only; never rerun the model'))
    print('FROZEN_M522_NATIVE_CPU_ONE_RUN_CONTROL', sha(PREP), flush=True)


def verify():
    p = read(PREP)
    for n, h in p['frozen'].items():
        assert sha(ROOT / n) == h, n
    for row in read(PKG / 'PACKAGE_MANIFEST.json')['files']:
        assert sha(PKG / row['path']) == row['sha256']
    return p


def uart(command, label, seconds):
    LOG.mkdir(parents=True, exist_ok=True)
    path, host = LOG / (label + '.log'), LOG / (label + '_host.raw')
    assert not path.exists() and not host.exists(), 'Existing attempt: collect only'
    args = [prior.PWSH, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(UART),
            '-Command', command, '-LogPath', path.relative_to(ROOT).as_posix(),
            '-TimeoutSeconds', str(seconds), '-MarkerPrefix', '__M522W_' + label.upper() + '_RC_']
    with host.open('xb') as f:
        rc = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    save(LOG / (label + '_EXIT.json'), dict(original_host_rc=rc, log_sha256=sha(path) if path.exists() else None))
    return rc


def run():
    p = verify()
    preflight = ROOT / 'tmp/m522w_native_patch03/Preflight03.log'
    text = preflight.read_text(encoding='utf-8-sig')
    assert 'M522_NATIVE_IMPORT_PREFLIGHT_PASS' in text and '__M522_NATIVE_PREFLIGHT03_RC_0__' in text
    prior.board_available()
    transfer = R / 'M522W-board-artifact-transfer-01/BOARD_RESULT.json'
    t = read(transfer)
    assert t['status'] == 'PASS_M522W_ARTIFACT_TRANSFER_ONLY' and t['temporary_address_restored']
    assert t['package_manifest_sha256'] == p['manifest_sha256']
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert sha(transfer) in (ROOT / name).read_text(encoding='utf-8-sig')
    assert not (LOG / 'Native_Run01.log').exists() and not OUT.exists()
    assert uart('sudo -n true', 'Native_Sudo01', 15) == 0, 'Same-COM3 authorization absent'
    assert uart('test ! -e /dev/shm/m522_sparse_native_reference03', 'Native_Absent01', 15) == 0
    runner = PATCH / 'run_native_reference03.sh'
    rc = uart('sudo -n bash ' + REMOTE + '/run_native_reference03.sh ' +
              sha(runner) + ' ' + p['manifest_sha256'], 'Native_Run01', p['bound_s'])
    collect()
    return rc


def collect():
    p = verify()
    log = LOG / 'Native_Run01.log'
    text = log.read_text(encoding='utf-8-sig')
    hs = re.findall(r'(?m)^M522_NATIVE_RESULT_SHA256=([0-9a-f]{64})\r?$', text)
    chunks = re.findall(r'(?m)^M522_NATIVE_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\r?$', text)
    if len(hs) != 1 or not chunks:
        raise RuntimeError('Native result incomplete: retain original attempt and collect saved bytes, never rerun')
    assert [int(x[0]) for x in chunks] == list(range(len(chunks)))
    assert all(int(x[1]) == len(chunks) for x in chunks)
    raw = b''.join(base64.b64decode(x[2], validate=True) for x in chunks)
    assert hashlib.sha256(raw).hexdigest() == hs[0]
    value = json.loads(raw)
    assert value['manifest_sha256'] == p['manifest_sha256'] and value['reference_only'] is True
    assert value['Overlay'] == value['DMA'] == value['fpga_transactions'] == 0
    rc = value['original_rc']
    assert type(rc) is int and rc in (0, 1)
    assert '__M522W_NATIVE_RUN01_RC_' + str(rc) + '__' in text
    assert read(LOG / 'Native_Run01_EXIT.json')['original_host_rc'] == rc
    if rc == 0:
        assert value['status'] == 'PASS_M522_NATIVE_VISION_CPU_REFERENCE_ONLY'
        assert set(value['arms']) == {'original', 'candidate'}
        for arm in value['arms'].values():
            assert len(arm['boundaries']) == 24 and arm['scope_restored'] and arm['complete_visual_forward']
            assert set(arm['batches']) == set(map(str, range(13, 24)))
            for parts in arm['batches'].values():
                assert set(parts) == {'fc1', 'fc2'}
                for batches in parts.values():
                    assert [b['rows'] for b in batches] == [32] * 12 + [8]
        assert 90 <= len(value['raw_files']) <= 180
    OUT.mkdir(parents=True, exist_ok=False)
    # Preserve original JSON bytes, including failed result, before publishing.
    from m441_host_io08 import atomic
    atomic(OUT / 'BOARD_RESULT.json', raw, immutable=True)
    receipt = dict(status=('PENDING_BINARY_AUDIT' if rc == 0 else 'FAIL_NATIVE_REFERENCE'),
        raw_sha256=hs[0], host_rc=rc, log_sha256=sha(log),
        binary_fetch_complete=False, hardware_transactions=0, performance_pass=False)
    save(OUT / 'COLLECTION_PENDING.json', receipt)
    synchronized('latest_m522_native_cpu_result03',
        dict(status=receipt['status'], result=(OUT / 'BOARD_RESULT.json').relative_to(ROOT).as_posix(),
             sha256=hs[0], board=True, native_cpu_only=True, performance=False),
        '## M522两层候选A53原生CPU参考原结果\n\n' + value['status'] +
        '；COM3原退出与原JSON字节已核，0 Overlay/DMA/FPGA事务。'
        '完整binary尚待取回独立审计，不晋级硬件、不称速度或质量通过。\n\nRESULT SHA `' + hs[0] + '`。')
    print(receipt['status'], hs[0], flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['Prepare']:
        prepare()
    elif sys.argv[1:] == ['Run']:
        raise SystemExit(run())
    elif sys.argv[1:] == ['Collect']:
        collect()
    else:
        raise SystemExit('Explicit Prepare/Run/Collect required')
