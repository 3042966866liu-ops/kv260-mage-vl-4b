"""Resident original M276 streams; endpoint SHA validation follows all timers."""
import copy,hashlib,json,resource,threading,time
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from m432_trials import delta
from m428_saved_features import tensor
from m368_video_contract import check_call_contract
from board_safety import safe_to_release
from m425_environment import read_environment
from m437_sequence import ORDER,NaturalSequence


def validate_candidate_cache_contract(cache):
    entries=cache.get('cache_entries'); size=cache.get('cache_bytes'); misses=cache.get('cache_misses')
    if type(entries) is not int or not 0 <= entries <= 26:
        raise RuntimeError('Candidate decoded-cache entry bound differs')
    if type(size) is not int or not 0 <= size <= 66699264:
        raise RuntimeError('Candidate decoded-cache byte bound differs')
    if cache.get('cache_within_budget') is not True:
        raise RuntimeError('Candidate decoded-cache budget flag differs')
    if type(misses) is not int or misses < 0:
        raise RuntimeError('Candidate decoded-cache miss counter differs')
    return dict(entries=entries,bytes=size,misses=misses,within_budget=True)

def validate_request_stream(events, decoder, expected_build):
    stages=[p['name'] for n,p in events if n=='stage']
    groups={n:[p for k,p in events if k==n] for n in ('complete','token','knife_observation')}
    if stages != ['preprocess','vision','prefill'] or any(len(v)!=1 for v in groups.values()):
        raise RuntimeError('Original stream stages/events incomplete')
    final,token,observation=(groups[n][0] for n in ('complete','token','knife_observation'))
    proof=final.get('proof',{})
    if not (final.get('status')=='PASS' and final.get('prompt_tokens')==159 and final.get('generated_tokens')==1
            and final.get('decode_calls')==0 and final.get('selected_frame_indices')==[3]
            and token.get('token_id')==15 and token.get('text')=='0' and token.get('knife_verdict')=='ABSENT'
            and observation.get('verdict')=='ABSENT' and observation.get('selected_frame_indices')==[3]
            and str(proof.get('build_id','')).lower()==expected_build.lower()
            and proof.get('pl_logical_chain_calls')==proof.get('expected_pl_logical_chain_calls')==778
            and proof.get('language_cpu_linear_fallback') is False and proof.get('decode_calls')==0
            and proof.get('pl_expected_macros',0)>0):
        raise RuntimeError('Frozen M277 functional contract failed')
    cache_state=validate_candidate_cache_contract(decoder)
    if not token['knife_score']==observation['knife_score']==final['knife_score']:
        raise RuntimeError('Inconsistent constrained decision score')
    return dict(token=token,observation=observation,proof=proof,prompt_tokens=159,
                selected_frame_indices=[3],generated_tokens=1,decode_calls=0,decoder_cache=cache_state)


def io_snapshot():
    return {k:int(v.strip()) for k,v in (line.split(':',1) for line in Path('/proc/self/io').read_text(encoding='utf-8').splitlines())}


