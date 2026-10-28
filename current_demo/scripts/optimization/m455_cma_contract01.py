"""Proposed exact-bit contract; no actual configuration proof or credit."""
import hashlib,re
BITS={'e1b5b9e6cb84325820e1150528d1e4117d30e924e777246576a35acb5332e4b8'}
KERNEL='5.15.0-1027-xilinx-zynqmp'

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
