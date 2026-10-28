#!/usr/bin/env python3
"""Monotonic NumPy allocator over the fixed DT-reserved Direct-DDR pool."""

from __future__ import annotations

import fcntl
import mmap
import os
import threading
from dataclasses import dataclass

import numpy as np


PAGE_BYTES = 4096
# Private _IO(0xA7, 0x01).  Do not reuse 0x5452: Linux treats it as FIOASYNC
# in the generic VFS layer before the misc driver's unlocked_ioctl is reached.
SYNC_IOCTL = 0xA701
POOL_BASE = 0x808000000
POOL_SIZE = 0x68000000
ENV_BASE = "TELLME_RESERVED_DDR_BASE"
ENV_SIZE = "TELLME_RESERVED_DDR_SIZE"
ENV_DEVICE = "TELLME_RESERVED_DDR_DEVICE"


def align_up(value: int, alignment: int = PAGE_BYTES) -> int:
    value = int(value)
    alignment = int(alignment)
    if value < 0 or alignment <= 0 or alignment & (alignment - 1):
        raise ValueError("invalid alignment request")
    return (value + alignment - 1) & -alignment


@dataclass(frozen=True)
class AllocationRecord:
    ordinal: int
    physical_address: int
    requested_bytes: int
    mapped_bytes: int


class ReservedDDRBuffer(np.ndarray):
    def __new__(cls, shape, dtype, *, mapping, offset, device_address, pool):
        result = np.ndarray.__new__(
            cls, shape=shape, dtype=dtype, buffer=mapping, offset=int(offset)
        )
        result.device_address = int(device_address)
        result.physical_address = int(device_address)
        result.coherent = True
        result.pool = pool
        result.freed = False
        return result

    def __array_finalize__(self, source):
        if source is None or not hasattr(source, "pool"):
            return
        self.pool = source.pool
        self.coherent = True
        self.freed = getattr(source, "freed", False)
        delta = self.__array_interface__["data"][0] - source.__array_interface__["data"][0]
        self.device_address = int(source.device_address) + delta
        self.physical_address = self.device_address

    def sync_to_device(self):
        self.pool.sync()

    def sync_from_device(self):
        self.pool.sync()

    def flush(self):
        self.sync_to_device()

    def invalidate(self):
        self.sync_from_device()

    def freebuffer(self):
        self.freed = True


class ReservedDDRPool:
    def __init__(self, base: int, size: int, device: str):
        self.base = int(base)
        self.size = int(size)
        self.device = str(device)
        if self.base != POOL_BASE or self.size != POOL_SIZE:
            raise ValueError("reserved-DDR pool must match the fixed driver window")
        self.end_exclusive = self.base + self.size
        self._fd = os.open(self.device, os.O_RDWR | os.O_SYNC)
        try:
            self._mapping = mmap.mmap(
                self._fd,
                self.size,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                offset=0,
            )
        except Exception:
            os.close(self._fd)
            self._fd = -1
            raise
        self._cursor = self.base
        self._records: list[AllocationRecord] = []
        self._lock = threading.Lock()
        self._closed = False

    def allocate(self, shape, dtype="u4", target=None, **kwargs):
        if target is not None:
            raise ValueError("reserved-DDR weights accept no PYNQ target")
        unexpected = set(kwargs) - {"cacheable"}
        if unexpected:
            raise TypeError(f"unsupported reserved-DDR options: {sorted(unexpected)}")
        dtype = np.dtype(dtype)
        elements = int(np.prod(shape, dtype=np.int64)) if np.ndim(shape) else int(shape)
        requested = elements * dtype.itemsize
        if requested <= 0:
            raise ValueError("reserved-DDR allocation must be non-empty")
        mapped = align_up(requested)
        with self._lock:
            start = align_up(self._cursor)
            stop = start + mapped
            if stop > self.end_exclusive:
                raise MemoryError(
                    f"reserved-DDR exhausted request={requested} cursor=0x{start:x}"
                )
            record = AllocationRecord(len(self._records), start, requested, mapped)
            self._records.append(record)
            self._cursor = stop
        result = ReservedDDRBuffer(
            shape,
            dtype,
            mapping=self._mapping,
            offset=start - self.base,
            device_address=start,
            pool=self,
        )
        result.reserved_ddr_record = record
        return result

    def sync(self):
        if self._closed:
            raise RuntimeError("reserved-DDR pool is closed")
        fcntl.ioctl(self._fd, SYNC_IOCTL, 0)

    def summary(self) -> dict[str, int | str]:
        used = self._cursor - self.base
        return {
            "status": "PASS",
            "allocator": "dt-reserved-writecombine-v1",
            "device": self.device,
            "base": self.base,
            "size_bytes": self.size,
            "end_exclusive": self.end_exclusive,
            "allocation_count": len(self._records),
            "used_bytes": used,
            "free_bytes": self.size - used,
        }

    def close(self):
        if self._closed:
            return
        self.sync()
        try:
            self._mapping.close()
        except BufferError:
            pass
        os.close(self._fd)
        self._fd = -1
        self._closed = True


def install_reserved_ddr_pool_from_env() -> ReservedDDRPool | None:
    raw_base = os.environ.get(ENV_BASE)
    raw_size = os.environ.get(ENV_SIZE)
    raw_device = os.environ.get(ENV_DEVICE)
    present = [value is not None for value in (raw_base, raw_size, raw_device)]
    if not any(present):
        return None
    if not all(present):
        raise RuntimeError(f"{ENV_BASE}, {ENV_SIZE}, and {ENV_DEVICE} must be set together")
    return ReservedDDRPool(int(raw_base, 0), int(raw_size, 0), raw_device)