def run(engine,runtime,policy,base,here,output,result,patch,features,provider,switch):
    import m276_video_runtime as video
    protocol_sha=json.loads((here/'PERFORMANCE_PLAN.json').read_bytes())['protocol_sha256']
    if hashlib.sha256((here/'WARM_PROTOCOL.json').read_bytes()).hexdigest()!=protocol_sha:raise RuntimeError('Frozen warm protocol differs')
    visual_expected=provider.sources['visual']['preprocessed']
    references=provider.sources['language']['samples']
    prompt_ids=video.tokenize(engine.config['tokenizer'],video.M276_KNIFE_PROMPT,3.0)
    if len(prompt_ids)!=159 or prompt_ids!=json.loads((here/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']:raise RuntimeError('Fixed159 IDs differ')
    request=SimpleNamespace(prompt=video.M276_KNIFE_PROMPT,max_new_tokens=1,frames_rgb_u8=provider.frames)
    result.update(prompt=video.M276_KNIFE_PROMPT,prompt_token_ids=prompt_ids,output_budget=1,decode_calls=0,
                  selected_frame_indices=[3],views=2,samples=[],completed_language_physical=0,completed_visual_physical=0,
                  performance_measurements_collected=False,PS_prefetch=False,parser_workers=1,
                  last_layer_tail=False,SiLU_workspace=False,full_hashes_after_timers=True)
    captured={};stage_ms={};index=0
    original_preprocess=video.preprocess;original_prefill=engine.language.prefill
    provider.original_vision_call=engine.vision.__class__.__call__
    def timed_preprocess(*a,**kw):
        t=time.perf_counter();answer=original_preprocess(*a,**kw);stage_ms['preprocess']=(time.perf_counter()-t)*1000
        captured['preprocessed']=answer;return answer
    def timed_vision(self,*a,**kw):
        if self is not engine.vision:raise RuntimeError('Unexpected concurrent visual instance')
        t=time.perf_counter();answer=provider(index,*a,**kw);stage_ms['vision']=(time.perf_counter()-t)*1000
        captured['visual']=answer;return answer
    def timed_prefill(hidden):
        captured['input']=hidden;result['model_forward_calls']+=1;result['language_scope_active']=True
        t=time.perf_counter()
        try:answer=original_prefill(hidden)
        finally:result['language_scope_active']=False
        stage_ms['prefill']=(time.perf_counter()-t)*1000;captured['output']=answer;return answer
    original_head=runtime.lm_head
    def timed_head(*a,**kw):
        t=time.perf_counter();answer=original_head(*a,**kw);stage_ms['head']=(time.perf_counter()-t)*1000;return answer
    patch(video,'preprocess',timed_preprocess);patch(engine.vision.__class__,'__call__',timed_vision)
    patch(engine.language,'prefill',timed_prefill);patch(runtime,'lm_head',timed_head)
    def forbid_extra(*a,**kw):
        result['blocked_inference_attempts'].append('extra-DMA.runtime.allocate')
        raise RuntimeError('Original seven DMA sealed')
    patch(runtime,'allocate',forbid_extra)
    reference_environment=read_environment()
    if reference_environment['observability_issues']:raise RuntimeError('Warm environment unproven before first request')
    sequence=NaturalSequence(result,reference_environment,protocol_sha=protocol_sha)
    result['warm_environment_reference']=reference_environment
    for n,variant in enumerate(ORDER):
        sequence.before(n);index=1
        switch.select(variant,n+1)
        expected_build='0x4D343431' if variant=='A' else '0x4D343433'
        if provider.current_owner is not None or not policy.safe():raise RuntimeError('Previous request owner not closed')
        if result['released_buffers'] or runtime._m368_closed:raise RuntimeError('Same runtime must remain resident')
        captured.clear();stage_ms.clear();result['visual_staging']=[]
        before=copy.deepcopy(runtime.evidence());gqa=engine.language.grouped_attention_calls
        before_environment=read_environment();before_cache=engine.vision.decoder_evidence()
        before_memory=policy.capture('before-timed-request:'+str(n+1),True)
        before_io=io_snapshot();faults=resource.getrusage(resource.RUSAGE_SELF).ru_majflt
        policy.stop_event=threading.Event();policy.stop_reason=None;policy.sample_count=0;policy.extrema=None;policy.begin_sampling()
        print(f'M443P_REQUEST_BEGIN sample={n+1} variant={variant}',flush=True)
        events=[]
        for event,payload in engine.stream(request):events.append((event,payload))
        # complete.total_ms/first_token_ms stopped inside the original stream.
        after_io=io_snapshot();major_fault_delta=resource.getrusage(resource.RUSAGE_SELF).ru_majflt-faults
        after_environment=read_environment();after_cache=engine.vision.decoder_evidence()
        after_memory=policy.capture('after-timed-request:'+str(n+1),True);policy.stop_sampling()
        if provider.current_owner is not None or result.get('language_scope_active') or any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Request worker/owner retained')
        final=next(p for e,p in events if e=='complete')
        semantic=validate_request_stream(events,after_cache,expected_build)
        token,logits,kv=captured['output']
        numerical=dict(input=tensor(captured['input']),visual=tensor(captured['visual']),token=int(token),logits=tensor(logits),
                       keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values])
        expected=references[index]
        exact={k:numerical[k]==expected[k] for k in numerical}
        if not all(exact.values()) or {k:tensor(v) for k,v in sorted(captured['preprocessed'].items())}!=visual_expected:raise RuntimeError('Post-timer full visual/logits/KV reference differs')
        decision=expected['decision']
        if any(semantic['token'][a]!=decision[b] for a,b in [('token_id','token_id'),('text','text'),('knife_verdict','verdict'),('knife_score','knife_score')]):raise RuntimeError('Original stream constrained decision differs')
        after=copy.deepcopy(runtime.evidence());row=delta(before,after);check_call_contract(row,expected['counts']['logical_expected_macros'])
        if row!=expected['counts'] or engine.language.grouped_attention_calls-gqa!=36:raise RuntimeError('Per-request language transaction/retry contract differs')
        transactions=result.get('transactions',[]);visual_transactions=result.get('visual_transactions',[])
        expected_transactions=provider.sources['language']['transactions'][index*781:(index+1)*781]
        if transactions!=expected_transactions:raise RuntimeError('Complete post-timer language physical sequence differs')
        if len(transactions)!=781 or len([x for x in transactions if x['method']=='head-original-execute'])!=8:raise RuntimeError('Per-request physical head/language accounting differs')
        if len(visual_transactions)!=(286 if index else 0) or any(x.get('completed') is not True or not safe_to_release(x['completed_snapshot']) for x in visual_transactions):raise RuntimeError('Per-request visual completion/accounting differs')
        if index and (len(result['visual_staging'])!=22 or sum(x['bytes'] for x in result['visual_staging'])!=49020928 or result.get('visual_static_cache_invalidated') is not True):raise RuntimeError('Borrowed stage/cache lifecycle differs')
        snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma)
        if not policy.safe() or not safe_to_release(snapshot) or snapshot['ap_return']!=int(expected_build,16):raise RuntimeError('Request completion unsafe')
        sample=dict(index=n+1,variant=variant,kernel_build=expected_build,timing=dict(total_ms=final['total_ms'],first_token_ms=final['first_token_ms'],stages_ms=dict(stage_ms)),
                    numerical_SHA_after_timer=numerical,exact_saved_reference=exact,semantic=semantic,counts=row,
                    language_physical_observed=len(transactions),visual_physical_observed=len(visual_transactions),
                    physical_record_SHA_after_timer=hashlib.sha256(json.dumps(transactions,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                    visual_record_SHA_after_timer=hashlib.sha256(json.dumps(visual_transactions,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                    visual_staging=copy.deepcopy(result['visual_staging']),final_snapshot=snapshot,
                    before_environment=before_environment,after_environment=after_environment,before_cache=before_cache,after_cache=after_cache,
                    before_memory=before_memory,after_memory=after_memory,sampled_memory=copy.deepcopy(result['sampled_memory']),
                    io_delta={k:after_io[k]-before_io[k] for k in before_io},major_fault_delta=major_fault_delta,
                    all_visual_bindings_restored=True,original_seven_DMA_still_resident=True)
        result['samples'].append(sample)
        result['completed_language_physical']+=len(transactions);result['completed_visual_physical']+=len(visual_transactions)
        result['last_transaction']=transactions[-1];result['last_visual_transaction']=visual_transactions[-1] if visual_transactions else None
        result['transactions']=[];result['visual_transactions']=[]
        print(f'M443P_REQUEST_COMPLETE sample={n+1} variant={variant} total_ms={final["total_ms"]:.3f}',flush=True)
        captured.clear()
        del logits,kv,events,before,after,row,transactions,visual_transactions,numerical
        sequence.record(sample)
    result['all12_requests_completed']=True;result['numerical_pass']=True
    result['performance_measurements_collected']=True
    result['performance_pass']=False
    result['formal_promotion_allowed']=False
