"""Verified stable T32 only: minimal zero transaction and executable restore.

On non-idle DMA failure retain buffers/lock in this process, persist diagnostics,
and wait for operator recovery. Never free live DMA storage or reset in a loop.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from measurement import sha256, write_json
from board_safety import safe_to_release, device_owner_blocks
from m120_board_common import (BUILD_ID, KERNEL_NAME, DMA_NAME, REG_POINTERS,
                               REG_CONFIG, REG_AP_CTRL, physical_address,
                               write_u64, wait_transaction, snapshot)

ROOT = Path('/home/ubuntu/tellme_m120_m89x2_20260901')
STABLE = ROOT / 'm175_m120_fixed_text_candidate'
STABLE_SHA = '406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'


def service_stopped():
    sockets = subprocess.run(['ss', '-ltnp'], capture_output=True, text=True, check=True, timeout=5)
    if ':8001' in sockets.stdout:
        raise RuntimeError('Port8001 busy; do not stop user service')
    processes = subprocess.run(['pgrep', '-af', 'm254_video_server|m222_video_server|m243_video_server|m276_m254_video_server'],
                               capture_output=True, text=True, timeout=5)
    if processes.returncode != 1:
        raise RuntimeError('Project service busy or process inspection failed')
    owners, display_owners = [], []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    driver_link = Path('/sys/class/drm') / Path(target).name / 'device/driver'
                    driver = driver_link.resolve().name if target.startswith('/dev/dri/') and driver_link.exists() else None
                    item = {'pid': int(proc.name), 'device': target, 'driver': driver}
                    if device_owner_blocks(target, driver):
                        owners.append(item)
                    elif target.startswith('/dev/dri/'):
                        display_owners.append(item)
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass
    if owners:
        raise RuntimeError('Other accelerator owner: ' + json.dumps(owners))
    return {'port8001_listening': False, 'accelerator_owners': owners, 'excluded_display_owners': display_owners}


def verify_self(here, digest):
    manifest = here / 'PACKAGE_MANIFEST.json'
    if sha256(manifest) != digest:
        raise RuntimeError('Probe manifest mismatch')
    data = json.loads(manifest.read_text())
    expected = {x['path'] for x in data['files']}
    actual = {p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file() and p != manifest}
    if expected != actual or len(expected) != data['file_count']:
        raise RuntimeError('Probe whitelist/count mismatch')
    if sum(x['bytes'] for x in data['files']) != data['total_bytes']:
        raise RuntimeError('Probe byte count mismatch')
    for item in data['files']:
        p = (here / item['path']).resolve()
        p.relative_to(here)
        if p.stat().st_size != item['bytes'] or sha256(p) != item['sha256']:
            raise RuntimeError('Probe payload mismatch: ' + item['path'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    verify_self(here, args.manifest_sha256)
    if args.result.exists():
        raise RuntimeError('Immutable probe result already exists')
    result = dict(status='FAIL', gate='OP00-stable-T32-load-minimal-restore',
                  build_id=None, overlay_loads=0, service_changed=False,
                  inference_performance=False, errors=[], recovery_required=False)
    buffers, kernel, dma, lock_fd = [], None, None, None
    transaction_started, unsafe = False, False
    try:
        if os.geteuid() != 0:
            raise RuntimeError('Root required')
        lock_fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        result['boot_sha256_before'] = sha256('/boot/firmware/boot.scr.uimg')
        result['cmdline_before'] = Path('/proc/cmdline').read_text()
        env_result = args.result.with_name(args.result.stem + '_environment.json')
        preflight = subprocess.run([sys.executable, str(here / 'm120_board_env_preflight.py'),
            '--candidate', str(STABLE), '--expected-package-manifest-sha256', STABLE_SHA,
            '--result', str(env_result)], timeout=90)
        result['preflight_exit'] = preflight.returncode
        if preflight.returncode:
            raise RuntimeError('Stable full-package/environment preflight failed')
        result['preflight'] = json.loads(env_result.read_text())
        import numpy as np
        from pynq import Overlay, allocate
        bit = STABLE / 'overlay/m120_m89x2_t32.bit'
        overlay = Overlay(str(bit), download=True)
        result['overlay_loads'] += 1
        kernel, dma = getattr(overlay, KERNEL_NAME), getattr(overlay, DMA_NAME)
        descriptor = (8 << 32 | 2 << 42).to_bytes(8, 'little') + bytes(8)
        packet = descriptor + bytes(32 * 80)
        output_bytes = 32 * 4 * 4 * 8
        for _ in range(4):
            buffers.append(allocate((9 * 16,), dtype=np.uint8))
        buffers.append(allocate((len(packet),), dtype=np.uint8))
        buffers.append(allocate((output_bytes,), dtype=np.uint8))
        weights, input_buffer, output_buffer = buffers[:4], buffers[4], buffers[5]
        for buffer in weights:
            buffer[:] = 0
            buffer.sync_to_device()
        input_buffer[:] = np.frombuffer(packet, np.uint8)
        input_buffer.sync_to_device()
        for reg, buffer in zip(REG_POINTERS, weights):
            write_u64(kernel, reg, physical_address(buffer))
        kernel.write(REG_CONFIG, 1 | 2 << 8 | 1 << 16)
        result['transaction'] = dict(identity='stable-build-id-zero', input_bytes=len(packet), output_bytes=output_bytes)
        transaction_started = True
        dma.recvchannel.transfer(output_buffer, nbytes=output_bytes)
        kernel.write(REG_AP_CTRL, 1)
        dma.sendchannel.transfer(input_buffer, nbytes=len(packet))
        proof = wait_transaction(kernel, dma, 5.0, 'stable-build-id-zero', len(packet), output_bytes)
        result['transaction']['completion'] = proof
        output_buffer.sync_from_device()
        if int(proof['ap_return']) != BUILD_ID or np.any(output_buffer):
            raise RuntimeError('Build ID / exact zero output mismatch')
        result['build_id'] = f'0x{BUILD_ID:08X}'
        final = snapshot(kernel, dma)
        result['transaction']['release_snapshot'] = final
        if not safe_to_release(final):
            raise RuntimeError('DMA/kernel not proven safe to release')
        for buffer in reversed(buffers):
            buffer.freebuffer()
        buffers.clear()
        transaction_started = False
        # Exercise the exact recovery method, using only the already proven stable bit.
        restored = Overlay(str(bit), download=True)
        result['overlay_loads'] += 1
        kernel, dma = getattr(restored, KERNEL_NAME), getattr(restored, DMA_NAME)
        result['restore_before_transaction'] = snapshot(kernel, dma)
        # Fresh PYNQ channels have not transferred. Prove recovery with another
        # complete zero transaction instead of accepting an untested startup flag.
        for _ in range(4):
            buffers.append(allocate((9 * 16,), dtype=np.uint8))
        buffers.append(allocate((len(packet),), dtype=np.uint8))
        buffers.append(allocate((output_bytes,), dtype=np.uint8))
        for buffer in buffers[:4]:
            buffer[:] = 0
            buffer.sync_to_device()
        buffers[4][:] = np.frombuffer(packet, np.uint8)
        buffers[4].sync_to_device()
        for reg, buffer in zip(REG_POINTERS, buffers[:4]):
            write_u64(kernel, reg, physical_address(buffer))
        kernel.write(REG_CONFIG, 1 | 2 << 8 | 1 << 16)
        transaction_started = True
        dma.recvchannel.transfer(buffers[5], nbytes=output_bytes)
        kernel.write(REG_AP_CTRL, 1)
        dma.sendchannel.transfer(buffers[4], nbytes=len(packet))
        result['restore_completion'] = wait_transaction(kernel, dma, 5.0,
            'stable-restored-build-id-zero', len(packet), output_bytes)
        buffers[5].sync_from_device()
        if int(result['restore_completion']['ap_return']) != BUILD_ID or np.any(buffers[5]):
            raise RuntimeError('Restored Build / zero output mismatch')
        restore_state = snapshot(kernel, dma)
        result['restore_snapshot'] = restore_state
        if not safe_to_release(restore_state):
            raise RuntimeError('Restored transaction is not safe to release')
        for buffer in reversed(buffers):
            buffer.freebuffer()
        buffers.clear()
        transaction_started = False
        result['final_service'] = service_stopped()
        result['boot_unchanged'] = sha256('/boot/firmware/boot.scr.uimg') == result['boot_sha256_before']
        result['cmdline_unchanged'] = Path('/proc/cmdline').read_text() == result['cmdline_before']
        if not result['boot_unchanged'] or not result['cmdline_unchanged']:
            raise RuntimeError('Protected boot identity changed')
        result['status'] = 'PASS'
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        if kernel is not None and dma is not None:
            result['failure_snapshot'] = snapshot(kernel, dma)
        unsafe = transaction_started and not safe_to_release(result.get('failure_snapshot', {}))
        result['recovery_required'] = unsafe or bool(result['overlay_loads'])
    finally:
        result['unsafe_dma_buffers_retained'] = unsafe
        write_json(args.result, result)
        print('OP00_PROBE_JSON_BEGIN', flush=True)
        print(json.dumps(result, allow_nan=False), flush=True)
        print('OP00_PROBE_JSON_END', flush=True)
        if unsafe:
            print('OP00_DMA_QUARANTINE_DO_NOT_INTERRUPT_PROCESS_OR_REUSE_DEVICE', flush=True)
            # Keep references and device lock alive. Recovery requires operator power isolation.
            while True:
                time.sleep(30)
        for buffer in reversed(buffers):
            buffer.freebuffer()
        if lock_fd is not None:
            os.close(lock_fd)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
