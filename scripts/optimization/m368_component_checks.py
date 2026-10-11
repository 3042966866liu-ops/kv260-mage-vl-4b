"""Offline policy/control checks; fake memory/MMIO, saved real video outputs."""
import ast
import copy
import importlib.util
import json
import symtable
import types
import m351_workflow as w
import m368_stage_policy as p
import m368_video_contract as v


def checks():
    count=0
    m=dict(system_bytes=dict(CmaFree=0,MemAvailable=1088<<20),process_bytes=dict(VmRSS=400<<20,VmHWM=400<<20))
    counters={'area:alloc_pages_success':10,'area:alloc_pages_fail':0}
    assert not p.assess(m,400<<20,counters,counters,sealed=True,buffer_bytes=p.SHAPES)['production_64mib_would_admit'];count+=1
    for mode in ('low_available','rss_growth','counts_change','geometry','unsealed','invalid'):
        mm=copy.deepcopy(m);cc=dict(counters);bb=list(p.SHAPES);sealed=True
        if mode=='low_available':mm['system_bytes']['MemAvailable']-=1
        if mode=='rss_growth':mm['process_bytes']['VmRSS']+=(1024<<20)+1
        if mode=='counts_change':cc['area:alloc_pages_success']+=1
        if mode=='geometry':bb[-1]+=1
        if mode=='unsealed':sealed=False
        if mode=='invalid':mm['system_bytes']['CmaFree']=True
        try:p.assess(mm,400<<20,cc,counters,sealed=sealed,buffer_bytes=bb)
        except (RuntimeError,MemoryError):count+=1
        else:raise AssertionError('Invalid video memory policy accepted: '+mode)
    state=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    rt=types.SimpleNamespace(kernel=object(),dma=object());base=types.SimpleNamespace(transaction_snapshot=lambda *a:dict(state));r={}
    policy=p.StagePolicy(r,lambda:rt,base,snapshot=lambda:m,counters=lambda:counters)
    policy.seal([types.SimpleNamespace(nbytes=n) for n in p.SHAPES],0x4d333537)
    assert policy.safe();policy.ever=True;assert not policy.safe();count+=2
    state.update(ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098);policy.completed=True
    for layer,family in ((0,'q'),(9,'kv'),(10,'qkv'),(35,'mlp_down')):
        chain=dict(layer=layer,family=family,chain_index=0,input_bytes=1,output_bytes=1)
        assert policy.wrap_launch(lambda ch:ch,'fixture')(chain)==chain and policy.safe();count+=1
    for layer,family in ((36,'qkv'),(0,'qkv'),(10,'q'),(None,'q')):
        try:policy.wrap_launch(lambda ch:None,'fixture')(dict(layer=layer,family=family))
        except RuntimeError:count+=1
        else:raise AssertionError('Video family scope escaped')
    def failed(chain):raise TimeoutError('explicit fake timeout')
    try:policy.wrap_launch(failed,'fixture')(dict(layer=0,family='q',chain_index=0,input_bytes=1,output_bytes=1))
    except TimeoutError:assert policy.active and not policy.safe();count+=1
    else:raise AssertionError('DMA fault swallowed')
    policy.active=False;policy.completed=True;policy.stop_reason='explicit fake stop'
    try:policy.capture('next safe boundary',True)
    except RuntimeError:count+=1
    else:raise AssertionError('Latched stop ignored')
    baseline=json.loads((w.BASE/'runs/M345-fixed-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))['passes'][0]
    assert [(f['layer'],f['family']) for f in baseline['families']]==p.FAMILIES
    original=copy.deepcopy(baseline);v.check_call_contract(original,baseline['logical_expected_macros'])
    assert original['language_retries']==3 and original['head_retries']==0;count+=1
    for key,value in [('logical_calls',777),('host_calls',778),('retry_count',0),('retry_launches',0),('logical_expected_macros',0)]:
        row=copy.deepcopy(baseline);row[key]=value
        try:v.check_call_contract(row,baseline['logical_expected_macros'])
        except RuntimeError:count+=1
        else:raise AssertionError('Invalid retry accounting accepted:'+key)
    events=copy.deepcopy(baseline['events'])
    for event,payload in events:
        if event=='complete':payload['proof']['build_id']='0x4D333537'
    semantic=v.validate_stream(events,baseline['decoder'],'0x4D333537')
    normalized=copy.deepcopy(semantic);normalized['proof']['build_id']=baseline['semantic']['proof']['build_id']
    assert normalized==baseline['semantic'];count+=1
    for mode in ('wrong_build','calls','decode','frames','decision'):
        mutated=copy.deepcopy(events)
        for event,payload in mutated:
            if event=='complete':
                if mode=='wrong_build':payload['proof']['build_id']='0x4D395832'
                if mode=='calls':payload['proof']['pl_logical_chain_calls']=777
                if mode=='decode':payload['decode_calls']=1
                if mode=='frames':payload['selected_frame_indices']=[0]
            if event=='token' and mode=='decision':payload['text']='1'
        try:v.validate_stream(mutated,baseline['decoder'],'0x4D333537')
        except RuntimeError:count+=1
        else:raise AssertionError('Invalid video semantic accepted:'+mode)
    source=(w.HERE/'m368_staged_video_gate.py').read_text(encoding='utf-8')
    ast.parse(source,feature_version=(3,10))
    symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert source.index('policy.seal(allocations')<source.index('recvchannel.transfer')<source.index('engine.stream(request)')
    assert 'engine.stream = forbid' not in source and 'vision.tower.forward' not in source and "for name in ('decode',)" in source
    assert 'index>=7' in source and '1024<<20' in source and "logical_calls']!=778" in source
    assert 'physical' not in source or "row['host_calls']!=len(result['transactions'])" in source
    return count


if __name__=='__main__':print('M368_DRAFT_COMPONENT_CHECKS_PASS checks='+str(checks()))
