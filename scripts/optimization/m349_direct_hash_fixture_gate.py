"""Opt-in bounded fixture gate, never reads model assets or loads an Overlay."""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import unittest

sys.dont_write_bytecode = True
from direct_hash import (AlignedBuffer, BLOCK, DirectHashRejected, alignment_for_fd,
                         check_budget, direct_sha256, identity, require_linux)
from test_direct_hash import DirectHashTests

HERE = Path(__file__).resolve().parent
EVIDENCE = Path('/home/ubuntu/m349_direct_hash_evidence_01')
FIXTURES = Path('/home/ubuntu/m349_direct_hash_fixtures_01')
RELEASE = Path('/home/ubuntu/tellme_release_install_20260926')
PRIOR = 'e4ed4b37bfa2122e0d9dd5998665767dfd47bf3e346cd312bbd7080d3437ff8e'
PATTERN = bytes((i * 73 + 19) % 256 for i in range(256))
SIZES = (0, 1, 4095, 4096, 4097, BLOCK - 1, BLOCK, BLOCK + 1)
LIVE_OBSERVATION_MAPS = 0


def atomic(path, result):
    encoded = (json.dumps(result, indent=2) + '\n').encode('utf-8')
    part = path.with_name(path.name + '.part')
    with part.open('wb') as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(part, path)


def snapshot():
    memory = {}
    for line in Path('/proc/meminfo').read_text(encoding='utf-8').splitlines():
        name, value = line.split(':', 1)
        if name in ('CmaFree', 'CmaTotal', 'Cached', 'MemAvailable'):
            memory[name] = int(value.split()[0]) * 1024
    for line in Path('/proc/self/status').read_text(encoding='utf-8').splitlines():
        if line.startswith('VmRSS:'):
            memory['VmRSS'] = int(line.split()[1]) * 1024
    return memory


