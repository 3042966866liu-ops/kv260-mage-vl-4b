"""Reuse actual failure/export routes, update synthetic admission evidence only."""
from m351_workflow import HERE,atomic
from m412_generate import replace_once
def main():
    s=(HERE/'m411_support.py').read_text(encoding='utf-8').replace('M411','M412').replace('m411','m412')
    s=replace_once(s,'import m412_workflow as w','import m412_workflow as w\nfrom m412_policy import POLICY,MemoryBudget,MAIN_SIZES,MINIMAL_SIZES')
    s=replace_once(s,"        good=dict(failure,status=",'''        baseline=dict(VmRSS=10<<20,CmaFree=32<<20,MemAvailable=2<<30)
        budget=MemoryBudget(baseline,lambda:dict(baseline))
        labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*156+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
        memory=[budget.check(label,recovery=i>=159) for i,label in enumerate(labels)]
        ps_labels=['after-constructor','before-numerical-original','after-numerical-original','after-numerical-PL']
        for phase in ['warmup-A','warmup-B']+['timed-'+v for v in 'ABBABAAB']:ps_labels.extend(['before-'+phase,'after-'+phase])
        checkpoints=[budget.check(label) for label in ps_labels]
        groups=[dict(label=label,sizes=list(sizes),attempted=len(sizes),returned=len(sizes),complete=True) for label,sizes in zip(['candidate-legal-build-id','completeMLP-seven','stable-restored-build-id'],[MINIMAL_SIZES,MAIN_SIZES,MINIMAL_SIZES])]
        good=dict(failure,status=''')
    s=replace_once(s,"allocations=allocations,releases=releases,memory=[dict(CmaFree=256<<20,MemAvailable=2<<30,required_cma_free_bytes=64<<20) for _ in range(161)],final_snapshot=snapshot,elapsed_s_diagnostic_not_performance=1.)",
        "allocations=allocations,releases=releases,memory=memory,PS_checkpoints=checkpoints,admission_policy=POLICY,memory_after_constructor=baseline,DMA_allocator_restored=True,DMA_sealed_after_main=True,unexpected_DMA_requests=[],DMA_admission_groups=groups,final_snapshot=snapshot,elapsed_s_diagnostic_not_performance=1.)")
    s=s.replace("if k==4:x['memory'][0]['CmaFree']=32<<20","if k==4:x['memory'][0]['VmRSS']=baseline['VmRSS']+(257<<20)")
    s=replace_once(s,"        mutations += [complete+complete",'''        for key,value in [('DMA_allocator_restored',False),('DMA_sealed_after_main',False),('unexpected_DMA_requests',['EXPLICIT forbidden allocation']),('PS_checkpoints',checkpoints[:-1]),('DMA_admission_groups',groups[:-1])]:
            x=copy.deepcopy(good);x[key]=value;mutations.append(export(x))
        mutations += [complete+complete''')
    atomic(HERE/'m412_support.py',s.encode('utf-8'),immutable=True)
    print('M412_ACTUAL_SUPPORT_SOURCE_READY')
if __name__=='__main__':main()
