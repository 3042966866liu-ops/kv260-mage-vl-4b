"""Explicit PS-only diagnostic release, never a PL/CMA resource manager.

Caller transfers the sole vision-runtime reference in a one-element holder.
Close failure leaves that reference intact. A successful close is not proof of
memory release: weakref and current RSS are reported separately.
"""
import ctypes
import gc
from pathlib import Path
import weakref


def memory_snapshot(proc=Path('/proc')):
    status = {}
    for line in (proc/'self/status').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in ('VmRSS','RssAnon','RssFile','RssShmem','VmSwap','VmHWM'):
            status[key] = int(value.split()[0]) * 1024
    mem = {}
    for line in (proc/'meminfo').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in ('MemAvailable','MemFree','Cached','SReclaimable','CmaFree','SwapFree'):
            mem[key] = int(value.split()[0]) * 1024
    return dict(process_bytes=status,system_bytes=mem)


def glibc_trim():
    """Return free heap pages where libc permits; no drop_caches or madvise."""
    libc = ctypes.CDLL(None)
    fn = getattr(libc, 'malloc_trim', None)
    if fn is None:
        return dict(supported=False,called=False)
    fn.argtypes=[ctypes.c_size_t];fn.restype=ctypes.c_int
    return dict(supported=True,called=True,return_code=int(fn(0)))


def release_vision(holder, *, snapshot=memory_snapshot, trim=False, trimmer=glibc_trim):
    if len(holder)!=1 or holder[0] is None:
        raise ValueError('Expected one owned PS vision runtime')
    before=snapshot()
    reference=weakref.ref(holder[0])
    holder[0].close()  # Fail closed: do not drop reference when close fails.
    holder.clear()
    collected=gc.collect()
    after_gc=snapshot()
    trim_evidence=trimmer() if trim else dict(called=False)
    return dict(before=before,after_gc=after_gc,after=snapshot(),gc_collected=collected,
                object_released=reference() is None,trim=trim_evidence,
                scope='PS vision only; no overlay, DMA, CMA or kernel changes')
