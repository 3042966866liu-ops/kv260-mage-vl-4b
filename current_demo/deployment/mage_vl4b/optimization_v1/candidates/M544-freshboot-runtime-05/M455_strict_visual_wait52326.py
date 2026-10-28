"""Strengthen visual wait at a new explicit facade; original sources unchanged.

Keep the observed AP_DONE edge while waiting for the original raw-register
release predicate in the returned snapshot. Never infer safety from a later
sample after a failed run; this applies only to a future admitted submission.
"""
import copy,time
from M455_adaptive_guard52301 import completed
BUILD=0x4D343535
class StrictVisualBase:
    def __init__(self,base,wait_observed,result,*,clock=time.monotonic_ns,sleeper=time.sleep):
        self.original=base;self.observe=wait_observed;self.result=result;self.clock=clock;self.sleep=sleeper
    def __getattr__(self,name):return getattr(self.original,name)
    def wait_transaction(self,kernel,dma,timeout_s):
        started=self.clock();deadline=started+int(timeout_s*1e9)
        identity=copy.deepcopy(self.result.get('visual_transactions',[{}])[-1])
        record=dict(identity=identity,started_ns=started,strict_completed=False,extra_polls=0)
        self.result.setdefault('strict_visual_completion_observations',[]).append(record)
        def snapshot():
            s=self.original.transaction_snapshot(kernel,dma);record['last_snapshot']=copy.deepcopy(s);return s
        try:
            current,detail=self.observe(snapshot,started,timeout_s=timeout_s,expected_build_id=BUILD,clock=self.clock,sleeper=self.sleep)
            record['first_returned_snapshot']=copy.deepcopy(current);record['observed_ap_done_detail']=detail
            while not completed(current):
                if current.get('ap_return')!=BUILD or any(current.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):
                    raise RuntimeError('Strict visual wait unknown register/Build; retain all owners')
                if any(type(current.get(k)) is not int or current[k]<0 or current[k]&0x770 for k in ('mm2s_dmasr','s2mm_dmasr')):
                    raise RuntimeError('Strict visual wait raw DMA error; retain all owners')
                if self.clock()>=deadline:raise TimeoutError('Strict visual raw completion timeout; retain all owners')
                self.sleep(.0001);current=snapshot();record['extra_polls']+=1
            record.update(strict_completed=True,completed_ns=self.clock())
            return current
        except BaseException as error:
            record['failure_type']=type(error).__name__
            if hasattr(error,'evidence'):record['original_observer_failure']=copy.deepcopy(error.evidence)
            raise
