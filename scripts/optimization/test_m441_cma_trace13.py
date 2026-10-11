"""Actual admission-policy negatives and trace attribution using explicit fixtures."""
import copy
from m368_stage_policy import assess,SHAPES
import m441_cma_trace13 as t

def run():
    memory=dict(system_bytes=dict(CmaFree=32<<20,MemAvailable=2<<30),process_bytes=dict(VmRSS=128<<20))
    counts={'reserved:alloc_pages_success':100,'reserved:alloc_pages_fail':0}
    assert assess(memory,128<<20,counts,counts,sealed=True,buffer_bytes=SHAPES)
    tests=['actual-policy-keeps-cancelled-fixed-CMA-floor']
    for label,c,m,s,b in [
        ('bitstream-increment-still-rejected',dict(counts,**{'reserved:alloc_pages_success':2004}),memory,True,SHAPES),
        ('allocator-failure-rejected',dict(counts,**{'reserved:alloc_pages_fail':1}),memory,True,SHAPES),
        ('unsealed-rejected',counts,memory,False,SHAPES),
        ('geometry-rejected',counts,memory,True,SHAPES[:-1]),
        ('PS-budget-rejected',counts,dict(memory,process_bytes=dict(VmRSS=2<<30)),True,SHAPES),
        ('ordinary-margin-rejected',counts,dict(memory,system_bytes=dict(CmaFree=32<<20,MemAvailable=32<<20)),True,SHAPES)]:
        try:assess(m,128<<20,c,counts,sealed=s,buffer_bytes=b)
        except (RuntimeError,MemoryError):tests.append(label)
        else:raise AssertionError(label)
    gate=dict(gate_return_code=1,samples=[],model_forward_calls=0,host_calls=0,logical_calls=0,fpga_transactions=2,
              kernel_transitions=[dict(full_output_exact=True)],safe_buffers_released=True,original_buffer_release_count=7,
              unsafe_buffers_retained=False,stable_overlay_reloaded=True,errors=['RuntimeError: Global CMA API counter changed; ownership unknown, stop diagnostic'])
    fixture=dict(maximum_bitstream_pages=1904,before_program_counts=counts,after_program_counts=dict(counts,**{'reserved:alloc_pages_success':2004}),after_minimal_or_failure_counts=dict(counts,**{'reserved:alloc_pages_success':2004}),
                 trace=dict(pid=123,trace_text='python-123 [0] cma_alloc_start: name=reserved count=1904\n dma_alloc_coherent\n zynqmp_fpga_ops_write\npython-123 [0] cma_alloc_finish: name=reserved pfn=0x1234 count=1904\npython-123 [0] cma_release: name=reserved pfn=0x1234 count=1904\n',stats={'cpu0':'overrun: 0\ncommit overrun: 0\ndropped events: 0\n'},observer_errors=[],own_instance_removed=True))
    t.DETAILS.update(fixture)
    assert t.verdict(gate)['status']=='PASS_M441_CMA_DRIVER_ATTRIBUTION_ONLY13';tests.append('complete-driver-allocation-release-fixture')
    for label,change in [('missing-release',lambda d:d['trace'].update(trace_text=d['trace']['trace_text'].split('python-123 [0] cma_release')[0])),
                         ('lost-events',lambda d:d['trace'].update(stats={'cpu0':'overrun: 1\n'})),
                         ('unknown-task',lambda d:d['trace'].update(trace_text=d['trace']['trace_text'].replace('python-123','other-124'))),
                         ('extra-allocation',lambda d:d.update(after_minimal_or_failure_counts=counts)),
                         ('wrong-PFN',lambda d:d['trace'].update(trace_text=d['trace']['trace_text'].replace('cma_release: name=reserved pfn=0x1234','cma_release: name=reserved pfn=0x5678'))),
                         ('missing-driver-stack',lambda d:d['trace'].update(trace_text=d['trace']['trace_text'].replace('zynqmp_fpga_ops_write','unidentified')))]:
        d=copy.deepcopy(fixture);change(d);t.DETAILS.clear();t.DETAILS.update(d)
        assert t.verdict(gate)['status']=='INCONCLUSIVE_M441_CMA_TRACE13',label;tests.append(label)
    t.DETAILS.clear()
    return tests

if __name__=='__main__':print(run())
