"""Default-off independent diagnostic adapter; original PS component unchanged."""
import weakref
from ps_read_ahead import PSReadAheadSession,RetainedPSResourcesError
from m382_ps_slot import assess,SlotOwner,release

class SealedPSReadSession(PSReadAheadSession):
    def __init__(self,runtime,base,plan,*,enabled=False,policy=None,resident=None,completed_transaction_snapshot=None,timeout_s=60):
        if not enabled:raise ValueError('Sealed diagnostic pre-read disabled by default')
        if policy is None or not policy.sealed or not callable(resident) or not resident():
            raise ValueError('Actual seven original DMA sealed/resident proof required')
        self.policy=policy;self.resident=resident
        self.baseline_rss=policy.snapshot()['process_bytes']['VmRSS']
        self.initial_counts=dict(policy.counters());self.memory_checks=[]
        self.slot_owners=[];self.slot_refs=[];self.release_proof=None
        super().__init__(runtime,base,plan,enabled=True,memory_reader=lambda:None,
                         completed_transaction_snapshot=completed_transaction_snapshot,timeout_s=timeout_s)

    def _memory(self,before_payload=False):
        if not self.resident():raise RetainedPSResourcesError('Sealed DMA/runtime identity changed')
        observed=self.policy.snapshot();counts=self.policy.counters()
        decision=assess(observed,self.baseline_rss,counts,self.initial_counts)
        self.memory_checks.append(dict(before_payload=before_payload,memory=observed,decision=decision,cma_counts=counts))
        return dict(observed['system_bytes'])

    def __enter__(self):
        try:
            super().__enter__()
            # Wrappers add ownership metadata, never another payload copy.
            self.slot_owners=[SlotOwner(data) for data in self.slot]
            self.slot_refs=[weakref.ref(owner) for owner in self.slot_owners]
            return self
        except BaseException:
            # A partially constructed active reader must keep its process.
            if self.future is not None and not self.future.done():
                raise RetainedPSResourcesError('Entry failed with active reader; retain process')
            raise

    def close(self):
        super().close()
        # Base waits for worker completion, closes fd/views, removes _stage and
        # runtime owner, then clears its payload list. Our sole-owner proof is
        # deliberately last; traceback/view aliases still refuse destruction.
        if self.release_proof is None and self.slot_owners:
            self.release_proof=release(self.slot_owners,self.slot_refs)
            self._memory()

    def report(self):
        if not self.closed or self.slot or self.slot_owners or self.release_proof is None:
            raise RetainedPSResourcesError('PS session lifecycle not closed')
        return dict(component=dict(self.record),independent_memory_checks=self.memory_checks,
                    slot_release=self.release_proof,production_policy_changed=False,
                    additional_dma_allocations=0,source_component_unchanged=True)