def verify_package(expected):
    raw = (HERE / 'PACKAGE_MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise DirectHashRejected('Package manifest SHA mismatch')
    manifest = json.loads(raw)
    names = set()
    for row in manifest['files']:
        name = row['path']
        if Path(name).name != name or name in names:
            raise DirectHashRejected('Non-whitelisted package path')
        names.add(name)
        data = (HERE / name).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise DirectHashRejected('Package member differs: ' + name)
    if len(names) != manifest['file_count'] or sum(r['bytes'] for r in manifest['files']) != manifest['total_bytes']:
        raise DirectHashRejected('Manifest count/bytes differ')
    if {p.name for p in HERE.iterdir()} != names | {'PACKAGE_MANIFEST.json'}:
        raise DirectHashRejected('Unexpected package files')
    prerequisite = json.loads((HERE / 'M348_PREREQUISITE.json').read_text(encoding='utf-8'))
    if prerequisite['raw_sha256'] != PRIOR or prerequisite['evidence_level'] != 'L0_SOURCE_AUDIT_ONLY':
        raise DirectHashRejected('Frozen M348 prerequisite differs')


def mount_record(path, mount_id=None):
    dev = path.stat().st_dev
    records = []
    for line in Path('/proc/self/mountinfo').read_text(encoding='utf-8').splitlines():
        left, right = line.split(' - ', 1)
        fields = left.split()
        if fields[2] == str(os.major(dev)) + ':' + str(os.minor(dev)):
            records.append(dict(id=int(fields[0]), mount_point=fields[4], fs_type=right.split()[0], raw=line))
    if mount_id is not None:
        records = [r for r in records if r['id'] == mount_id]
    if len(records) != 1:
        raise DirectHashRejected('Mount identity not unique')
    return records[0]


def expected_sha(size):
    # Independent memory-only expected digest; no ordinary fixture file read.
    h = hashlib.sha256()
    page = PATTERN * 16
    for unused in range(size // len(page)):
        h.update(page)
    h.update(page[:size % len(page)])
    return h.hexdigest()


def create_fixture(path, size, alignment, deadline):
    if path.parent != FIXTURES or path.exists():
        raise DirectHashRejected('Only new exact fixture paths allowed')
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_DIRECT | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        actual = alignment_for_fd(fd)
        if actual != alignment:
            raise DirectHashRejected('Fixture direct alignment/mount differs')
        padded = ((size + alignment.offset - 1) // alignment.offset) * alignment.offset
        with AlignedBuffer(BLOCK, alignment.memory) as buffer:
            data = PATTERN * (BLOCK // len(PATTERN))
            buffer.view[:] = data
            offset = 0
            while offset < padded:
                check_budget(deadline)
                count = min(BLOCK, padded - offset)
                target = buffer.view[:count]
                try:
                    wrote = os.pwritev(fd, [target], offset)
                finally:
                    target.release()
                if wrote != count:
                    raise DirectHashRejected('Short direct fixture write; no fallback')
                offset += wrote
        os.ftruncate(fd, size)
        os.fsync(fd)
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_mode & 0o777 != 0o600:
            raise DirectHashRejected('Fixture ownership/mode invalid')
        return list(identity(info))
    finally:
        os.close(fd)


def resident_pages(path, deadline):
    """PROT_NONE observation only; no touched pages and no mapping during reads."""
    global LIVE_OBSERVATION_MAPS
    check_budget(deadline)
    info = path.stat(follow_symlinks=False)
    if info.st_uid != os.geteuid() or info.st_nlink != 1:
        raise DirectHashRejected('mincore ownership evidence unavailable')
    if not info.st_size:
        return dict(pages=0, resident=0, owner=info.st_uid, euid=os.geteuid(), permission_valid=True)
    length = math.ceil(info.st_size / mmap_page_size()) * mmap_page_size()
    pages = length // mmap_page_size()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.mmap.restype = ctypes.c_void_p
    libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
    libc.mincore.restype = ctypes.c_int
    libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    libc.munmap.restype = ctypes.c_int
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    address = None
    try:
        if identity(os.fstat(fd)) != identity(info):
            raise DirectHashRejected('mincore file identity changed')
        address = libc.mmap(None, length, 0, 1, fd, 0)  # PROT_NONE, MAP_SHARED.
        if address == ctypes.c_void_p(-1).value:
            address = None
            raise OSError(ctypes.get_errno(), 'mincore mmap failed')
        LIVE_OBSERVATION_MAPS += 1
        vec = (ctypes.c_ubyte * pages)()
        if libc.mincore(address, length, vec) != 0:
            raise OSError(ctypes.get_errno(), 'mincore failed')
        if identity(os.fstat(fd)) != identity(info):
            raise DirectHashRejected('mincore identity changed during observation')
        return dict(pages=pages, resident=sum(value & 1 for value in vec), owner=info.st_uid,
                    euid=os.geteuid(), permission_valid=True)
    finally:
        try:
            if address is not None:
                if libc.munmap(address, length) != 0:
                    raise OSError(ctypes.get_errno(), 'mincore munmap failed')
                LIVE_OBSERVATION_MAPS -= 1
        finally:
            os.close(fd)


def mmap_page_size():
    return os.sysconf('SC_PAGE_SIZE')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest_sha')
    parser.add_argument('--enable-fixture-gate', action='store_true')
    args = parser.parse_args()
    if not args.enable_fixture_gate:
        parser.error('Fixture gate disabled by default; explicit opt-in required')
    # Fixed new result directory; never overwrite/re-execute after unknown outcome.
    EVIDENCE.mkdir(mode=0o700, exist_ok=False)
    result = dict(status='FAIL_COMPONENT_UNPROVEN', gate_level='small-direct-hash-fixtures-only',
        build_id='0x4D395832', prior_raw_sha256=PRIOR, errors=[], fixtures=[], observations=[],
        overlay_loaded=False, model_forward_calls=0, fpga_transactions=0, real_assets_read=False,
        direct_mode_proven=False, memory_capacity_proven=False, numerical_pass=False,
        performance_pass=False, formal_promotion_allowed=False, cache_eviction=False,
        fixture_limit_bytes=16 << 20, budget_seconds=60, scope='Component only; no runtime integration')
    started = time.monotonic()
    deadline = started + 60
    phase = 'package'
    try:
        verify_package(args.manifest_sha)
        result['manifest_sha256'] = args.manifest_sha
        require_linux()
        if os.geteuid() != 0:
            raise DirectHashRejected('Same authorized terminal root required')
        result['platform'] = dict(uname=list(os.uname()), python=sys.version, euid=os.geteuid(),
                                  executable=sys.executable, page_size=mmap_page_size())
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(DirectHashTests)
        tested = unittest.TextTestRunner(verbosity=1).run(suite)
        if not tested.wasSuccessful():
            raise DirectHashRejected('Actual Python algorithm/error checks failed')
        result['algorithm_checks'] = tested.testsRun
        FIXTURES.mkdir(mode=0o700, exist_ok=False)
        if FIXTURES.stat().st_dev != RELEASE.stat().st_dev:
            raise DirectHashRejected('Fixtures not on installed release filesystem')
        result['mount_before_alignment'] = mount_record(FIXTURES)
        phase = 'capability'
        probe = FIXTURES / 'alignment-probe.bin'
        fd = os.open(probe, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            align = alignment_for_fd(fd)
        finally:
            os.close(fd)
        result['alignment'] = dict(memory=align.memory, offset=align.offset, mount_id=align.mount_id)
        result['mount'] = mount_record(FIXTURES, align.mount_id)
        if result['mount']['fs_type'] not in ('ext4', 'xfs', 'f2fs'):
            raise DirectHashRejected('Filesystem outside explicit supported scope')
        padded_total = sum(((s + align.offset - 1) // align.offset) * align.offset for s in SIZES + (65536,))
        if padded_total > result['fixture_limit_bytes']:
            raise DirectHashRejected('Fixture byte budget exceeded')
        for index, size in enumerate(SIZES):
            phase = 'fixture-' + str(index)
            check_budget(deadline)
            path = FIXTURES / ('fixture-' + str(index) + '.bin')
            row = dict(index=index, size=size, path=str(path), expected_sha256=expected_sha(size))
            result['fixtures'].append(row)
            row['created_identity'] = create_fixture(path, size, align, deadline)
            row['resident_before'] = resident_pages(path, deadline)
            if row['resident_before']['resident'] != 0:
                raise DirectHashRejected('Fresh fixture already resident; no eviction/retry')
            row['hash'] = direct_sha256(path, enabled=True, expected_sha256=row['expected_sha256'], deadline=deadline)
            row['resident_after'] = resident_pages(path, deadline)
            if row['resident_after']['resident'] != 0:
                raise DirectHashRejected('New resident pages after direct read; fallback unproven')
            result['observations'].append(dict(phase=phase, elapsed_s=time.monotonic()-started, memory=snapshot()))
            atomic(EVIDENCE / 'progress.json', result)
            print('M349_FIXTURE_OK index=' + str(index) + ' size=' + str(size), flush=True)
        phase = 'residency-control'
        control = FIXTURES / 'ordinary-read-control.bin'
        create_fixture(control, 65536, align, deadline)
        before = resident_pages(control, deadline)
        if before['resident']:
            raise DirectHashRejected('Control initially resident; cannot validate observation')
        fd = os.open(control, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            data = os.read(fd, 65536)
            if len(data) != 65536 or hashlib.sha256(data).hexdigest() != expected_sha(65536):
                raise DirectHashRejected('Ordinary control SHA/length differs')
        finally:
            os.close(fd)
        after = resident_pages(control, deadline)
        result['residency_control'] = dict(before=before, after=after)
        if after['resident'] != after['pages'] or not after['resident']:
            raise DirectHashRejected('mincore positive control not proven')
        check_budget(deadline)
        result.update(status='PASS_SMALL_DIRECT_HASH_COMPONENT_ONLY', direct_mode_proven=True,
                      fixture_allocated_bytes=padded_total)
    except BaseException as error:
        result['errors'].append(type(error).__name__ + ': ' + str(error))
        result['traceback'] = traceback.format_exc()
    finally:
        result['final_phase'] = phase
        result['elapsed_s'] = time.monotonic() - started
        result['final_memory'] = snapshot()
        remaining_fds = []
        for entry in Path('/proc/self/fd').iterdir():
            try:
                target = os.readlink(entry)
            except FileNotFoundError:
                continue
            if target.startswith(str(FIXTURES) + '/'):
                remaining_fds.append(dict(fd=entry.name, target=target))
        result['lifecycle'] = dict(live_aligned_buffers=AlignedBuffer.live_count,
            live_observation_maps=LIVE_OBSERVATION_MAPS, remaining_fixture_fds=remaining_fds,
            cleanup_policy='Per-operation finally; cleanup exceptions reject gate')
        if AlignedBuffer.live_count or LIVE_OBSERVATION_MAPS or remaining_fds:
            result['errors'].append('Resource lifecycle not proven closed')
            result['status'] = 'FAIL_COMPONENT_UNPROVEN'
            result['direct_mode_proven'] = False
        result['gate_return_code'] = 0 if result['status'] == 'PASS_SMALL_DIRECT_HASH_COMPONENT_ONLY' else 1
        atomic(EVIDENCE / 'BOARD_RESULT.json', result)
        print('M349_COMPONENT_RESULT status=' + result['status'], flush=True)
    return 0 if result['status'] == 'PASS_SMALL_DIRECT_HASH_COMPONENT_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
