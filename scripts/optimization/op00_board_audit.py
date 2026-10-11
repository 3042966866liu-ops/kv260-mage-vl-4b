"""Bounded read-only board audit with kernel-wide advisory lock. Never loads PL."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest-sha256', required=True)
    ap.add_argument('--result', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    manifest_path = here / 'PACKAGE_MANIFEST.json'
    if sha(manifest_path) != args.manifest_sha256:
        raise RuntimeError('audit package manifest mismatch')
    manifest = json.loads(manifest_path.read_text())
    for item in manifest['files']:
        path = (here / item['path']).resolve()
        path.relative_to(here)
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('audit payload identity mismatch')
    if args.result.exists():
        raise RuntimeError('refuse overwriting audit attempt')
    result = {'status': 'FAIL', 'scope': 'OP00-board-files-environment-lock-audit',
              'overlay_loaded': False, 'service_changed': False, 'kernel_register_read': False,
              'evidence': {}, 'errors': []}
    root = Path('/home/ubuntu/tellme_m120_m89x2_20260901')
    lock_fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
    locked = False
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        other_fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_RDWR)
        try:
            try:
                fcntl.flock(other_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                result['evidence']['device_lock_exclusion'] = True
            else:
                raise RuntimeError('device lock did not exclude second writer')
        finally:
            os.close(other_fd)
        if os.geteuid() != 0:
            raise RuntimeError('root required for complete preflight')
        if os.environ.get('XILINX_XRT') != '/usr' or os.environ.get('TMPDIR') != '/dev/shm':
            raise RuntimeError('fixed environment not set')
        selected = shutil.which('xclbinutil')
        expected = '/usr/local/share/pynq-venv/bin/xclbinutil'
        if selected != expected:
            raise RuntimeError('wrong xclbinutil')
        version = subprocess.run([expected, '--version'], capture_output=True, text=True, timeout=15)
        if version.returncode:
            raise RuntimeError('xclbinutil nonzero exit')
        from pynq._3rdparty import xrt
        from pynq.pl_server import Device
        result['evidence']['xrt'] = {'supported': bool(xrt.XRT_SUPPORTED),
            'probe': int(xrt.xclProbe()) if xrt.XRT_SUPPORTED else 0, 'devices': len(Device.devices),
            'xclbinutil': selected, 'version': version.stdout.splitlines()[:1]}
        if result['evidence']['xrt']['probe'] != 1 or len(Device.devices) != 1:
            raise RuntimeError('XRT/PYNQ enumeration mismatch')
        packages = {}
        for name in ('m175_m120_fixed_text_candidate', 'm181_m120_video_board_candidate',
                     'm242_m241_fixed_text_delta', 'm243_web_prefill_delta', 'm254_dual_path_web_candidate'):
            directory = root / name
            pm = directory / 'PACKAGE_MANIFEST.json'
            packages[name] = {'exists': directory.is_dir(), 'manifest_exists': pm.is_file(),
                              'manifest_sha256': sha(pm) if pm.is_file() else None}
        result['evidence']['packages'] = packages
        stable = root / 'm175_m120_fixed_text_candidate'
        overlay = stable / 'overlay'
        expected_files = {'m120_m89x2_t32.bit': '1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac',
                          'm120_m89x2_t32.hwh': '9bd6100bcc274486ddd51133e4dc2247f35c030d49e53cc709438f2a74ee3520'}
        result['evidence']['stable_overlay'] = []
        for name, digest in expected_files.items():
            path = overlay / name
            observed = sha(path) if path.is_file() else None
            result['evidence']['stable_overlay'].append({'path': str(path), 'sha256': observed,
                                                         'match': observed == digest})
            if observed != digest:
                result['errors'].append('stable overlay mismatch: ' + name)
        proc = subprocess.run(['pgrep', '-af', 'm254_video_server|m222_video_server|m243_video_server|m276_m254_video_server'],
                              capture_output=True, text=True, timeout=5)
        result['evidence']['service_processes'] = {'rc': proc.returncode, 'stdout': proc.stdout}
        if proc.returncode not in (0, 1):
            raise RuntimeError('process inspection failed')
        result['evidence']['listeners'] = subprocess.run(['ss', '-ltnp'], capture_output=True, text=True,
                                                          timeout=5).stdout
        for path in ('/proc/cmdline', '/sys/class/fpga_manager/fpga0/state'):
            result['evidence'][path] = Path(path).read_text().strip()
        result['evidence']['boot_sha256'] = sha('/boot/firmware/boot.scr.uimg')
        result['evidence']['override_dtb_exists'] = Path('/boot/firmware/user-override.dtb').exists()
        result['status'] = 'FAIL' if result['errors'] else 'PASS'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
    finally:
        if locked:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix('.partial')
    with temporary.open('w') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, args.result)
    print('OP00_AUDIT_JSON_BEGIN', flush=True)
    print(json.dumps(result, allow_nan=False), flush=True)
    print('OP00_AUDIT_JSON_END', flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
