"""Opt-in single PS slot. No allocator, MMIO or CMA access on its worker.

Caller owns environment, actual memory measurements, a completed same-overlay
transaction prerequisite and fail-closed retention of the original runtime.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time

from board_safety import safe_to_release

MAXIMUM_PER_PORT = 6963200
RESERVE = 64 << 20

class RetainedPSResourcesError(RuntimeError):
    """Retain the owner, worker, runtime, original DMA bank and process."""

def chain_identity(chain):
    return hashlib.sha256(json.dumps(chain, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def file_identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_nlink)

def read_exact_into(stream, target, offset, *, deadline, max_eintr=3):
    """A legal positive short read continues; EOF/invalid count never passes."""
    stream.seek(offset)
    cursor = interruptions = calls = 0
    while cursor < len(target):
        if time.monotonic() >= deadline: raise TimeoutError('PS read deadline exceeded')
        part = target[cursor:]
        try:
            try: count = stream.readinto(part)
            except InterruptedError:
                interruptions += 1
                if interruptions > max_eintr: raise RuntimeError('PS read EINTR limit exceeded')
                continue
        finally: part.release()
        calls += 1
        if type(count) is not int or count <= 0 or count > len(target) - cursor:
            raise RuntimeError('PS read EOF or invalid short-read progress')
        cursor += count
    if time.monotonic() >= deadline: raise TimeoutError('PS read deadline exceeded')
    return dict(bytes=cursor, read_calls=calls, interruptions=interruptions)

class PSReadAheadSession:
    def __init__(self, runtime, base, plan, *, enabled=False,
                 memory_reader=None, completed_transaction_snapshot=None,
                 timeout_s=60.0):
        if not enabled: raise ValueError('PS read-ahead disabled by default')
        if not callable(memory_reader): raise ValueError('Actual memory reader required')
        if not safe_to_release(completed_transaction_snapshot or {}):
            raise ValueError('Completed same-overlay transaction evidence required; DMA zero is invalid')
        if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError('Positive finite timeout required')
        if runtime.weight_mode != 'staged-low-cma' or len(runtime.staged_buffers) != 4 or not plan:
            raise ValueError('Nonempty staged four-port runtime required')
        maximum = runtime.maximum_weight_window_bytes
        if type(maximum) is not int or not 0 < maximum <= MAXIMUM_PER_PORT:
            raise ValueError('Window exceeds frozen PS payload limit')
        if any(len(b) < maximum for b in runtime.staged_buffers): raise ValueError('Original bank too small')
        if hasattr(runtime, '_m351_ps_owner'): raise RuntimeError('Runtime already has a PS read owner')
        self.runtime, self.base = runtime, base
        self.memory_reader, self.timeout_s, self.maximum = memory_reader, float(timeout_s), maximum
        self.payload_bytes = 4 * maximum
        self.plan = []
        identities = {}
        for layout, source in plan:
            chain = json.loads(json.dumps(source))
            words, size = base.chain_window(layout, chain)
            if type(words) is not int or words < 0 or type(size) is not int or not 0 < size <= maximum:
                raise ValueError('Invalid frozen window')
            rows = layout.manifest['files']
            if len(rows) != 4: raise ValueError('Exactly four shards required')
            root = Path(layout.root).resolve()
            paths = []
            for port, row in enumerate(rows):
                if row['path'] != 'weights' + str(port) + '.bin': raise ValueError('Shard order differs')
                path = root / row['path']
                s = path.lstat()
                if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_size != row['bytes']:
                    raise ValueError('File identity/size/regular-file check failed')
                if words * 16 + size > s.st_size: raise ValueError('Window outside shard')
                identity = file_identity(s)
                if path in identities and identities[path] != identity: raise RuntimeError('Plan file changed')
                identities[path] = identity
                paths.append((path, identity))
            self.plan.append((layout, chain_identity(chain), words, size, tuple(paths)))
        self._memory(before_payload=True)
        self.index = 0
        self.slot = []
        self.executor = self.future = None
        self.entered = self.closed = self.failed = False
        self.patched = False
        self.had_instance_method = '_stage' in vars(runtime)
        self.original_instance = vars(runtime).get('_stage')
        self.record = dict(status='PREPARED_NOT_RUN', stages=0, submissions=0,
            ps_payload_bytes=self.payload_bytes, extra_cma_allocation_calls=0,
            read_work_ms=0.0, foreground_wait_ms=0.0, foreground_copy_ms=0.0,
            foreground_sync_ms=0.0, total_weight_bytes=0, open_files=0, live_views=0,
            performance_pass=False, hardware_contract_changed=False)

    def _memory(self, before_payload=False):
        row = self.memory_reader()
        required = RESERVE + (self.payload_bytes if before_payload else 0)
        if any(type(row.get(k)) is not int or row[k] < 0 for k in ('CmaFree', 'MemAvailable')):
            raise ValueError('Invalid actual memory observation')
        if row['CmaFree'] < RESERVE or row['MemAvailable'] < required:
            raise MemoryError('PS read-ahead memory reserve unmet')
        return dict(row)

    def _idle(self):
        row = self.base.transaction_snapshot(self.runtime.kernel, self.runtime.dma)
        if not safe_to_release(row):
            self.failed = True
            self.record.update(status='FAIL_DEVICE_RETAINED', failure_snapshot=row)
            raise RetainedPSResourcesError('Original DMA bank/runtime retained; device not safe')
        return row

    def __enter__(self):
        if self.entered: raise RuntimeError('One-use PS session')
        self.entered = True
        self._idle()
        self.runtime._m351_ps_owner = self
        try:
            self.record['memory_before_slot'] = self._memory(before_payload=True)
            self.slot = [bytearray(self.maximum) for _ in range(4)]
            self.record['memory_after_slot'] = self._memory()
            self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='m351-ps-read')
            self.runtime._stage = self.stage
            self.patched = True
            self.record['status'] = 'RUNNING'
            self._submit(0)
            return self
        except BaseException:
            self.close()
            raise

    def _read(self, index):
        _, identity, words, size, paths = self.plan[index]
        started = time.monotonic()
        deadline = started + self.timeout_s
        counts = []
        for port, (path, expected) in enumerate(paths):
            if file_identity(path.lstat()) != expected: raise RuntimeError('PS source identity changed')
            with path.open('rb', buffering=0) as f:
                self.record['open_files'] += 1
                try:
                    observed = file_identity(os.fstat(f.fileno()))
                    if observed != expected: raise RuntimeError('PS opened identity changed: ' + repr((expected, observed)))
                    view = memoryview(self.slot[port])[:size]
                    self.record['live_views'] += 1
                    try: counts.append(read_exact_into(f, view, words * 16, deadline=deadline))
                    finally:
                        view.release()
                        self.record['live_views'] -= 1
                    if file_identity(os.fstat(f.fileno())) != expected or file_identity(path.lstat()) != expected:
                        raise RuntimeError('PS source identity changed during read')
                finally: self.record['open_files'] -= 1
        return dict(index=index, identity=identity, bytes=4 * size, words=words,
                    read_ms=(time.monotonic()-started)*1000.0, counts=counts)

    def _submit(self, index):
        self.future = self.executor.submit(self._read, index)
        self.record['submissions'] += 1

    def stage(self, layout, chain):
        if not self.entered or self.closed or self.failed or self.index >= len(self.plan):
            raise RuntimeError('PS stage outside active frozen plan')
        try:
            expected_layout, identity, words, size, paths = self.plan[self.index]
            if layout is not expected_layout or chain_identity(chain) != identity:
                raise RuntimeError('PS unexpected chain/layout; no fallback')
            self._idle()
            started = time.monotonic()
            try: completed = self.future.result(timeout=self.timeout_s)
            except FutureTimeoutError as exc:
                self.record['status'] = 'FAIL_WORKER_TIMEOUT_RETAINED'
                raise RetainedPSResourcesError('PS worker timeout; owner and original bank retained') from exc
            self.record['foreground_wait_ms'] += (time.monotonic()-started)*1000.0
            if completed['index'] != self.index or completed['identity'] != identity or completed['bytes'] != 4*size or completed['words'] != words:
                raise RuntimeError('PS worker identity/size mismatch')
            self._idle()
            self.record['memory_before_copy'] = self._memory()
            if any(file_identity(path.lstat()) != expected for path, expected in paths):
                raise RuntimeError('PS source identity changed before copy')
            import numpy as np
            copy_ms = sync_ms = 0.0
            for port, buffer in enumerate(self.runtime.staged_buffers):
                started = time.monotonic()
                view = np.frombuffer(self.slot[port], dtype=np.uint8, count=size)
                try: buffer[:size] = view
                finally: del view
                copy_ms += (time.monotonic()-started)*1000.0
                started = time.monotonic()
                buffer.sync_to_device()
                sync_ms += (time.monotonic()-started)*1000.0
            self.index += 1
            self.record['stages'] += 1
            self.record['read_work_ms'] += completed['read_ms']
            self.record['foreground_copy_ms'] += copy_ms
            self.record['foreground_sync_ms'] += sync_ms
            self.record['total_weight_bytes'] += completed['bytes']
            self.runtime.stage_bytes += completed['bytes']
            self.runtime.stage_ms += completed['read_ms'] + copy_ms + sync_ms
            # Only now may the single PS slot be overwritten for the next chain.
            if self.index < len(self.plan): self._submit(self.index)
            return self.runtime.staged_buffers, words
        except BaseException as exc:
            self.failed = True
            self.record['error'] = type(exc).__name__ + ': ' + str(exc)
            if self.record['status'] == 'RUNNING': self.record['status'] = 'FAIL_STAGE_NO_SUBMIT'
            raise

    def close(self):
        if self.closed: return
        if self.future is not None:
            try: self.future.result(timeout=self.timeout_s)
            except FutureTimeoutError as exc:
                # Includes a completed worker TimeoutError: only a still-running
                # future requires retention; an ended failure can be recovered.
                if not self.future.done():
                    self.failed = True
                    self.record['status'] = 'FAIL_WORKER_TIMEOUT_RETAINED'
                    raise RetainedPSResourcesError('Cannot release PS slot still owned by worker') from exc
            except BaseException: pass
        if self.executor: self.executor.shutdown(wait=True, cancel_futures=True)
        if self.entered: self.record['release_snapshot'] = self._idle()
        if self.record['open_files'] or self.record['live_views']:
            raise RetainedPSResourcesError('PS file/view lifecycle not closed')
        if self.patched:
            if self.had_instance_method: self.runtime._stage = self.original_instance
            else: vars(self.runtime).pop('_stage', None)
        if getattr(self.runtime, '_m351_ps_owner', None) is self:
            del self.runtime._m351_ps_owner
        self.slot.clear()
        self.closed = True

    def __exit__(self, kind, value, traceback):
        if kind: self.record['caller_error'] = kind.__name__ + ': ' + str(value)
        self.close()
        if kind is None:
            if self.failed or self.index != len(self.plan):
                self.record['status'] = 'FAIL_INCOMPLETE_PLAN'
                raise RuntimeError('PS caller did not consume complete frozen plan')
            self.record['status'] = 'COMPLETE_COMPONENT_ONLY'
        elif self.record['status'] == 'RUNNING': self.record['status'] = 'FAIL_CALLER'
        return False
