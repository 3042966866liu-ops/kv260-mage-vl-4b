"""Independent, bounded MLP admission; statistics are not a CMA allocation oracle."""
import threading
from contextlib import contextmanager

MAIN_SIZES = (557056, 557056, 557056, 557056, 163856, 524288, 524288)
MINIMAL_SIZES = (144, 144, 144, 144, 2576, 4096)
POLICY = dict(name='M413-planned-DMA-then-sealed-PS-budget',
    main_payload_bytes=sum(MAIN_SIZES), ordinary_growth_limit_bytes=768 << 20,
    ordinary_available_reserve_bytes=64 << 20, fixed_CmaFree_floor=None,
    production_policy_changed=False, native_or_driver_zero_allocation_proven=False)

class MemoryBudget:
    def __init__(self, baseline, read):
        self.baseline = dict(baseline)
        self.read = read

    def check(self, label, recovery=False):
        row = dict(self.read(), label=label, admission_policy=POLICY['name'],
                   required_cma_free_bytes=None, recovery=bool(recovery))
        for key in ('CmaFree', 'MemAvailable', 'VmRSS'):
            if type(row.get(key)) is not int or row[key] < 0:
                raise RuntimeError('Actual memory fields invalid')
        growth = max(0, row['VmRSS'] - self.baseline['VmRSS'])
        row['RSS_growth_bytes'] = growth
        remaining = max(0, POLICY['ordinary_growth_limit_bytes'] - growth)
        required = POLICY['ordinary_available_reserve_bytes'] + (0 if recovery else remaining)
        row['required_MemAvailable_bytes'] = required
        if not recovery and growth > POLICY['ordinary_growth_limit_bytes']:
            raise MemoryError('Independent MLP ordinary RSS growth limit exceeded')
        if row['MemAvailable'] < required:
            raise MemoryError('Independent MLP remaining ordinary budget/reserve unavailable')
        return row

class PlannedDMA:
    """Only three exact owner allocation groups; all other public calls reject."""
    def __init__(self, module, result):
        self.module, self.result = module, result
        self.original = module.allocate
        self.thread = threading.get_ident()
        self.pending = None
        self.seen = set()
        self.closed = False
        result['DMA_admission_groups'] = []
        result['unexpected_DMA_requests'] = []
        self.wrapper = self._allocate
        module.allocate = self.wrapper

    def _allocate(self, *args, **kwargs):
        if self.closed or threading.get_ident() != self.thread or self.pending is None:
            self.result['unexpected_DMA_requests'].append('outside authorized owner group')
            raise RuntimeError('New public DMA allocation sealed')
        group = self.pending
        index = group['attempted']
        shape = args[0] if args else kwargs.get('shape')
        dtype = kwargs.get('dtype')
        if index >= len(group['sizes']) or len(args) != 1 or set(kwargs) != {'dtype'} or shape != (group['sizes'][index],) or getattr(dtype, '__name__', None) != 'uint8':
            self.result['unexpected_DMA_requests'].append('allocation signature/size differs')
            raise RuntimeError('Exact planned DMA signature differs')
        group['attempted'] += 1
        answer = self.original(*args, **kwargs)
        group['returned'] += 1
        return answer

    @contextmanager
    def group(self, sizes, label):
        permitted = {'candidate-legal-build-id': MINIMAL_SIZES,
                     'completeMLP-seven': MAIN_SIZES,
                     'stable-restored-build-id': MINIMAL_SIZES}
        if self.pending is not None or self.closed or self.module.allocate is not self.wrapper:
            raise RuntimeError('Allocation guard reentrancy/drift')
        if label not in permitted or tuple(sizes) != permitted[label] or label in self.seen:
            raise RuntimeError('Unplanned or repeated owner DMA group')
        if label == 'completeMLP-seven' and 'candidate-legal-build-id' not in self.seen:
            raise RuntimeError('Legal same Overlay transaction must precede seven DMA')
        self.seen.add(label)
        row = dict(label=label, sizes=list(sizes), attempted=0, returned=0, complete=False)
        self.result['DMA_admission_groups'].append(row)
        self.pending = row
        try:
            yield
            if row['returned'] != len(sizes):
                raise RuntimeError('Planned owner allocation incomplete')
            row['complete'] = True
        finally:
            self.pending = None

    def close(self):
        if self.closed:
            return
        if self.pending is not None or self.module.allocate is not self.wrapper:
            raise RuntimeError('Unresolved allocation guard scope/drift')
        self.module.allocate = self.original
        self.closed = True
        self.result['DMA_allocator_restored'] = True

def verify_owner_buffers(owner, identities):
    if tuple(id(b) for b in owner.buffers) != identities or tuple(int(b.nbytes) for b in owner.buffers) != MAIN_SIZES:
        raise RuntimeError('Sealed seven DMA identity/size changed')
