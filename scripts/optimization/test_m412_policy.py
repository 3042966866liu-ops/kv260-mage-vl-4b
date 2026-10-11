"""Actual new policy/Owner methods, explicitly fake allocator and MMIO."""
import ast,importlib.util,json,sys,types
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha
from m412_policy import POLICY,MemoryBudget,PlannedDMA,MAIN_SIZES,MINIMAL_SIZES,verify_owner_buffers

def main():
    baseline=dict(CmaFree=34<<20,MemAvailable=2<<30,VmRSS=400<<20)
    readings=dict(baseline);budget=MemoryBudget(baseline,lambda:dict(readings));checks=[]
    for cma in (34<<20,1<<20,0):
        readings['CmaFree']=cma;assert budget.check('actual-statistic')['required_cma_free_bytes'] is None
    checks.append('CMA34MiB/1MiB/0 statistic alone does not reject after actual allocation')
    for key,value in [('VmRSS',(657<<20)),('MemAvailable',319<<20),('CmaFree',-1)]:
        readings=dict(baseline);readings[key]=value
        try:budget.check('explicit-failure')
        except (RuntimeError,MemoryError):pass
        else:raise AssertionError('Ordinary budget/invalid actual fields bypass')
    checks.append('ordinary growth/remaining available budget/invalid statistic rejection')
    readings=dict(baseline,VmRSS=700<<20,MemAvailable=65<<20)
    assert budget.check('stable-recovery',True)['required_MemAvailable_bytes']==64<<20
    readings['MemAvailable']=63<<20
    try:budget.check('stable-recovery',True)
    except MemoryError:pass
    else:raise AssertionError('Recovery minimum bypass')
    checks.append('bounded recovery does not require prior transient growth headroom')
    helper=types.ModuleType('m341_build_id_gate');helper.verify_self=helper.service_stopped=lambda *a:None;helper.STABLE=ROOT;helper.STABLE_SHA='explicit-fake';helper.ROOT=ROOT
    common=types.ModuleType('m120_board_common');common.KERNEL_NAME='kernel';common.DMA_NAME='dma'
    observer_spec=importlib.util.spec_from_file_location('m357_completion_observer',BASE/'candidates/M357-private-activation-01/m357_completion_observer.py')
    observer=importlib.util.module_from_spec(observer_spec);observer_spec.loader.exec_module(observer)
    with patch.dict(sys.modules,dict(m341_build_id_gate=helper,m120_board_common=common,fcntl=types.ModuleType('fcntl'),m357_completion_observer=observer)):
        spec=importlib.util.spec_from_file_location('m412_actual_lower_owner',HERE/'m410_probe.py');lower=importlib.util.module_from_spec(spec);spec.loader.exec_module(lower)
    tree=ast.parse((HERE/'m412_gate.py').read_bytes())
    cls=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='WorkOwner')
    signature='def factory(lower,budget,r,base,sealed_ids,proc,PlannedDMA,verify_owner_buffers):\n    allocator=None\n    pass\n    return None\n'
    scaffold=ast.parse(signature);f=scaffold.body[0];f.body[1]=cls;f.body[-1]=ast.Return(ast.Name('WorkOwner',ast.Load()));ast.fix_missing_locations(scaffold)
    scope={'np':np};exec(compile(scaffold,'ACTUAL_M412_WorkOwner','exec'),scope)
    for failure in ('success','partial-third-allocation','ordinary-budget','buffer-identity','guard-drift'):
        state=dict(count=0,free=0)
        class Buffer(np.ndarray):
            def __new__(cls,size):return np.zeros(size,np.uint8).view(cls)
            def freebuffer(self):state['free']+=1
        def allocate(shape,dtype):
            state['count']+=1
            if failure=='partial-third-allocation' and state['count']==3:raise MemoryError('EXPLICIT backend partial allocation failure')
            return Buffer(shape[0])
        fake=types.ModuleType('pynq');fake.allocate=allocate
        snapshot=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
        base=types.SimpleNamespace(LOW_END=0x80000000,physical_address=lambda b:0x10000000,transaction_snapshot=lambda *a:snapshot)
        readings=dict(baseline,CmaFree=0);result=dict(memory=[],allocations=[],releases=[])
        live_budget=MemoryBudget(baseline,lambda:dict(readings));typ=scope['factory'](lower,live_budget,result,base,None,None,PlannedDMA,verify_owner_buffers)
        owner=typ(base,result);owner.kernel=object();owner.dma=object();owner.expected=0x4d333537
        if failure=='ordinary-budget':readings['VmRSS']=baseline['VmRSS']+(257<<20)
        with patch.dict(sys.modules,{'pynq':fake}):
            try:owner.allocate(MINIMAL_SIZES,'candidate-legal-build-id')
            except MemoryError:assert failure in ('partial-third-allocation','ordinary-budget')
            else:assert failure not in ('partial-third-allocation','ordinary-budget')
            original_group_count=state['count']
            try:fake.allocate((1,),dtype=np.uint8)
            except RuntimeError:pass
            else:raise AssertionError('Public allocation outside owner group allowed')
            assert state['count']==original_group_count
            if failure=='success':
                owner.release();owner.allocate(MAIN_SIZES,'completeMLP-seven')
                ids=tuple(id(b) for b in owner.buffers);verify_owner_buffers(owner,ids)
                owner.release();owner.expected=0x4d395832;owner.allocate(MINIMAL_SIZES,'stable-restored-build-id');owner.release()
                assert state['count']==19 and state['free']==19
            else:
                if failure=='buffer-identity':
                    ids=tuple(id(b) for b in owner.buffers)
                    try:verify_owner_buffers(owner,ids)
                    except RuntimeError:pass
                    else:raise AssertionError('Six buffers treated as main seven')
                owner.release();assert state['free']==(2 if failure=='partial-third-allocation' else 6)
            guard=owner.allocate.__func__.__closure__
            # Actual nested allocation closure holds the installed guard.
            tracker=next(c.cell_contents for c in guard if isinstance(c.cell_contents,PlannedDMA))
            if failure=='guard-drift':
                fake.allocate=allocate
                try:tracker.close()
                except RuntimeError:pass
                else:raise AssertionError('Changed public allocator silently restored')
                fake.allocate=tracker.wrapper
            tracker.close();assert fake.allocate is allocate and result['DMA_allocator_restored']
        checks.append('actual WorkOwner '+failure)
    v=dict(status='PASS_M412_ACTUAL_INDEPENDENT_POLICY_COMPONENT',checks=checks,policy=POLICY,actual_new_Owner_memory_allocate_methods=True,
        explicit_fake_allocator_MMIO=True,CMA_floor_removed_only_independent_entry=True,actual_partial_allocation_safely_released=True,
        original_active_DMA_retention_unchanged=True,original_M410_source_sha256=sha(HERE/'m410_probe.py'),new_source_sha256={n:sha(HERE/n) for n in ('m412_gate.py','m412_policy.py','test_m412_policy.py')},hardware_or_capacity_proven=False)
    p=BASE/'runs/M412-policy-component-01/RESULT.json';atomic(p,encoded(v),immutable=True);print('M412_POLICY_COMPONENT_PASS',sha(p),len(checks))
if __name__=='__main__':main()
