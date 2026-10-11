"""Same video admission, sparse evidence; no hashing in timed requests."""
import threading
import time
from m368_stage_policy import StagePolicy as OriginalPolicy,assess


class StagePolicy(OriginalPolicy):
    def capture(self,label,check=False):
        memory=self.snapshot();counts=self.counters()
        with self.lock:
            if self.sealed and check:
                if self.stop_reason:raise RuntimeError('Latched monitor stop: '+self.stop_reason)
                decision=assess(memory,self.baseline_rss,counts,self.initial_counts,sealed=True,buffer_bytes=self.buffer_bytes)
            else:decision=None
            if 'physical-launch' not in label:
                self.result.setdefault('stage_memory',[]).append(dict(label=label,elapsed_s=time.monotonic()-self.started,memory=memory,cma_counts=counts,admission=decision))
        return memory

    def begin_sampling(self):
        if not self.sealed:raise RuntimeError('Policy not sealed')
        self.forward_started=time.monotonic()
        def sample():
            while not self.stop_event.wait(.1):
                try:
                    m=self.snapshot();c=self.counters()
                    assess(m,self.baseline_rss,c,self.initial_counts,sealed=True,buffer_bytes=self.buffer_bytes)
                    with self.lock:
                        self.sample_count+=1
                        values=dict(max_rss=m['process_bytes']['VmRSS'],max_hwm=m['process_bytes']['VmHWM'],min_cma=m['system_bytes']['CmaFree'],min_available=m['system_bytes']['MemAvailable'])
                        if self.extrema is None:self.extrema=values
                        else:
                            for k,v in values.items():self.extrema[k]=(max if k.startswith('max') else min)(self.extrema[k],v)
                    if time.monotonic()-self.forward_started>420:raise RuntimeError('Video soft budget exceeded420s')
                except BaseException as e:
                    with self.lock:self.stop_reason=type(e).__name__+': '+str(e)
                    return
        self.thread=threading.Thread(target=sample,name='m369-light-memory',daemon=True);self.thread.start()

    def stop_sampling(self):
        super().stop_sampling()
        self.result['sampled_memory']['sample_interval_s']=.1
