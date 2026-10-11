"""New isolated admission only; preserve all old gate/reference evidence."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha

def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def main():
    old=BASE/'candidates/M411-complete-visual-MLP-01'
    m=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    assert sha(old/'PACKAGE_MANIFEST.json')=='989f43879fd407660bccc793e94785451371428ade5be45a96640b0be8b9257f'
    for row in m['files']:assert sha(old/row['path'])==row['sha256']
    text=(old/'m411_gate.py').read_text(encoding='utf-8')
    text=text.replace('M411','M412').replace('m411_complete_mlp_01','m412_complete_mlp_01').replace('m411_export','m412_export')
    changes=[]
    def change(before,after):
        nonlocal text
        text=replace_once(text,before,after);changes.append((before,after))
    change('owner=runtime=mlp=layer=x=binding=cap=lock=None;restored=[];ps_ref=None',
           'owner=runtime=mlp=layer=x=binding=cap=lock=None;restored=[];ps_ref=None;allocator=None;budget=None;sealed_ids=None\n    r.update(admission_policy=None,DMA_allocator_restored=False,DMA_sealed_after_main=False,PS_checkpoints=[])')
    change("        if r['memory_after_constructor']['CmaFree']<64<<20:raise MemoryError('Actual complete PS constructor below64MiB CMA before hardware')",
           "        from m412_policy import POLICY,MemoryBudget,PlannedDMA,verify_owner_buffers\n        r['admission_policy']=POLICY\n        budget=MemoryBudget(r['memory_after_constructor'],proc)\n        r['PS_checkpoints'].append(budget.check('after-constructor'))")
    change('        class WorkOwner(lower.Owner):\n            def submit',
           '''        class WorkOwner(lower.Owner):
            def memory(self,label):
                recovery=self.expected==0x4d395832
                row=budget.check(label,recovery=recovery)
                r['memory'].append(row)
                if sealed_ids is not None and not recovery:verify_owner_buffers(self,sealed_ids)
            def allocate(self,sizes,label):
                nonlocal allocator
                if allocator is None:
                    import pynq
                    allocator=PlannedDMA(pynq,r)
                with allocator.group(sizes,label):lower.Owner.allocate(self,sizes,label)
            def submit''')
    change("        owner.allocate([557056]*4+[163856,524288,524288],'completeMLP-seven')",
           "        owner.allocate([557056]*4+[163856,524288,524288],'completeMLP-seven')\n        sealed_ids=tuple(id(b) for b in owner.buffers);verify_owner_buffers(owner,sealed_ids)\n        r['DMA_sealed_after_main']=True")
    change("            phase[0]='numerical-original';r['local_mlp_calls']+=1",
           "            r['PS_checkpoints'].append(budget.check('before-numerical-original'))\n            phase[0]='numerical-original';r['local_mlp_calls']+=1")
    change("            phase[0]='numerical-PL';r['local_mlp_calls']+=1;binding=",
           "            r['PS_checkpoints'].append(budget.check('after-numerical-original'))\n            phase[0]='numerical-PL';r['local_mlp_calls']+=1;binding=")
    change("            r['numerical_batches']=binding.batches;r['full_wire_reference_batches_exact']=26",
           "            r['PS_checkpoints'].append(budget.check('after-numerical-PL'))\n            r['numerical_batches']=binding.batches;r['full_wire_reference_batches_exact']=26")
    change("                phase[0]=('warmup-' if warmup else 'timed-')+variant;before=proc();first=",
           "                phase[0]=('warmup-' if warmup else 'timed-')+variant\n                r['PS_checkpoints'].append(budget.check('before-'+phase[0]));verify_owner_buffers(owner,sealed_ids)\n                before=proc();first=")
    change("                after=proc();arr=answer[0].numpy();want=",
           "                after=proc();r['PS_checkpoints'].append(budget.check('after-'+phase[0]));verify_owner_buffers(owner,sealed_ids)\n                arr=answer[0].numpy();want=")
    change("        r['bindings_restored']=all(restored);owner.release();binding=cap=mlp=layer=x=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None",
           "        r['bindings_restored']=all(restored);owner.release();sealed_ids=None;binding=cap=mlp=layer=x=None;runtime.close();runtime=None;gc.collect();r['PS_owner_closed']=ps_ref() is None")
    change('                if owner is not None:owner.release()',
           '                if owner is not None:owner.release()\n                sealed_ids=None')
    change("        r['unsafe_dma_buffers_retained']=unsafe;r['safe_buffers_released']=not unsafe",
           "        if allocator is not None and not unsafe:\n            try:allocator.close()\n            except BaseException as error:unsafe=True;r['errors'].append(dict(type='AllocatorRestoreUnproven',message=str(error)))\n        r['unsafe_dma_buffers_retained']=unsafe;r['safe_buffers_released']=not unsafe")
    # Strict inverse transform proves original algorithm, checks and timing unchanged.
    restored=text
    for before,after in reversed(changes):restored=replace_once(restored,after,before)
    expected=(old/'m411_gate.py').read_text(encoding='utf-8').replace('M411','M412').replace('m411_complete_mlp_01','m412_complete_mlp_01').replace('m411_export','m412_export')
    assert ast.dump(ast.parse(restored),include_attributes=False)==ast.dump(ast.parse(expected),include_attributes=False)
    atomic(HERE/'m412_gate.py',text.encode('utf-8'),immutable=True)
    atomic(HERE/'m412_export.py',(old/'m411_export.py').read_bytes().replace(b'M411',b'M412').replace(b'm411_complete_mlp_01',b'm412_complete_mlp_01'),immutable=True)
    workflow=(HERE/'m411_workflow.py').read_text(encoding='utf-8').replace('M411','M412').replace('m411','m412')
    workflow=workflow.replace('from m412_mlp_binding import decision','from m411_mlp_binding import decision\nfrom m412_policy import POLICY,MAIN_SIZES,MINIMAL_SIZES')
    oldcheck="        if len(r['memory'])!=161 or any(x['required_cma_free_bytes']!=64<<20 or x['CmaFree']<64<<20 or x['MemAvailable']<128<<20 for x in r['memory']):raise ValueError('Actual per-submit capacity rejected')"
    newcheck='''        if r.get('admission_policy')!=POLICY or r.get('DMA_allocator_restored') is not True or r.get('DMA_sealed_after_main') is not True or r.get('unexpected_DMA_requests'):raise ValueError('Independent allocation seal/policy unproven')
        groups=r['DMA_admission_groups']
        labels=['candidate-legal-build-id','completeMLP-seven','stable-restored-build-id']
        if len(groups)!=3 or [x['label'] for x in groups]!=labels:raise ValueError('Exact allocation groups differ')
        for g,sizes in zip(groups,(MINIMAL_SIZES,MAIN_SIZES,MINIMAL_SIZES)):
            if g!=dict(label=g['label'],sizes=list(sizes),attempted=len(sizes),returned=len(sizes),complete=True):raise ValueError('Incomplete planned allocation group')
        if len(r['memory'])!=161 or len(r['PS_checkpoints'])!=24:raise ValueError('Independent memory checkpoint coverage differs')
        for x in r['memory']+r['PS_checkpoints']:
            if x['admission_policy']!=POLICY['name'] or x['required_cma_free_bytes'] is not None or type(x['CmaFree']) is not int or x['CmaFree']<0:raise ValueError('Memory statistics/policy identity differs')
            growth=max(0,x['VmRSS']-r['memory_after_constructor']['VmRSS'])
            required=(64<<20)+(0 if x['recovery'] else max(0,(256<<20)-growth))
            if x['RSS_growth_bytes']!=growth or x['required_MemAvailable_bytes']!=required or x['MemAvailable']<required or (not x['recovery'] and growth>256<<20):raise ValueError('Actual ordinary memory budget rejected')'''
    workflow=replace_once(workflow,oldcheck,newcheck)
    workflow=workflow.replace('完整段计时从第一权重读/恢复到输出可供PS使用','独立准入按实际七块3.281265MiB分配后封锁新增DMA，256MiB普通增长预算＋64MiB普通余量；CmaFree仅统计，生产政策不改。完整段计时从第一权重读/恢复到输出可供PS使用')
    atomic(HERE/'m412_workflow.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m411_control.ps1').read_text(encoding='utf-8').replace('M411','M412').replace('m411','m412')
    control=control.replace("'latest_m412_complete_mlp_preparation','latest_m412_complete_mlp_support'","'latest_m411_complete_mlp_capacity_closure','latest_m365_staged_layer_closure','latest_m368_video_closure','latest_m412_complete_mlp_preparation','latest_m412_complete_mlp_support'")
    atomic(HERE/'m412_control.ps1',control.encode('utf-8'),immutable=True)
    atomic(BASE/'runs/M412-policy-source-diff-01/RESULT.json',encoded(dict(status='PASS_EXACT_INVERSE_AST_DIFF',old_package_sha256=sha(old/'PACKAGE_MANIFEST.json'),new_gate_sha256=sha(HERE/'m412_gate.py'),changes=[dict(before=a,after=b) for a,b in changes],math_timing_reference_unchanged=True,hardware_executed=False)),immutable=True)
    print('M412_GENERATED_ADMISSION_ONLY',sha(HERE/'m412_gate.py'))
if __name__=='__main__':main()
