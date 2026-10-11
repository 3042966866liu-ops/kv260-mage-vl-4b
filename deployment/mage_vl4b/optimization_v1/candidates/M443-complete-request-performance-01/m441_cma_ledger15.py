"""Exact, released FPGA-configuration credits; original admission remains strict."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import traceback
from m433_light_policy import StagePolicy as ParentPolicy
from m441_cma_trace15 import Trace

BITS={'8bac3588a5d8f008a651fe25d35e0a11a32ef6615c5675add25b60e2a2e9711f',
      '73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'}
KERNEL='5.15.0-1027-xilinx-zynqmp'

def prerequisite(here):
    proof=json.loads((Path(here)/'CMA_PREREQUISITE.json').read_bytes())
    raw=Path(proof['remote_diagnostic']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==proof['sha256']
    d=json.loads(raw);g=d['gate'];x=d['diagnostic']
    assert d['status']=='PASS_M441_CMA_DRIVER_ATTRIBUTION_ONLY13' and d['original_gate_rc']==1
    assert g['original_buffer_release_count']==7 and g['safe_buffers_released'] and not g['unsafe_buffers_retained'] and g['stable_overlay_reloaded']
    assert not g.get('samples') and not g['model_forward_calls'] and g['fpga_transactions']==2
    validate(dict(kernel=KERNEL,page_size=x['page_size'],pid=x['trace']['pid'],bit_sha256=x['bit_sha256'],bit_bytes=x['bit_bytes'],pages=x['maximum_bitstream_pages'],before=x['before_program_counts'],after=x['after_program_counts'],trace=x['trace']))
    assert platform.release()==KERNEL
    for row in json.loads((Path(here)/'SOURCE_IDENTITIES.json').read_bytes()):
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
    return proof

def validate(record):
    """Reject unknown allocations, task/PFN mismatch, lost events or incomplete free."""
    assert record['kernel']==KERNEL and record['page_size']==4096
    assert record['bit_sha256'] in BITS and record['bit_bytes']==7797914 and record['pages']==1904
    before,after=record['before'],record['after']
    assert set(before)==set(after)
    delta={k:after[k]-before[k] for k in before}
    assert delta=={'reserved:alloc_pages_success':1904,'reserved:alloc_pages_fail':0}
    t=record['trace'];text=t['trace_text']
    assert hashlib.sha256(text.encode()).hexdigest()==t['trace_sha256']
    assert not t['observer_errors'] and t['own_instance_removed'] and t['owned_instance_only'] and not t['shared_root_configuration_changed']
    assert t['pid']==record['pid'] and t['elapsed_trace_s']<=30
    assert t['stats'] and set(t['stats'])=={'cpu0','cpu1','cpu2','cpu3'}
    for stats in t['stats'].values():
        for field in ('overrun','commit overrun','dropped events'):
            m=re.search(r'^'+re.escape(field)+r':\s*(\d+)',stats,re.M)
            assert m and int(m[1])==0,'Trace events lost or accounting unavailable'
    events=[]
    for m in re.finditer(r'(?m)^.*?\b(cma_alloc_start|cma_alloc_finish|cma_alloc_busy_retry|cma_release):\s*([^\n]*)\n',text):
        line=m[0];fields=m[2];tail=text[m.end():]
        next_event=re.search(r'(?m)^.*?(?:cma_\w+:|tracing_mark_write:)',tail)
        stack=tail[:next_event.start()] if next_event else tail
        assert re.search(r'-'+str(record['pid'])+r'\s',line)
        assert re.search(r'\bname=reserved\b',fields) and re.search(r'\bcount=1904\b',fields)
        assert '=> zynqmp_fpga_ops_write' in stack
        assert ('=> dma_alloc_attrs' in stack if m[1]!='cma_release' else '=> dma_free_attrs' in stack)
        events.append((m[1],fields))
    assert [e[0] for e in events]==['cma_alloc_start','cma_alloc_finish','cma_release']
    pfns=[re.search(r'\bpfn=(0x[0-9a-f]+)\b',e[1])[1] for e in events[1:]]
    assert pfns[0]==pfns[1] and int(pfns[0],16)>0
    return {'reserved:alloc_pages_success':1904}

class StagePolicy(ParentPolicy):
    def __init__(self,result,runtime,base,*,evidence,**kwargs):
        super().__init__(result,runtime,base,**kwargs)
        self.evidence=Path(evidence);self.credits={};self.pending=None
        self.raw_counters=self.counters;self.counters=self.accounted_counts
        self.result['configuration_CMA_ledger']=[]
        self.result['configuration_CMA_contract']='15: raw cumulative counters minus only directly traced released configuration pages; original baseline immutable'

    def accounted_counts(self):
        raw=self.raw_counters()
        assert set(self.credits).issubset(raw),'Counter identities changed'
        return {k:v-self.credits.get(k,0) for k,v in raw.items()}

    def prepare_programming(self,path,index,variant):
        assert self.pending is None and self.sealed and not self.active and self.completed
        assert not self.thread or not self.thread.is_alive(),'Request observer still active'
        self.capture('before-programming-ledger:'+str(index),True)
        p=Path(path);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        assert sha in BITS and len(raw)==7797914 and platform.release()==KERNEL
        trace_dir=self.evidence/('cma_program_'+str(index));trace_dir.mkdir(exist_ok=False)
        t=Trace(trace_dir)
        try:t.prepare()
        except BaseException:
            if t.created:
                import time
                t.started=time.monotonic();t.stop()
            raise
        self.pending=dict(trace=t,path=str(p),index=index,variant=variant,bit_sha256=sha,bit_bytes=len(raw))

    def commit(self,record):
        credits=validate(record)
        assert {k:v-self.credits.get(k,0) for k,v in record['before'].items()}==self.initial_counts,'Unknown allocation before configuration'
        proposed={k:self.credits.get(k,0)+credits.get(k,0) for k in record['after']}
        assert {k:v-proposed[k] for k,v in record['after'].items()}==self.initial_counts,'Unknown allocation after configuration'
        for k,v in credits.items():self.credits[k]=self.credits.get(k,0)+v
        assert self.accounted_counts()==self.initial_counts,'Unknown allocation after configuration'
        record['verified_released_configuration_pages']=credits
        record['cumulative_verified_credits']=dict(self.credits)
        record['original_baseline_unchanged']=dict(self.initial_counts)
        self.result['configuration_CMA_ledger'].append(record)

    def wrap_overlay(self,original):
        def load(path,*args,**kwargs):
            if not self.sealed:return original(path,*args,**kwargs)
            q=self.pending
            assert q is not None and str(path)==q['path'],'Unprepared programming refused'
            t=q['trace'];record={k:v for k,v in q.items() if k not in ('trace','path')}
            record.update(kernel=platform.release(),page_size=os.sysconf('SC_PAGE_SIZE'),pages=1904,pid=os.getpid(),before=self.raw_counters())
            import time
            t.started=time.monotonic()
            try:
                t.start()
                overlay=original(path,*args,**kwargs)
                record['trace']=t.stop();record['after']=self.raw_counters()
                self.commit(record)
                return overlay
            except BaseException:
                if not t.details.get('own_instance_removed'):record['trace']=t.stop()
                record['after']=self.raw_counters();record['error']=traceback.format_exc()
                self.result.setdefault('configuration_CMA_rejected',[]).append(record)
                raise
            finally:self.pending=None
        return load
