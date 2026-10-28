"""Exact original seven-owner allocation ledger; no automatic hardware actions."""
SHAPES = (6963200, 6963200, 6963200, 6963200, 389152, 2621440, 2621440)


class Owners:
    def __init__(self, allocator, dtype, address, eligible, safe, release_hook, result, low_end=0x80000000):
        self.allocator, self.dtype, self.address = allocator, dtype, address
        self.eligible, self.safe, self.release_hook, self.result, self.low_end = eligible, safe, release_hook, result, low_end
        self.buffers = []; self.hooks = []; self.allocating_unknown = False
        self.sealed = self.closed = False
        self.result['allocations'] = []; self.result['releases'] = []

    def allocate(self, *args, **kwargs):
        index = len(self.buffers)
        if self.closed or self.sealed or self.allocating_unknown or index >= 7:
            raise RuntimeError('Allocator sealed or unresolved; no additional DMA owner')
        if len(args) != 1 or args[0] != (SHAPES[index],) or set(kwargs) != {'dtype'} or kwargs['dtype'] is not self.dtype:
            raise RuntimeError('Original seven-owner request geometry differs')
        self.eligible()  # Actual accepted configuration, frequency, free pages.
        self.allocating_unknown = True
        buffer = self.allocator(*args, **kwargs)
        self.buffers.append(buffer)  # Strong reference before any post-allocation checks.
        begin, size = int(self.address(buffer)), int(buffer.nbytes)
        row = dict(index=index, address=begin, bytes=size)
        self.result['allocations'].append(row)
        hook = self.release_hook(buffer.freebuffer, self.release_safe,
            lambda: self.result['releases'].append(dict(row)))
        self.hooks.append(hook); buffer.freebuffer = hook
        if size != SHAPES[index] or begin <= 0 or begin % 4096 or begin + size > self.low_end:
            raise RuntimeError('Original owner lies outside its required aligned low DDR extent')
        if any(begin < r['address'] + r['bytes'] and r['address'] < begin + size for r in self.result['allocations'][:-1]):
            raise RuntimeError('Aliased DMA owners')
        self.allocating_unknown = False
        if len(self.buffers) == 7: self.sealed = True
        return buffer

    def release_safe(self):
        return not self.allocating_unknown and self.safe() is True

    def verify_full(self, runtime):
        if not self.sealed or self.allocating_unknown or len(self.buffers) != 7:
            raise RuntimeError('Complete seven-owner construction unproven')
        actual = list(runtime.staged_buffers) + [runtime.input_buffer, runtime.output_buffer, runtime.output_buffer_alt]
        if any(a is not b for a, b in zip(actual, self.buffers)) or len(actual) != 7:
            raise RuntimeError('Original runtime owner binding differs')
        if runtime.maximum_weight_window_bytes != SHAPES[0]:
            raise RuntimeError('Original staged window differs')

    def release_all(self):
        if self.allocating_unknown: raise RuntimeError('Unknown allocation: retain process and owners')
        if not self.closed:
            for buffer in reversed(self.buffers): buffer.freebuffer()
            self.verify_released()
            self.closed = True

    def verify_released(self):
        if self.allocating_unknown or any(h.state != 'released' for h in self.hooks):
            raise RuntimeError('Release incomplete; retain all remaining owners')
        expected = list(reversed(self.result['allocations']))
        if self.result['releases'] != expected:
            raise RuntimeError('Original seven-owner release order or count differs')
