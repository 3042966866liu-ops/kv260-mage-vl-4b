"""Independent one-layer diagnostic admission; never production policy."""
import threading
import time
from pathlib import Path
from board_safety import safe_to_release
from memory_lifecycle import memory_snapshot

MIB=1<<20
SHAPES=[6963200]*4+[389152,2621440,2621440]
FAMILIES=[(layer,family) for layer in range(36) for family in (('q','kv','attention_out','gate_up','mlp_down') if layer<10 else ('qkv','attention_out','gate_up','mlp_down'))]
PS_GROWTH_LIMIT=1024*MIB
PS_AVAILABLE_MARGIN=64*MIB

def read_cma_counts():
    result={}
    root=Path('/sys/kernel/mm/cma')
    if not root.is_dir():raise RuntimeError('CMA allocation counters unavailable')
    for area in sorted(root.iterdir()):
        if not area.is_dir():continue
        for field in ('alloc_pages_success','alloc_pages_fail'):
            value=int((area/field).read_text(encoding='utf-8').strip())
            if value<0:raise RuntimeError('Invalid CMA counter')
            result[area.name+':'+field]=value
    if not result:raise RuntimeError('No CMA allocation counter')
    return result

def assess(memory,baseline_rss,counts,initial_counts,*,sealed,buffer_bytes):
    s=memory['system_bytes'];p=memory['process_bytes']
    for v in (s['CmaFree'],s['MemAvailable'],p['VmRSS'],baseline_rss):
        if type(v) is not int or v<0:raise RuntimeError('Invalid memory snapshot')
    if not sealed or buffer_bytes!=SHAPES:raise RuntimeError('Seven exact buffers and allocator seal required')
    if counts!=initial_counts:raise RuntimeError('Global CMA API counter changed; ownership unknown, stop diagnostic')
    growth=max(0,p['VmRSS']-baseline_rss)
    required=max(0,PS_GROWTH_LIMIT-growth)+PS_AVAILABLE_MARGIN
    if growth>PS_GROWTH_LIMIT:raise MemoryError('Diagnostic observed RSS growth exceeded1024MiB')
    if s['MemAvailable']<required:raise MemoryError('Ordinary available memory below remaining monitored budget plus64MiB')
    return dict(cma_free_bytes=s['CmaFree'],production_64mib_would_admit=s['CmaFree']>=64*MIB,diagnostic_additional_explicit_cma_bytes=0,observed_rss_growth_bytes=growth,required_mem_available_bytes=required,mem_available_bytes=s['MemAvailable'])

