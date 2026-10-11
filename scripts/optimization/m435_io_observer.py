"""Bounded diagnostic I/O attribution. No cache eviction or model algorithm changes."""
import base64
import ctypes
import hashlib
import os
from pathlib import Path
try:
    import resource
except ImportError:
    resource = None  # Windows tests explicitly inject counters; never a capability fallback.
import stat
import threading
import time


def identity(s):
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_nlink]


def io_snapshot():
    return {k: int(v.strip()) for k, v in
            (line.split(':', 1) for line in Path('/proc/self/io').read_text(encoding='ascii').splitlines())}


def counters():
    if resource is None:
        raise RuntimeError('Linux process counters required')
    return dict(io=io_snapshot(), major=resource.getrusage(resource.RUSAGE_SELF).ru_majflt)


def delta(a, b):
    return dict(io={k: b['io'][k] - a['io'][k] for k in a['io']}, major=b['major'] - a['major'])


def residency(path):
    """Untouched read-only mapping. Owner criterion avoids Linux privacy all-ones."""
    if os.name != 'posix' or not hasattr(os, 'geteuid'):
        raise RuntimeError('Linux owner-valid mincore required')
    path = Path(path)
    before = path.lstat()
    owner_valid = before.st_uid == os.geteuid()
    caps = next(line.split(':', 1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))
    cap_fowner = bool(int(caps, 16) & (1 << 3))
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not (owner_valid or cap_fowner):
        raise RuntimeError('Residency ownership/type unproven: ' + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    address = None
    try:
        if identity(os.fstat(fd)) != identity(before) or before.st_size <= 0:
            raise RuntimeError('Residency file identity/length differs')
        page = os.sysconf('SC_PAGESIZE')
        if page <= 0:
            raise RuntimeError('Invalid page size')
        pages = (before.st_size + page - 1) // page
        if pages > 600000:
            raise RuntimeError('Residency probe budget exceeded')
        libc = ctypes.CDLL(None, use_errno=True)
        libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_long]
        libc.mmap.restype = ctypes.c_void_p
        libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        libc.mincore.restype = ctypes.c_int
        libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        libc.munmap.restype = ctypes.c_int
        address = libc.mmap(None, before.st_size, 1, 1, fd, 0)  # PROT_READ/MAP_SHARED; no populate
        if address == ctypes.c_void_p(-1).value or address is None:
            address = None
            raise OSError(ctypes.get_errno(), 'mmap')
        vector = (ctypes.c_ubyte * pages)()
        if libc.mincore(address, before.st_size, vector):
            raise OSError(ctypes.get_errno(), 'mincore')
        bits = bytearray((pages + 7) // 8)
        count = 0
        for i, value in enumerate(vector):
            if value & 1:
                bits[i // 8] |= 1 << (i % 8)
                count += 1
        if identity(os.fstat(fd)) != identity(before) or identity(path.lstat()) != identity(before):
            raise RuntimeError('Residency file changed')
        return dict(path=str(path), identity=identity(before), owner_uid=before.st_uid,
                    euid=os.geteuid(), permission_proven=True, owner_valid=owner_valid,
                    cap_fowner_effective=cap_fowner, cap_eff_hex=caps, page_bytes=page,
                    pages=pages, resident_pages=count, bits_b64=base64.b64encode(bits).decode('ascii'),
                    bits_sha256=hashlib.sha256(bits).hexdigest(), snapshot_not_locked=True)
    finally:
        try:
            if address is not None and libc.munmap(address, before.st_size):
                raise OSError(ctypes.get_errno(), 'munmap')
        finally:
            os.close(fd)


def residency_change(a, b):
    if (a['identity'] != b['identity'] or a['pages'] != b['pages']
            or a['page_bytes'] != b['page_bytes']
            or not a['permission_proven'] or not b['permission_proven']):
        raise RuntimeError('Residency comparison identity/permission differs')
    x = base64.b64decode(a['bits_b64'], validate=True)
    y = base64.b64decode(b['bits_b64'], validate=True)
    if len(x) != len(y) or len(x) != (a['pages'] + 7) // 8:
        raise RuntimeError('Residency vector length differs')
    if hashlib.sha256(x).hexdigest() != a['bits_sha256'] or hashlib.sha256(y).hexdigest() != b['bits_sha256']:
        raise RuntimeError('Residency bitmap digest differs')
    def count(v):
        return bin(v).count('1')
    return dict(gained_pages=sum(count(v & (~u & 255)) for u, v in zip(x, y)),
                lost_pages=sum(count(u & (~v & 255)) for u, v in zip(x, y)),
                before_resident=a['resident_pages'], after_resident=b['resident_pages'],
                page_bytes=a['page_bytes'])


class ReadFile:
    def __init__(self, file, path, observer, group):
        self.file, self.path, self.observer, self.group = file, path, observer, group
        self.expected_identity = identity(file.fstat()) if hasattr(file, 'fstat') else identity(os.fstat(file.fileno()))
        if self.expected_identity != observer.identities[str(path)]:
            file.close()
            raise RuntimeError('Opened weight file identity differs')

    def __getattr__(self, name):
        return getattr(self.file, name)

    def __enter__(self):
        self.file.__enter__()
        return self

    def __exit__(self, *args):
        return self.file.__exit__(*args)

    def read(self, size=-1):
        obs = self.observer
        if threading.get_ident() != obs.thread or obs.phase not in ('vision', 'prefill'):
            raise RuntimeError('Unexpected concurrent/phase weight read')
        if (self.group == 'visual') != (obs.phase == 'vision') or size <= 0 or size > 16 << 20:
            raise RuntimeError('Weight read contract/phase differs')
        offset = self.file.tell()
        before = counters()
        started = time.perf_counter_ns()
        answer = self.file.read(size)
        elapsed = time.perf_counter_ns() - started
        after = counters()
        row = dict(request=obs.request, phase=obs.phase, group=self.group, path=str(self.path),
                   offset=offset, requested_bytes=size, returned_bytes=len(answer), elapsed_ns_diagnostic=elapsed,
                   **delta(before, after))
        obs.reads.append(row)
        if (len(answer) != size or identity(os.fstat(self.file.fileno())) != self.expected_identity
                or identity(self.path.lstat()) != self.expected_identity):
            raise RuntimeError('Weight read short/changed; original owner must close safely')
        return answer


class IOObserver:
    def __init__(self, files, store, result):
        self.files = {str(Path(p).resolve()): group for p, group in files.items()}
        self.identities = {p: identity(Path(p).lstat()) for p in self.files}
        self.thread = threading.get_ident()
        self.store, self.result = store, result
        self.phase, self.request = 'none', 0
        self.reads, self.decodes, self.snapshots = [], [], []
        self.entered = False

    def snapshot(self, label):
        rows = [dict(group=self.files[p], **residency(p)) for p in sorted(self.files)]
        if any(row['identity'] != self.identities[row['path']] for row in rows):
            raise RuntimeError('File changed across request boundaries')
        out = dict(request=self.request, label=label, counters=counters(), files=rows)
        self.snapshots.append(out)
        return out

    def __enter__(self):
        if self.entered:
            raise RuntimeError('Nested observer')
        self.original_open, self.original_decode = Path.open, self.store.decode
        obs = self
        def observed_open(path, *args, **kwargs):
            name = str(path.resolve())
            group = obs.files.get(name)
            if group is None:
                return obs.original_open(path, *args, **kwargs)
            mode = args[0] if args else kwargs.get('mode', 'r')
            if mode != 'rb':
                raise RuntimeError('Observed weights are read-only')
            if identity(path.lstat()) != obs.identities[name]:
                raise RuntimeError('Weight pathname identity changed')
            return ReadFile(obs.original_open(path, *args, **kwargs), Path(name), obs, group)
        def observed_decode(name):
            if obs.phase != 'vision' or threading.get_ident() != obs.thread:
                raise RuntimeError('Unexpected decode phase/thread')
            before = counters(); started = time.perf_counter_ns()
            answer = obs.original_decode(name)
            after = counters()
            obs.decodes.append(dict(request=obs.request, name=name,
                                    elapsed_ns_diagnostic=time.perf_counter_ns() - started, **delta(before, after)))
            return answer
        self.open_hook, self.decode_hook = observed_open, observed_decode
        Path.open, self.store.decode = observed_open, observed_decode
        self.entered = True
        return self

    def __exit__(self, *args):
        intact = Path.open is self.open_hook and self.store.decode is self.decode_hook
        Path.open, self.store.decode = self.original_open, self.original_decode
        self.entered = False
        self.result['io_observer_hooks_restored'] = True
        self.result['read_observation'] = dict(reads=self.reads, decodes=self.decodes, snapshots=self.snapshots,
            attribution='Process read_bytes intervals, may include filesystem readahead; not sector trace',
            residency='Owner-valid snapshots; unlocked and not proof of eviction cause',
            cache_eviction=False, additional_weight_cache=False)
        if not intact:
            raise RuntimeError('Observer hook identity changed')


def linux_probe_fixture(folder):
    """New, owned sparse inode then one buffered page: permission-valid positive control."""
    import tempfile
    page = os.sysconf('SC_PAGESIZE')
    with tempfile.TemporaryDirectory(prefix='m435-probe-', dir=folder) as temp:
        path = Path(temp) / 'probe.bin'
        with path.open('xb') as file:
            file.truncate(4 * page)
        before = residency(path)
        if before['resident_pages']:
            raise RuntimeError('New sparse probe unexpectedly resident; UNPROVEN')
        with path.open('r+b', buffering=0) as file:
            file.write(b'P' * page); os.fsync(file.fileno())
        after = residency(path)
        if not after['resident_pages'] or not (base64.b64decode(after['bits_b64'])[0] & 1):
            raise RuntimeError('Residency positive control unproven')
        proof = dict(owner_valid=True, sparse_initial_resident=before['resident_pages'],
                     buffered_write_resident=after['resident_pages'], first_page_observed=True,
                     fixture_bytes=4 * page, maps_and_fds_closed=True)
    proof['fixture_removed'] = not path.exists()
    return proof
