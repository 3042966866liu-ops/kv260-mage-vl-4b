"""Actual validator tests on old native PASS and explicitly synthetic fault records."""
import copy,hashlib,json,re
from pathlib import Path

def tests(directory):
    directory=Path(directory)
    from m455_cma_retry_contract02 import validate as candidate
    from b0_cma_retry_contract02 import validate as stable
    actual=json.loads((directory/'CONFIG_FIXTURES.json').read_bytes())
    assert candidate(actual['candidate'])==stable(actual['stable'])=={'reserved:alloc_pages_success':1904}
    # This composed fixture exercises parsing; it is NOT new board configuration evidence.
    synthetic=copy.deepcopy(actual['candidate']);synthetic['pid']=40788
    synthetic['trace']['pid']=40788;synthetic['trace']['trace_text']=actual['busy_trace']
    synthetic['trace']['trace_sha256']=hashlib.sha256(actual['busy_trace'].encode()).hexdigest()
    assert candidate(synthetic)=={'reserved:alloc_pages_success':1904}
    rejects=0
    def reject(v):
        nonlocal rejects
        try:candidate(v)
        except (AssertionError,TypeError,IndexError,ValueError):rejects+=1
        else:raise AssertionError('Malformed or incomplete CMA record admitted')
    for edit in (
        lambda v:v['after'].__setitem__('reserved:alloc_pages_fail',v['after']['reserved:alloc_pages_fail']+1904),
        lambda v:v['after'].__setitem__('reserved:alloc_pages_success',v['after']['reserved:alloc_pages_success']+1),
        lambda v:v.__setitem__('pid',1),lambda v:v.__setitem__('pages',1903),lambda v:v.__setitem__('page_size',8192),
        lambda v:v['trace'].__setitem__('observer_errors',['lost']),lambda v:v['trace'].__setitem__('own_instance_removed',False),
        lambda v:v['trace'].__setitem__('shared_root_configuration_changed',True),lambda v:v['trace'].__setitem__('elapsed_trace_s',31),
        lambda v:v['trace'].__setitem__('trace_sha256','0'*64),
        lambda v:v['trace']['stats'].__setitem__('cpu0',v['trace']['stats']['cpu0'].replace('overrun: 0','overrun: 1')),
    ):
        v=copy.deepcopy(synthetic);edit(v);reject(v)
    text=actual['busy_trace']
    mutations=[
        text.replace('python-40788','python-1'),text.replace('name=reserved','name=other'),text.replace('count=1904','count=1903'),
        text.replace('=> zynqmp_fpga_ops_write','=> other'),text.replace('=> dma_free_attrs','=> other'),
        text.replace('cma_release:','cma_alloc_finish:'),text.replace('cma_alloc_finish:','cma_release:'),
        text.replace('cma_alloc_busy_retry:','cma_unknown_event:'),text.replace('align=8','align=7'),
        text.replace('pfn=0x4e900 page=0000000086c68632 count=1904\n','pfn=0x4ea00 page=0000000086c68632 count=1904\n'),
        text.replace('pfn=0x4e300','pfn=0x4e200'),text.replace('pfn=0x4e800','pfn=0x4fa00'),
    ]
    for changed in mutations:
        assert changed!=text;v=copy.deepcopy(synthetic);v['trace']['trace_text']=changed
        v['trace']['trace_sha256']=hashlib.sha256(changed.encode()).hexdigest();reject(v)
    assert rejects==23
    return dict(actual_old_native_records_accepted=2,explicit_synthetic_busy_parse_fixture=True,
        negative_tests=rejects,board_configuration_proof=False,device_calls=0,model_forwards=0)
