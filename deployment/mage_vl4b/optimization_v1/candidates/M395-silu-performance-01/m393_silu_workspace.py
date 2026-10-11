"""Disabled isolated CPU component; no model/runtime/PL integration."""
from contextlib import contextmanager
import threading
import numpy as np


class SiluWorkspace:
    def __init__(self, shape, *, enabled=False):
        if not enabled:
            raise RuntimeError('M393 disabled by default')
        if tuple(shape) not in ((30,9728),(159,9728)):
            raise ValueError('Only fixed30 text or fixed159 video geometry admitted')
        self._buffer = np.empty(shape, dtype=np.float32)
        self._lock = threading.Lock()
        self._active = False
        self._retained = False
        self._closed = False

    @contextmanager
    def lease(self, gate, up):
        # Caller owns the borrowed result until all synchronous consumers,
        # packing/parsing futures and retries are finished. Exceptions retain it.
        with self._lock:
            if self._closed or self._active or self._retained:
                raise RuntimeError('Workspace unavailable; do not reuse/free')
            out = self._buffer
            for value in (gate, up):
                if not isinstance(value, np.ndarray) or value.dtype != np.float32:
                    raise ValueError('Inputs must already be FP32 arrays')
                if value.shape != out.shape or np.shares_memory(value, out):
                    raise ValueError('Shape differs or input aliases workspace')
            self._active = True
        try:
            # Exactly the frozen operation order, without clipping, fusion or
            # reciprocal substitution. No modification of either input.
            np.negative(gate, out=out)
            np.exp(out, out=out)
            np.add(np.float32(1.0), out, out=out)
            np.divide(gate, out, out=out)
            np.multiply(out, up, out=out)
            yield out
        except BaseException:
            with self._lock:
                self._retained = True
            raise
        else:
            with self._lock:
                self._active = False

    def close(self):
        with self._lock:
            if self._active or self._retained:
                raise RuntimeError('Consumer failure/busy: retain workspace')
            self._buffer = None
            self._closed = True
