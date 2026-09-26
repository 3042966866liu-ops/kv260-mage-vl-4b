"""Offline-tested, byte-bounded exact vision cache. No KV/approximate reuse.

Only suitable for a deterministic vision encoder independent of prompt text.
Cache the ENTIRE input window (not independent frame features with cross-frame
attention). Caller supplies all semantic dependencies via strict identity.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
import threading

import numpy as np


@dataclass(frozen=True)
class VisionIdentity:
    model_sha256: str
    weights_sha256: str
    processor_sha256: str
    execution_policy_sha256: str

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("every cache identity must be a lowercase SHA-256")


def vision_key(identity: VisionIdentity, frames: np.ndarray, *, positions: np.ndarray,
               attention_mask: np.ndarray) -> str:
    digest = hashlib.sha256(json.dumps(asdict(identity), sort_keys=True).encode())
    for name, raw in (("frames", frames), ("positions", positions), ("mask", attention_mask)):
        arr = np.asarray(raw)
        if arr.size == 0 or arr.dtype.kind not in "biuf" or not np.isfinite(arr).all():
            raise ValueError("cache inputs must be nonempty finite numeric arrays")
        arr = np.ascontiguousarray(arr)
        header = json.dumps([name, arr.dtype.str, list(arr.shape)], separators=(",", ":")).encode()
        digest.update(len(header).to_bytes(8, "little"))
        digest.update(header)
        digest.update(arr.tobytes())
    return digest.hexdigest()


class ExactVisionCache:
    """LRU budget covers stored ndarray payload only, not Python/RSS overhead.

    Copy on put/get prevents caller mutation. Lock protects shared operations;
    this is NOT a single-flight encoder or a production runtime integration.
    """
    def __init__(self, max_bytes: int, max_entries: int = 8):
        if type(max_bytes) is not int or max_bytes <= 0 or type(max_entries) is not int or max_entries <= 0:
            raise ValueError("positive cache limits required")
        self.max_bytes, self.max_entries = max_bytes, max_entries
        self._items: OrderedDict[str, np.ndarray] = OrderedDict()
        self._bytes = 0
        self._lock = threading.RLock()

    @property
    def bytes_used(self) -> int:
        with self._lock:
            return self._bytes

    def get(self, key: str) -> np.ndarray | None:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key].copy()

    def put(self, key: str, value: np.ndarray) -> bool:
        arr = np.asarray(value)
        if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("invalid cache key")
        if arr.size == 0 or arr.dtype.kind not in "fiu" or not np.isfinite(arr).all():
            raise ValueError("cache value must be finite numeric features")
        with self._lock:
            # A rejected replacement must not leave a stale same-key value.
            previous = self._items.pop(key, None)
            if previous is not None:
                self._bytes -= previous.nbytes
            if arr.nbytes > self.max_bytes:
                return False
            while self._items and (self._bytes + arr.nbytes > self.max_bytes or len(self._items) >= self.max_entries):
                _, old = self._items.popitem(last=False)
                self._bytes -= old.nbytes
            self._items[key] = arr.copy()
            self._bytes += arr.nbytes
            return True
