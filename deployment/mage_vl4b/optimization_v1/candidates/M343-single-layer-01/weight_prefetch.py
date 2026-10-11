"""One-window-ahead PS staging using the unchanged copy implementation.

This component owns only its second four-buffer bank. Its caller must enforce
the board gate order, environment, frozen source identities and numerical gates.
No worker reads MMIO or changes runtime counters. No arithmetic/packet change.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import hashlib
import json
import time

import numpy as np
from board_safety import safe_to_release


class RetainedBuffersError(RuntimeError):
    """Caller must retain runtime/session and enter explicit recovery."""


def chain_identity(chain):
    return hashlib.sha256(json.dumps(chain, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class WeightPrefetchSession:
    def __init__(self, runtime, base, plan, *, cma_free_bytes, reserve_bytes=64 << 20,
                 timeout_s=60.0):
        if runtime.weight_mode != 'staged-low-cma':
            raise ValueError('Prefetch requires the accepted staged mode')
        if not plan or len(runtime.staged_buffers) != 4:
            raise ValueError('Expected nonempty plan and four original buffers')
        if type(cma_free_bytes) is not int or cma_free_bytes < 0 or reserve_bytes < 0:
            raise ValueError('Explicit valid CMA measurement required')
        self.runtime, self.base = runtime, base
        self.maximum = int(runtime.maximum_weight_window_bytes)
        self.extra_bytes = 4 * self.maximum
        if self.maximum <= 0 or cma_free_bytes < self.extra_bytes + reserve_bytes:
            raise MemoryError('CMA free space fails extra-bank plus reserve requirement')
        self.plan = []
        for layout, source in plan:
            # Freeze the complete descriptor identity before starting any worker.
            chain = json.loads(json.dumps(source))
            words, size = base.chain_window(layout, chain)
            if len(layout.manifest['files']) != 4 or not 0 < size <= self.maximum:
                raise ValueError('Weight window exceeds frozen bank geometry')
            self.plan.append((layout, chain, chain_identity(chain), words, size))
        self.timeout_s = timeout_s
        self.index = 0
        self.extra = []
        self.future = self.executor = None
        self.prior = None
        self.had_instance_method = '_stage' in vars(runtime)
        self.original = runtime._stage
        self.closed = self.entered = False
        self.record = dict(status='PREPARED_NOT_RUN', stages=0, submissions=0,
                           extra_bank_bytes=self.extra_bytes, cma_free_before=cma_free_bytes,
                           reserve_bytes=reserve_bytes, worker_compute_ms=0.0,
                           foreground_wait_ms=0.0, total_weight_bytes=0,
                           performance_pass=False, hardware_contract_changed=False)

    def _idle(self):
        snapshot = self.base.transaction_snapshot(self.runtime.kernel, self.runtime.dma)
        if not safe_to_release(snapshot):
            self.record.update(status='FAIL_UNSAFE_DEVICE_RETAINED', failure_snapshot=snapshot)
            raise RetainedBuffersError('Kernel/DMA not idle; banks retained: '+json.dumps(snapshot))
        return snapshot

    def __enter__(self):
        if self.entered: raise RuntimeError('One-use session')
        self.entered = True
        self._idle()
        try:
            for _ in range(4):
                buffer = self.runtime.allocate((self.maximum,), dtype=np.uint8)
                self.extra.append(buffer)  # Retain even if address validation fails.
                address = int(self.base.physical_address(buffer))
                if address < 0 or address + self.maximum > self.base.LOW_END:
                    raise RuntimeError('Additional weight buffer outside low DDR')
            self.banks = (self.runtime.staged_buffers, self.extra)
            self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='m340-weight')
            self.prior = vars(self.runtime).get('_stage')
            self.runtime._stage = self.stage
            # Retain ownership through failure even after a caller leaves scope.
            self.runtime._m340_weight_owner = self
            self.record['status'] = 'RUNNING'
            self._submit(0)
            return self
        except BaseException:
            self.close()
            raise

    def _copy(self, index):
        layout, chain, identity, words, size = self.plan[index]
        started = time.monotonic()
        for item, buffer in zip(layout.manifest['files'], self.banks[index & 1]):
            self.base.copy_window_to_buffer(layout.root / item['path'], words * 16, size, buffer)
        return dict(index=index, identity=identity, words=words, bytes=4 * size,
                    compute_ms=(time.monotonic()-started)*1000.0)

    def _submit(self, index):
        self.future = self.executor.submit(self._copy, index)
        self.record['submissions'] += 1

    def stage(self, layout, chain):
        if self.closed or self.index >= len(self.plan):
            raise RuntimeError('Stage outside frozen plan')
        expected_layout, _, identity, words, size = self.plan[self.index]
        if layout is not expected_layout or chain_identity(chain) != identity:
            raise RuntimeError('Unexpected chain/layout; no fallback or speculative overwrite')
        # All preceding PL calls and adaptive retries must have completed before
        # _stage is called again. Validate BOTH DMA paths and the kernel here.
        self._idle()
        started = time.monotonic()
        try:
            completed = self.future.result(timeout=self.timeout_s)
        except TimeoutError as exc:
            self.record['status'] = 'FAIL_WORKER_TIMEOUT_RETAINED'
            raise RetainedBuffersError('Prefetch worker timed out; buffers retained') from exc
        self.record['foreground_wait_ms'] += (time.monotonic()-started)*1000.0
        if completed['index'] != self.index or completed['identity'] != identity:
            raise RuntimeError('Worker identity mismatch')
        current = self.index
        self.index += 1
        self.record['stages'] += 1
        self.record['worker_compute_ms'] += completed['compute_ms']
        self.record['total_weight_bytes'] += completed['bytes']
        self.runtime.stage_bytes += completed['bytes']
        # Preserve stage_ms as TOTAL preparation work, not critical-path time.
        self.runtime.stage_ms += completed['compute_ms']
        if self.index < len(self.plan): self._submit(self.index)
        return self.banks[current & 1], words

    def close(self):
        if self.closed: return
        if self.entered and (self.prior is not None or '_stage' in vars(self.runtime)):
            if self.had_instance_method: self.runtime._stage = self.prior if self.prior is not None else self.original
            else: vars(self.runtime).pop('_stage', None)
        if self.future is not None:
            try:
                self.future.result(timeout=self.timeout_s)
            except TimeoutError as exc:
                if self.executor: self.executor.shutdown(wait=False, cancel_futures=True)
                self.record['status'] = 'FAIL_WORKER_TIMEOUT_RETAINED'
                raise RetainedBuffersError('Cannot release a bank still owned by worker') from exc
            except BaseException:
                # Worker has stopped. The original exception is raised by stage;
                # device ownership is checked independently before releasing.
                pass
        if self.executor: self.executor.shutdown(wait=True, cancel_futures=True)
        if self.extra:
            self.record['release_snapshot'] = self._idle()
            for buffer in reversed(self.extra): buffer.freebuffer()
            self.extra.clear()
        self.closed = True

    def __exit__(self, kind, value, traceback):
        self.close()
        if kind is None and self.index != len(self.plan):
            self.record['status'] = 'FAIL_INCOMPLETE_PLAN'
            raise RuntimeError('Caller did not consume complete frozen plan')
        if kind is None: self.record['status'] = 'COMPLETE_COMPONENT_ONLY'
        elif self.record['status'] == 'RUNNING': self.record['status'] = 'FAIL_CALLER'
        return False
