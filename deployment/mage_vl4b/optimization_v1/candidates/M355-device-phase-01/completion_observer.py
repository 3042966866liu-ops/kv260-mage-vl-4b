"""Same-snapshot completion timing. Host observation intervals, not PL counters."""
import time

BUILD_ID=0x4D395832


class ObservationFailure(RuntimeError):
    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence=evidence


def wait_observed(snapshot_reader, submitted_ns, *, timeout_s=10.0,
                  clock=time.monotonic_ns, sleeper=time.sleep, initial_busy=None):
    deadline=clock()+int(timeout_s*1e9)
    evidence=dict(submitted_ns=submitted_ns,polls=0,max_poll_gap_ns=0,events={},
                  dma_timing_unresolved=[],pure_compute_time_proven=False)
    busy=dict(initial_busy or {})
    prior_end=submitted_ns
    prior_before=submitted_ns
    kernel_finished=False
    while True:
        before=clock()
        latest=snapshot_reader()  # The sole AP_CTRL read belongs to this snapshot.
        after=clock()
        evidence['polls']+=1
        evidence['max_poll_gap_ns']=max(evidence['max_poll_gap_ns'],after-prior_end)
        evidence['last_snapshot']=latest
        for key in ('kernel_read_error','return_read_error','dma_read_error'):
            if latest.get(key)!='':
                raise ObservationFailure('MMIO read error or missing field: '+key,evidence)
        for key in ('ap_ctrl','ap_return','mm2s_dmasr','s2mm_dmasr'):
            if type(latest.get(key)) is not int or latest[key]<0:
                raise ObservationFailure('Unknown register: '+key,evidence)
        for channel in ('mm2s','s2mm'):
            flag=latest.get(channel+'_idle')
            error=latest.get(channel+'_error')
            if type(flag) is not bool or type(error) is not bool:
                raise ObservationFailure('Unknown DMA flag: '+channel,evidence)
            if error or latest[channel+'_dmasr'] & 0x770:
                raise ObservationFailure('DMA error: '+channel,evidence)
            if not flag:
                busy[channel]=dict(before_ns=before,after_ns=after)
            elif channel in busy and channel not in evidence['events']:
                evidence['events'][channel]=dict(lower_ns=busy[channel]['before_ns'],upper_ns=after,
                                                 observed_ns=after,causal_busy_seen=True)
        if latest['ap_ctrl'] & 2:
            if latest['ap_return']!=BUILD_ID:
                raise ObservationFailure('Kernel return/Build mismatch',evidence)
            if not kernel_finished:
                evidence['events']['ap_done']=dict(lower_ns=prior_before if evidence['polls']>1 else submitted_ns,
                    upper_ns=after,observed_ns=after,clear_on_read_latched=True)
            kernel_finished=True  # Later AP_DONE=0 must not lose this edge.
        if kernel_finished and latest['mm2s_idle'] and latest['s2mm_idle']:
            evidence['dma_timing_unresolved']=[c for c in ('mm2s','s2mm') if c not in evidence['events']]
            evidence['completion_proven']=True
            evidence['completed_ns']=after
            evidence['wait_ns']=after-submitted_ns
            return latest,evidence
        if after>=deadline:
            raise ObservationFailure('Active transaction timeout; retain all buffers',evidence)
        prior_end=after
        prior_before=before
        sleeper(0.0001)
