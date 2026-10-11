"""Opt-in Linux direct SHA component. No buffered fallback, runtime hook or imports."""
import ctypes
from dataclasses import dataclass
import hashlib
import mmap
import os
import platform
import stat
import struct
import sys
import time

BLOCK = 4 << 20
MAX_ALIGNMENT = 1 << 20
STATX_DIOALIGN = 0x2000
STATX_MNT_ID = 0x1000
STATX_BASIC_STATS = 0x7ff
AT_EMPTY_PATH = 0x1000


class DirectHashRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class Alignment:
    memory: int
    offset: int
    mount_id: int

    def validate(self):
        for value in (self.memory, self.offset):
            if value <= 0 or value > MAX_ALIGNMENT or value & (value - 1):
                raise DirectHashRejected('Unproven/unsupported direct alignment')
        if BLOCK % self.offset:
            raise DirectHashRejected('Chunk does not meet returned alignment')
        return self


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid, info.st_gid, info.st_nlink)


def require_linux():
    if sys.platform != 'linux' or sys.byteorder != 'little' or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise DirectHashRejected('Only explicit 64-bit little-endian Linux ABI supported')
    if platform.machine().lower() not in ('aarch64', 'x86_64'):
        raise DirectHashRejected('Unsupported machine ABI')
    for name in ('O_DIRECT', 'O_CLOEXEC', 'O_NOFOLLOW', 'preadv', 'pwritev'):
        if not hasattr(os, name):
            raise DirectHashRejected('Required API absent: ' + name)


def alignment_for_fd(fd):
    """Linux UAPI statx size 0x100; DIO fields offsets 0x98/0x9c.

    Primary ABI: include/uapi/linux/stat.h. No preferred-block-size heuristic.
    """
    require_linux()
    libc = ctypes.CDLL(None, use_errno=True)
    if not hasattr(libc, 'statx'):
        raise DirectHashRejected('libc statx absent')
    fn = libc.statx
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p]
    fn.restype = ctypes.c_int
    out = ctypes.create_string_buffer(256)
    if fn(fd, b'', AT_EMPTY_PATH, STATX_BASIC_STATS | STATX_DIOALIGN | STATX_MNT_ID, out) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    raw = out.raw
    mask = struct.unpack_from('<I', raw, 0)[0]
    if mask & (STATX_DIOALIGN | STATX_MNT_ID) != STATX_DIOALIGN | STATX_MNT_ID:
        raise DirectHashRejected('STATX_DIOALIGN/MNT_ID unavailable; no guessed fallback')
    info = os.fstat(fd)
    if struct.unpack_from('<Q', raw, 32)[0] != info.st_ino or struct.unpack_from('<Q', raw, 40)[0] != info.st_size:
        raise DirectHashRejected('statx/fstat identity mismatch')
    major, minor = struct.unpack_from('<II', raw, 136)
    if (major, minor) != (os.major(info.st_dev), os.minor(info.st_dev)):
        raise DirectHashRejected('statx/fstat device mismatch')
    memory, offset = struct.unpack_from('<II', raw, 152)
    mount_id = struct.unpack_from('<Q', raw, 144)[0]
    return Alignment(memory, offset, mount_id).validate()


class AlignedBuffer:
    """Anonymous mapping only. All exported views close before the mapping."""
    live_count = 0

    def __init__(self, length, alignment):
        if length <= 0 or alignment <= 0 or alignment > MAX_ALIGNMENT or alignment & (alignment - 1):
            raise DirectHashRejected('Invalid buffer geometry')
        self.mapping = mmap.mmap(-1, length + alignment)
        base = ctypes.addressof(ctypes.c_char.from_buffer(self.mapping))
        shift = (-base) % alignment
        self.address = base + shift
        self.view = memoryview(self.mapping)[shift:shift + length]
        self.closed = False
        AlignedBuffer.live_count += 1
        if self.address % alignment:
            self.close()
            raise DirectHashRejected('Actual address is not aligned')

    def close(self):
        if not self.closed:
            self.view.release()
            self.mapping.close()
            self.closed = True
            AlignedBuffer.live_count -= 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def check_budget(deadline, clock=time.monotonic):
    if deadline is not None and clock() >= deadline:
        raise TimeoutError('Direct hash deadline exceeded; no fallback')


def hash_stream(size, view, read_at, offset_alignment, *, block=BLOCK,
                deadline=None, clock=time.monotonic, max_interrupts=3):
    """Algorithm core; injected reader is used only for offline fault tests.

    Every requested offset/count is aligned. Final count may exceed EOF, but
    exactly remaining actual bytes enter SHA; nonfinal short reads are rejected.
    """
    if not isinstance(size, int) or size < 0 or offset_alignment <= 0 or block % offset_alignment or len(view) < block:
        raise DirectHashRejected('Invalid stream geometry')
    hasher = hashlib.sha256()
    offset = calls = interrupts = 0
    while offset < size:
        check_budget(deadline, clock)
        remaining = size - offset
        requested = min(block, ((remaining + offset_alignment - 1) // offset_alignment) * offset_alignment)
        if offset % offset_alignment or requested % offset_alignment:
            raise DirectHashRejected('Unaligned request')
        target = view[:requested]
        try:
            while True:
                check_budget(deadline, clock)
                try:
                    count = read_at(target, offset)
                    calls += 1
                    break
                except InterruptedError:
                    interrupts += 1
                    if interrupts > max_interrupts:
                        raise DirectHashRejected('EINTR retry bound exceeded')
            check_budget(deadline, clock)
            expected = min(requested, remaining)
            if type(count) is not int or count != expected:
                raise DirectHashRejected('Short read/early EOF/growing file: expected=' + str(expected) + ' observed=' + str(count))
            payload = target[:count]
            try:
                hasher.update(payload)
            finally:
                payload.release()
            offset += count
        finally:
            target.release()
    check_budget(deadline, clock)
    return dict(sha256=hasher.hexdigest(), bytes_hashed=offset, successful_reads=calls,
                interrupted_reads=interrupts, buffered_fallback=False)


def direct_sha256(path, *, enabled=False, expected_sha256=None, deadline=None):
    if not enabled:
        raise DirectHashRejected('Direct hashing disabled by default')
    require_linux()
    path = os.fspath(path)
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise DirectHashRejected('Require non-symlink regular file with one link')
    flags = os.O_RDONLY | os.O_DIRECT | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        if identity(os.fstat(fd)) != identity(before):
            raise DirectHashRejected('Path/fd identity changed before read')
        alignment = alignment_for_fd(fd)
        with AlignedBuffer(BLOCK, alignment.memory) as buffer:
            result = hash_stream(before.st_size, buffer.view,
                lambda target, offset: os.preadv(fd, [target], offset), alignment.offset, deadline=deadline)
        if identity(os.fstat(fd)) != identity(before) or identity(os.stat(path, follow_symlinks=False)) != identity(before):
            raise DirectHashRejected('File identity changed during read')
        if expected_sha256 is not None and result['sha256'] != expected_sha256:
            raise DirectHashRejected('Full SHA differs')
        result.update(alignment=dict(memory=alignment.memory, offset=alignment.offset, mount_id=alignment.mount_id),
                      identity=list(identity(before)), flags=flags,
                      direct_mode_proven=False, scope='Aligned API only; residency gate required separately')
        return result
    finally:
        os.close(fd)