class StagePolicy:
    def __init__(self,result,runtime,base,snapshot=memory_snapshot,counters=read_cma_counts):
        self.result=result;self.runtime=runtime;self.base=base;self.snapshot=snapshot;self.counters=counters
        self.sealed=False;self.buffer_bytes=[];self.baseline_rss=None;self.initial_counts=None
        self.active=False;self.ever=False;self.completed=False;self.build=None
        self.stop_event=threading.Event();self.thread=None;self.stop_reason=None;self.lock=threading.RLock()
        self.sample_count=0;self.extrema=None;self.started=time.monotonic();self.forward_started=None

    def capture(self,label,check=False):
        memory=self.snapshot();counts=self.counters()
        with self.lock:
            if self.sealed and check:
                if self.stop_reason:raise RuntimeError('Latched monitor stop: '+self.stop_reason)
                decision=assess(memory,self.baseline_rss,counts,self.initial_counts,sealed=self.sealed,buffer_bytes=self.buffer_bytes)
            else:decision=None
            self.result.setdefault('stage_memory',[]).append(dict(label=label,elapsed_s=time.monotonic()-self.started,memory=memory,cma_counts=counts,admission=decision))
        return memory

    def seal(self,buffers,build):
        self.buffer_bytes=[int(b.nbytes) for b in buffers]
        if self.buffer_bytes!=SHAPES:raise RuntimeError('Buffer geometry changed')
        self.build=build;self.initial_counts=self.counters();self.baseline_rss=self.snapshot()['process_bytes']['VmRSS'];self.sealed=True
        self.capture('diagnostic-admission-after-seven-real-buffers',True)

    def begin_sampling(self):
        if not self.sealed:raise RuntimeError('Policy not sealed')
        self.forward_started=time.monotonic()
        def sample():
            while not self.stop_event.wait(.02):
                try:
                    m=self.snapshot();c=self.counters()
                    decision=assess(m,self.baseline_rss,c,self.initial_counts,sealed=self.sealed,buffer_bytes=self.buffer_bytes)
                    with self.lock:
                        self.sample_count+=1
                        point=dict(rss=m['process_bytes']['VmRSS'],hwm=m['process_bytes']['VmHWM'],cma=m['system_bytes']['CmaFree'],available=m['system_bytes']['MemAvailable'])
                        if self.extrema is None:self.extrema=dict(max_rss=point['rss'],max_hwm=point['hwm'],min_cma=point['cma'],min_available=point['available'])
                        else:
                            for k,v in [('max_rss',point['rss']),('max_hwm',point['hwm'])]:self.extrema[k]=max(self.extrema[k],v)
                            for k,v in [('min_cma',point['cma']),('min_available',point['available'])]:self.extrema[k]=min(self.extrema[k],v)
                    if time.monotonic()-self.forward_started>420:raise RuntimeError('Video soft budget exceeded420s')
                except BaseException as e:
                    with self.lock:self.stop_reason=type(e).__name__+': '+str(e)
                    return
        self.thread=threading.Thread(target=sample,name='m368-memory-observer',daemon=True);self.thread.start()

    def stop_sampling(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(2)
            if self.thread.is_alive():raise RuntimeError('Memory observer alive; retain resources')
        self.result['sampled_memory']=dict(sample_interval_s=.02,sample_count=self.sample_count,extrema=self.extrema,stop_reason=self.stop_reason,exact_instantaneous_peak_proven=False,VmHWM_scope='whole process high watermark including load; not reset or layer-specific',observer_stopped=True)

    def safe(self):
        if self.active:return False
        rt=self.runtime()
        if rt is None or not hasattr(rt,'kernel') or not hasattr(rt,'dma'):return False
        s=self.base.transaction_snapshot(rt.kernel,rt.dma)
        if any(s.get(k)!='' for k in ('kernel_read_error','return_read_error','dma_read_error')):return False
        if self.ever:return self.completed and safe_to_release(s) and s['ap_return']==self.build
        return s['ap_ctrl']==4 and s['ap_return']==0 and s['mm2s_dmasr']==s['s2mm_dmasr']==0 and not s['mm2s_error'] and not s['s2mm_error']

    def wrap_launch(self,original,name):
        def observed(chain,*a,**kw):
            if (chain.get('layer'),chain.get('family')) not in FAMILIES and not (chain.get('layer') is None and chain.get('family')=='lm_head'):raise RuntimeError('Fixed-text scope escaped')
            self.capture('before-physical-launch:'+name+':'+chain['family'],True)
            rt=self.runtime()
            if self.ever and not self.safe():raise RuntimeError('Previous transaction completion unproven')
            self.result.setdefault('transactions',[]).append(dict(method=name,chain_index=chain['chain_index'],layer=chain['layer'],family=chain['family'],input_bytes=chain['input_bytes'],output_bytes=chain['output_bytes']))
            self.active=self.ever=True;self.completed=False
            answer=original(chain,*a,**kw)
            s=self.base.transaction_snapshot(rt.kernel,rt.dma)
            if not safe_to_release(s) or s['ap_return']!=self.build:raise RuntimeError('Completed transaction safety/build differs')
            self.active=False;self.completed=True
            # A post-launch stop is raised only after hardware completed safely.
            self.capture('after-physical-launch:'+name+':'+chain['family'],True)
            return answer
        return observed
