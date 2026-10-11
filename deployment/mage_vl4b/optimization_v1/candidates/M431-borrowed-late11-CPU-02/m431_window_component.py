"""Actual borrowed adapter, real geometry, explicit synthetic DMA/MMIO data."""
import copy
import hashlib
import tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from m431_borrowed_visual import BorrowedVisual, SIZES
from m429_pl_range import SavedWireCheck


class Buffer(np.ndarray):
    def __new__(cls, size):
        value = np.zeros(size, np.uint8).view(cls)
        value.to_count = value.from_count = 0
        return value
    def sync_to_device(self):
        self.to_count += 1
    def sync_from_device(self):
        self.from_count += 1
    def freebuffer(self):
        raise AssertionError('Borrower cannot free the original owner buffers')


def component(references, fixture_root):
    arrays = [Buffer(n) for n in SIZES]
    kernel = SimpleNamespace(writes=[])
    kernel.write = lambda reg, value: kernel.writes.append((reg, value))
    runtime = SimpleNamespace(staged_buffers=arrays[:4], input_buffer=arrays[4], output_buffer=arrays[5], output_buffer_alt=arrays[6],
                              kernel=kernel, _programmed_config=123, _programmed_weight_addresses=(1, 2, 3, 4))
    snapshot = dict(ap_ctrl=4, ap_return=0x4d333537, mm2s_dmasr=4098, s2mm_dmasr=4098,
                    kernel_read_error='', return_read_error='', dma_read_error='')
    pending = {}
    def receive(target, nbytes):
        pending['target'], pending['nbytes'] = target, nbytes
    def wait(*unused):
        raw = pending['raw']
        assert pending['nbytes'] == len(raw)
        pending['target'][:len(raw)] = np.frombuffer(raw, np.uint8)
        return copy.deepcopy(snapshot)
    runtime.dma = SimpleNamespace(recvchannel=SimpleNamespace(transfer=receive), sendchannel=SimpleNamespace(transfer=lambda *a, **k: None))
    policy = SimpleNamespace(sealed=True, buffer_bytes=list(SIZES), ever=True, completed=True, active=False, build=0x4d333537, checks=[])
    policy.safe = lambda: not policy.active and policy.completed
    policy.capture = lambda label, check: policy.checks.append(label)
    base = SimpleNamespace(REG_POINTERS=(16, 28, 40, 52), REG_CONFIG=64, REG_AP_CTRL=0,
                           physical_address=lambda b: id(b), write_u64=lambda k, r, v: k.write(r, v), wait_transaction=wait)
    references = copy.deepcopy(references)
    # Original saved sizes, starts and shifts are retained. Fake byte hashes are
    # declared synthetic: this is a buffer/scheduling test, not PL mathematics.
    for layer in references.values():
        for rows in layer.values():
            for row in rows:
                row['packet_sha256'] = hashlib.sha256(b'\x34' * row['input_bytes']).hexdigest()
                row['raw_sha256'] = hashlib.sha256(b'\x12' * row['output_bytes']).hexdigest()
    record = {}
    with tempfile.TemporaryDirectory(dir=fixture_root, prefix='m431-window-') as temporary:
        root = Path(temporary)
        windows = []
        for i in range(4):
            path = root / str(i)
            path.write_bytes(bytes([i + 1]) * 557056)
            windows.append(dict(relative_file=str(i), bytes=557056, file_bytes=557056, offset=0))
        with BorrowedVisual(runtime, policy, base, record, enabled=True) as owner:
            guard = SavedWireCheck(references, owner.submit)
            for index in range(13, 24):
                for part in ('fc1', 'fc2'):
                    row = references[str(index)][part][0]
                    chain = dict(input_bytes=row['input_bytes'], output_bytes=row['output_bytes'], config='0x10440')
                    owner.stage(index, part, chain, windows, root)
                    for row in references[str(index)][part]:
                        packet, raw = b'\x34' * row['input_bytes'], b'\x12' * row['output_bytes']
                        pending['raw'] = raw
                        assert guard(index, part, chain, row['start'], row['selected_shift'], packet) == raw
            guard.require_complete()
            assert len(owner.rows) == 286 and len(owner.staging) == 22
            assert [(x['layer'], x['part']) for x in owner.staging] == [(i, p) for i in range(13, 24) for p in ('fc1', 'fc2')]
            assert sum(x['bytes'] for x in owner.staging) == 49020928
            assert owner.ids == tuple(id(x) for x in arrays) and policy.completed and not policy.active
        assert not owner.entered and not owner.retained
        assert runtime._programmed_config is None and runtime._programmed_weight_addresses is None
        assert arrays[5].from_count == arrays[6].from_count == 143
    return dict(full286_original_geometry_and_saved_shifts=True, complete_batches=286, staged_windows=22,
                staged_bytes=49020928, fake_original_buffer_bytes=sum(SIZES),
                fake_DMA_MMIO_policy_and_byte_content=True, original_buffer_identities_unchanged=True,
                alternating_outputs=[arrays[5].from_count, arrays[6].from_count], static_cache_invalidated=True,
                extra_DMA_allocate_or_free_calls=0, all_fixture_files_released=True,
                actual_PL_numerics_or_complete_runtime_capacity_proven=False)
