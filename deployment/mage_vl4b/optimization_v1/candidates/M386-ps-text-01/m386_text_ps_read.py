"""Default-off fixed-text diagnostic: slot and layer share existing 256 MiB budget.

Production admission and the original pre-read source are unchanged. This is
an experimental stop ceiling, not a prediction of native allocations or peak.
"""
from m383_sealed_ps_read import SealedPSReadSession
from m366_stage_policy import assess, PS_GROWTH_LIMIT, PS_AVAILABLE_MARGIN
from ps_read_ahead import RetainedPSResourcesError


class TextPSReadSession(SealedPSReadSession):
    def _memory(self, before_payload=False):
        if not self.resident():
            raise RetainedPSResourcesError('Sealed layer runtime identity changed')
        if self.policy.stop_reason:
            raise MemoryError('Latched layer observer stop: ' + self.policy.stop_reason)
        observed = self.policy.capture('PS-slot:before' if before_payload else 'PS-slot:live', True)
        counts = self.policy.counters()
        decision = assess(observed, self.policy.baseline_rss, counts,
                          self.policy.initial_counts, sealed=self.policy.sealed,
                          buffer_bytes=self.policy.buffer_bytes)
        self.memory_checks.append(dict(before_payload=before_payload, memory=observed,
                                       decision=decision, cma_counts=counts))
        return dict(observed['system_bytes'])

    def report(self):
        result = super().report()
        result.update(budget_growth_bytes=PS_GROWTH_LIMIT,
                      available_margin_bytes=PS_AVAILABLE_MARGIN,
                      budget_baseline_rss=self.policy.baseline_rss,
                      budget_scope='All RSS growth after seven original DMA allocations; includes PS slot and layer')
        return result
