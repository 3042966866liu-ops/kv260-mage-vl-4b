"""Experimental-only minimum gate; never overwrite or promote stable artifacts."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from measurement import sha256, write_json
from op00_stable_probe import verify_self, service_stopped, STABLE, STABLE_SHA
from m120_board_common import snapshot, DMA_NAME, KERNEL_NAME
from decode_one_board_protocol import CANDIDATE_BUILD, STABLE_BUILD, zero_transaction, referenced_descriptor
from decode_one_board_transaction import BoardTransaction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--result', required=True, type=Path)
    parser.add_argument('--real-chain', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    verify_self(here, args.manifest_sha256)
    if args.result.exists() or args.result.resolve().is_relative_to(here):
        raise RuntimeError('Result must be new and outside immutable package')
    result = dict(gate='OP01-experimental-minimal-board', status='FAIL',
                  candidate_build='0x4F503131', stable_build='0x4D395832',
                  capacity_status='STOPPED_BY_USER_NOT_PASS', formal_promotion_allowed=False,
                  performance_pass=False, transactions=[], errors=[], overlay_loads=0,
                  recovery_required=False, stable_restored=False)
    lock_fd, transaction, overlay = None, None, None
    loaded = False
    try:
        real_fixture = None
        if args.real_chain:
            from decode_one_real_chain import load_real_chain
            real_fixture = load_real_chain(here / 'real_gate_up.bin')
            result['gate'] = 'OP01-experimental-real-chain-board'
        if os.geteuid() != 0:
            raise RuntimeError('Root required')
        lock_fd = os.open('/tmp/tellme_kv260_execution.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result['initial_service'] = service_stopped()
        result['boot_sha256_before'] = sha256('/boot/firmware/boot.scr.uimg')
        result['cmdline_before'] = Path('/proc/cmdline').read_text()
        for label, script, candidate, digest in (
            ('stable', 'm120_board_env_preflight.py', STABLE, STABLE_SHA),
            ('candidate', 'decode_one_env_preflight.py', here, args.manifest_sha256)):
            env_result = args.result.with_name(args.result.stem + '_' + label + '_environment.json')
            completed = subprocess.run([sys.executable, '-B', str(here / script), '--candidate', str(candidate),
                '--expected-package-manifest-sha256', digest, '--result', str(env_result)], timeout=90)
            if completed.returncode:
                raise RuntimeError(label + ' environment/identity preflight failed')
            result[label + '_preflight'] = json.loads(env_result.read_text())
        from pynq import Overlay, allocate
        # If download itself fails, no transaction was issued; finally attempts
        # one stable restore. Once DMA is active, unsafe failure is quarantined.
        loaded = True
        overlay = Overlay(str(here / 'overlay/op01_decode_one.bit'), download=True)
        result['overlay_loads'] += 1
        kernel, dma = getattr(overlay, 'op01_decode_one_0'), getattr(overlay, DMA_NAME)
        transaction = BoardTransaction(kernel, dma, allocate, lambda: snapshot(kernel, dma))
        cases = (
            ('candidate-build-id-zero', zero_transaction(build_id=CANDIDATE_BUILD)),
            ('candidate-T32-reference-descriptor', referenced_descriptor(decode_one=False)),
            ('candidate-decode-one-reference-descriptor', referenced_descriptor(decode_one=True)))
        if real_fixture is not None:
            cases = (cases[0], ('candidate-real-layer0-gate-up-chain', real_fixture))
        for name, fixture in cases:
            result['current_transaction'] = name
            proof = transaction.run(fixture, name)
            result['transactions'].append(dict(proof))
            write_json(args.result, result)
            print('OP01_MINIMAL_STAGE ' + name + ' PASS', flush=True)
        result['candidate_minimal_pass'] = True
    except Exception as exc:
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        if transaction is not None:
            result['failed_transaction'] = transaction.evidence
    finally:
        unsafe = transaction is not None and transaction.recovery_required
        if loaded and not unsafe:
            try:
                restored = Overlay(str(STABLE / 'overlay/m120_m89x2_t32.bit'), download=True)
                result['overlay_loads'] += 1
                kernel, dma = getattr(restored, KERNEL_NAME), getattr(restored, DMA_NAME)
                transaction = BoardTransaction(kernel, dma, allocate, lambda: snapshot(kernel, dma))
                result['restore_transaction'] = transaction.run(zero_transaction(build_id=STABLE_BUILD),
                                                                 'stable-restored-build-id-zero')
                result['stable_restored'] = True
            except Exception as exc:
                result['errors'].append('restore: ' + f'{type(exc).__name__}: {exc}')
                if transaction is not None:
                    result['restore_failure'] = transaction.evidence
                    unsafe = transaction.recovery_required
        result['recovery_required'] = unsafe or (loaded and not result['stable_restored'])
        result['unsafe_dma_buffers_retained'] = unsafe
        if 'boot_sha256_before' in result:
            result['boot_unchanged'] = sha256('/boot/firmware/boot.scr.uimg') == result['boot_sha256_before']
            result['cmdline_unchanged'] = Path('/proc/cmdline').read_text() == result['cmdline_before']
        if (result.get('candidate_minimal_pass') and result['stable_restored'] and not result['errors']
                and result.get('boot_unchanged') and result.get('cmdline_unchanged')):
            result['status'] = 'PASS_EXPERIMENTAL_MINIMAL_ONLY'
            if args.real_chain:
                result['status'] = 'PASS_EXPERIMENTAL_REAL_CHAIN_ONLY'
        write_json(args.result, result)
        print('OP01_MINIMAL_JSON_BEGIN\n' + json.dumps(result) + '\nOP01_MINIMAL_JSON_END', flush=True)
        if unsafe:
            print('OP01_DMA_QUARANTINE_DO_NOT_INTERRUPT_PROCESS_OR_REUSE_DEVICE', flush=True)
            while True:
                time.sleep(30)
        if lock_fd is not None:
            os.close(lock_fd)
    return 0 if result['status'] in ('PASS_EXPERIMENTAL_MINIMAL_ONLY', 'PASS_EXPERIMENTAL_REAL_CHAIN_ONLY') else 1


if __name__ == '__main__':
    raise SystemExit(main())
