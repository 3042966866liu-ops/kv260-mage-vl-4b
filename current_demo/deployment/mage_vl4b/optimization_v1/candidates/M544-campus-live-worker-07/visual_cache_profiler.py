"""M533: observe the unchanged PS decoder with two independent warm LRU budgets.

Only ordinary FP32 weight caches change. Both caches remain resident during
ABBA, avoiding an arm-dependent working set. No device or model imports here.
"""
import time
from PS_crop_native import DecodeBudget


class ObservedDecodeBudget(DecodeBudget):
    def __init__(self, limit):
        assert type(limit) is int and limit in (32 << 20, 80 << 20)
        super().__init__()
        self.limit = limit  # Versioned M533 capacity; original decoder is unchanged.
        self.events = []

    def obtain(self, key, codes, scales):
        hit = key in self.cache
        prior = tuple(self.cache)
        started = time.perf_counter_ns()
        dense = super().obtain(key, codes, scales)
        elapsed = (time.perf_counter_ns() - started) / 1e9
        self.events.append(dict(key=key, hit=hit, elapsed_s=elapsed,
                                evicted=[k for k in prior if k not in self.cache],
                                resident_bytes=self.bytes))
        return dense


class CacheAB:
    def __init__(self, selector):
        assert selector.active and not selector.closed and not selector.budget.cache
        self.selector = selector
        self.budgets = {"A": ObservedDecodeBudget(32 << 20),
                        "B": ObservedDecodeBudget(80 << 20)}
        self.stores = [module.store for row in selector.rows for module in row['cropped']]
        assert len(self.stores) == 6 and len({store.key for store in self.stores}) == 6
        assert all(store.budget is selector.budget and store.codes.size * 4 == 12 << 20
                   for store in self.stores)
        self.active = None

    def begin(self, arm):
        assert arm in self.budgets
        self.selector.idle()
        budget = self.budgets[arm]
        budget.events.clear()
        self.selector.budget = budget
        for store in self.stores:
            store.budget = budget
        self.active = arm

    def end(self):
        budget = self.budgets[self.active]
        events = list(budget.events)
        assert len(events) == 6 and [e['key'] for e in events] == [s.key for s in self.stores]
        return dict(arm=self.active, limit_bytes=budget.limit,
                    hits=sum(e['hit'] for e in events), misses=sum(not e['hit'] for e in events),
                    obtain_s=sum(e['elapsed_s'] for e in events),
                    miss_decode_allocation_eviction_s=sum(e['elapsed_s'] for e in events if not e['hit']),
                    resident_bytes=budget.bytes, high_water_bytes=budget.high_water,
                    both_arms_resident_bytes=sum(b.bytes for b in self.budgets.values()),
                    deployment_B_only_extra_vs_A_bytes=48 << 20,
                    benchmark_extra_vs_A_after_warm_bytes=72 << 20,
                    events=events, original_decode_algorithm_unchanged=True,
                    timing_inside_prepare=True)
