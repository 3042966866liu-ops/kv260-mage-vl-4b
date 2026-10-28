"""Lossless bounded diagnostic archives, outside both arms' TTFT intervals.

Small identity/sample files keep the original atomic writer. Large diagnostic
JSON is serialized identically, gzip-compressed and atomically saved to disk.
No raw observations are discarded; raw and archive hashes bind each member.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path

COMPRESSED = frozenset(('WEIGHT_STAGE_PROFILE.json', 'PARSER_PROFILE.json',
                        'PHYSICAL_TRANSACTIONS.json', 'STRICT_VISUAL_COMPLETION.json'))


class LogBudget:
    def __init__(self, root, original, record, *, limit=2 << 20, reserve=64 << 20):
        self.root = Path(root).resolve()
        self.original, self.record = original, record
        self.limit, self.reserve, self.used, self.count = limit, reserve, 0, 0
        self.members = []
        assert self.root.stat().st_dev != Path('/dev/shm').stat().st_dev

    def save(self, path, value):
        path = Path(path)
        assert path.resolve().is_relative_to(self.root) and not path.exists()
        raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
        assert len(raw) <= 8 << 20
        compressed = path.name in COMPRESSED
        payload = gzip.compress(raw, compresslevel=6, mtime=0) if compressed else raw
        target = path.with_suffix('.json.gz') if compressed else path
        assert not target.exists() and not target.with_suffix('.partial').exists()
        assert self.used + len(payload) <= self.limit, 'Frozen2MiB diagnostic bound reached'
        fs = os.statvfs(str(self.root))
        assert fs.f_bavail * fs.f_frsize >= len(payload) + self.reserve, 'Persistent64MiB reserve unavailable'
        if compressed:
            part = target.with_suffix('.partial')
            with part.open('xb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            assert not target.exists()
            os.rename(part, target)
        else:
            self.original(target, value)
        assert target.stat().st_size == len(payload)
        self.used += len(payload)
        self.count += 1
        self.members.append(dict(path=target.relative_to(self.root).as_posix(),
                                 bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                                 raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(), gzip=compressed))
        self.record['persistent_log_budget'] = dict(limit_bytes=self.limit, reserve_bytes=self.reserve,
            written_bytes=self.used, files=self.count, TTFT_interval_excluded=True,
            serialization_unchanged=True, lossless_compression=True, members=self.members)


def read_saved(path):
    path = Path(path)
    if path.name in COMPRESSED:
        return json.loads(gzip.decompress(path.with_suffix('.json.gz').read_bytes()))
    return json.loads(path.read_bytes())
