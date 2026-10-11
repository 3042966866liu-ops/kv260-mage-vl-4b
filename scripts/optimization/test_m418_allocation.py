"""Actual Owner allocation/partial failure/idempotent release with fake PYNQ only."""
import ast,json,types
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from owned_buffer_release import OwnedBufferRelease
from board_safety import safe_to_release

def main():
    source=HERE/'m418_probe.py';tree=ast.parse(source.read_text(encoding='utf-8'))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Owner')
    namespace=dict(np=np,OwnedBufferRelease=OwnedBufferRelease,safe_to_release=safe_to_release)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(source),'exec'),namespace)
    answers=[]
    for fail_at in (None,3):
        state=dict(allocations=0,frees=0,reads=0)
        def snapshot(*args):
            state['reads']+=1
            return dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
        class Buffer(np.ndarray):
            def __new__(cls,size):return np.zeros(size,np.uint8).view(cls)
            def freebuffer(self):state['frees']+=1
        def allocate(shape,dtype):
            state['allocations']+=1
            if state['allocations']==fail_at:raise MemoryError('EXPLICIT fake allocator ENOMEM')
            return Buffer(shape[0])
        fake=types.ModuleType('pynq');fake.allocate=allocate
        base=types.SimpleNamespace(transaction_snapshot=snapshot,LOW_END=0x80000000,physical_address=lambda b:0x10000000)
        result=dict(memory=[],allocations=[],releases=[])
        owner=namespace['Owner'](base,result);owner.kernel=object();owner.dma=object()
        namespace['meminfo']=lambda:dict(CmaFree=0,MemAvailable=1<<30,Cached=0)
        with patch.dict('sys.modules',dict(pynq=fake)):
            failed=False
            try:owner.allocate([16]*6,'fixture')
            except MemoryError:failed=True
        assert failed==(fail_at is not None)
        expected=2 if failed else 6
        assert len(owner.buffers)==expected and len(result['allocations'])==expected
        held=list(owner.buffers);owner.release()
        assert len(result['releases'])==state['frees']==expected and not owner.buffers
        reads=state['reads']
        for b in held:b.freebuffer();b.freebuffer()
        assert state['frees']==expected and state['reads']==reads
        assert not owner.ever and not owner.active
        answers.append(dict(fake_allocator_failure=failed,allocated_buffers=expected,exact_release_once=True,idempotent_no_MMIO=True,
                            zero_CMA_floor_accepted=not failed,no_PL_submission=True))
    value=dict(status='PASS_M418_ACTUAL_OWNER_ALLOCATION_COMPONENT',source_sha256=sha(source),checks=answers,
               actual_Owner_class=True,explicit_fake_PYNQ_buffers_MMIO_memory=True,board_run=False,performance_pass=False)
    out=BASE/'runs/M418-allocation-component-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m418_allocation_component',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),
         f'## M418 实际Owner分配停止组件（2026-10-06）\n\nSHA {sha(out)}；实际Owner类、明确fake PYNQ/缓冲/MMIO/内存：6块分配成功与第三块ENOMEM保留前两块，未提交PL，原owner逆序各释放一次，重复free无MMIO或后端调用；零CMA统计不再被固定64MiB floor挡住。仅组件，不证明板端容量或数值。后续只使用M417同输入参考，在实际分配与DMA生命周期约束下单descriptor/chain，生产政策不改。')
    print('M418_ALLOCATION_COMPONENT_PASS',sha(out))

if __name__=='__main__':main()
