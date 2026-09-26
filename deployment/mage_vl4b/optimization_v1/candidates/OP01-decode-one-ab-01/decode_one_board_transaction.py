"""Bounded experimental transaction; caller owns overlay, lock and quarantine.

Never destroys live DMA buffers on an exception. Keep this object alive when
recovery_required is true; do not unload the overlay or exit its owner process.
"""
import hashlib
import time
import numpy as np
from board_safety import safe_to_release
from decode_one_board_protocol import wait_transaction


class BoardTransaction:
    def __init__(self, kernel, dma, allocate, read_snapshot, waiter=wait_transaction):
        self.kernel, self.dma = kernel, dma
        self.allocate, self.read_snapshot, self.waiter = allocate, read_snapshot, waiter
        self.buffers = []
        self.started = False
        self.recovery_required = False
        self.evidence = {}

    def release_if_safe(self):
        if self.started:
            state = self.read_snapshot()
            self.evidence['release_snapshot'] = state
            if not safe_to_release(state):
                self.recovery_required = True
                return False
        for buffer in reversed(self.buffers):
            buffer.freebuffer()
        self.buffers.clear()
        self.started = False
        return True

    def run(self, fixture, identity):
        if self.buffers or self.started or self.recovery_required:
            raise RuntimeError('Previous transaction not safely released; no retry')
        packet = fixture['packet']
        weights = fixture.get('weights')
        if weights is None:
            weights = bytes(fixture['weight_bytes_per_shard'])
        expected = fixture.get('expected_output', bytes(fixture['output_bytes']))
        if len(expected) != fixture['output_bytes']:
            raise ValueError('Fixture output size mismatch')
        self.evidence = dict(identity=identity, input_bytes=len(packet), output_bytes=len(expected),
                             expected_build=fixture['expected_build'], status='FAIL')
        begin = time.monotonic()
        try:
            for size in [len(weights)] * 4 + [len(packet), len(expected)]:
                self.buffers.append(self.allocate((size,), dtype=np.uint8))
            for buffer in self.buffers[:4]:
                buffer[:] = np.frombuffer(weights, dtype=np.uint8)
                buffer.sync_to_device()
            self.buffers[4][:] = np.frombuffer(packet, dtype=np.uint8)
            self.buffers[4].sync_to_device()
            # Non-reference sentinel catches incomplete output including zero lanes.
            self.buffers[5][:] = 0xA5
            self.buffers[5].sync_to_device()
            for reg, buffer in zip((0x18, 0x24, 0x30, 0x3c), self.buffers[:4]):
                address = getattr(buffer, 'device_address', None)
                if address is None:
                    address = buffer.physical_address
                self.kernel.write(reg, int(address) & 0xffffffff)
                self.kernel.write(reg + 4, int(address) >> 32)
            self.kernel.write(0x80, fixture['config'])
            self.started = True  # transfer can partially launch before raising
            self.dma.recvchannel.transfer(self.buffers[5], nbytes=len(expected))
            self.kernel.write(0, 1)
            self.dma.sendchannel.transfer(self.buffers[4], nbytes=len(packet))
            self.evidence['completion'] = self.waiter(
                self.read_snapshot, expected_build=fixture['expected_build'], identity=identity,
                input_bytes=len(packet), output_bytes=len(expected), timeout_s=5.0)
            self.buffers[5].sync_from_device()
            observed = self.buffers[5].tobytes()
            self.evidence['observed_sha256'] = hashlib.sha256(observed).hexdigest()
            self.evidence['expected_sha256'] = hashlib.sha256(expected).hexdigest()
            if observed != expected:
                raise RuntimeError('Complete output differs from frozen reference')
            if not self.release_if_safe():
                raise RuntimeError('Device not safe to release after completion')
            self.evidence['status'] = 'PASS_MINIMAL_TRANSACTION_ONLY'
            return self.evidence
        except Exception as exc:
            self.evidence['error'] = f'{type(exc).__name__}: {exc}'
            self.evidence['failure_snapshot'] = self.read_snapshot()
            if hasattr(exc, 'evidence'):
                self.evidence['wait_failure'] = exc.evidence
            self.release_if_safe()
            self.evidence['recovery_required'] = self.recovery_required
            raise
        finally:
            self.evidence['total_seconds'] = time.monotonic() - begin
