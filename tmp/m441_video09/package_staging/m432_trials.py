"""Two unchanged M241 Prefills from immutable M414 features; zero visual calls."""
import copy,json,threading,time
import numpy as np
from m428_saved_features import tensor,save_array,compare_logits,load_features
from m368_video_contract import check_call_contract
from m368_stage_policy import FAMILIES

COUNTERS={'logical_calls':'logical_calls','host_calls':'host_calls','retry_count':'scale_retry_count','retry_launches':'pipeline_retry_launches','nonfinite_detections':'fused_nonfinite_detections','stage_bytes':'stage_bytes','logical_expected_macros':'logical_expected_macros','expected_macros':'expected_macros'}

def delta(before,after):
    row={key:after[value]-before[value] for key,value in COUNTERS.items()}
    prior=before['scale_attempts'];attempts=after['scale_attempts']
    if attempts[:len(prior)]!=prior:raise ValueError('Retry history mutated')
    row['scale_attempts']=attempts[len(prior):]
    return row

def run(engine,runtime,policy,base,here,output,result,patch,features,provider):
    import m276_video_runtime as video
    from m246_knife_binary import constrained_knife_decision
    expected=json.loads((here/'VIDEO_EXPECTED.json').read_bytes())['baseline']
    visual_expected=json.loads((here/'VISUAL_EXPECTED.json').read_bytes())
    ids=video.tokenize(engine.config['tokenizer'],video.M276_KNIFE_PROMPT,3.0)
    if ids!=visual_expected['prompt_token_ids'] or len(ids)!=159:raise ValueError('Exact159 prompt IDs differ')
    result.update(prompt=video.M276_KNIFE_PROMPT,prompt_token_ids=ids,output_budget=1,decode_calls=0,
                  vision_forward_calls=0,selected_frame_indices=[3],views=2,samples=[],logit_files=[])
    model=engine.language;original_family=model._family;families=[]
    def family(layer,name,values):
        if len(families)>=len(FAMILIES) or (layer,name)!=FAMILIES[len(families)]:raise ValueError('Family sequence escaped')
        if name in ('q','qkv'):print('M441V_LAYER '+str(layer),flush=True)
        policy.capture('before-family:'+str(layer)+':'+name,True)
        answer=original_family(layer,name,values)
        families.append(dict(layer=layer,family=name,input=tensor(values),output={k:tensor(v) for k,v in sorted(answer.items())}))
        policy.capture('after-family:'+str(layer)+':'+name,True)
        return answer
    patch(model,'_family',family)
    original_logits=None;decisions=[]
    for i,visual in ((1,features[1]),):
        visual=provider(i)
        variant='original' if i==0 else 'late13_23_candidate';families.clear()
        hidden=video.latest_input_embeddings(model,ids,visual)
        if hidden.shape!=(159,2560):raise ValueError('Hidden contract differs')
        if i==0 and tensor(hidden)!=expected['input']:raise ValueError('Original embedding reference differs')
        before=copy.deepcopy(runtime.evidence());gqa=model.grouped_attention_calls;start_count=len(result.get('transactions',[]))
        policy.stop_event=threading.Event();policy.stop_reason=None;policy.sample_count=0;policy.extrema=None
        policy.capture('before-'+variant+'-prefill',True);policy.begin_sampling()
        print('M441V_PREFILL_BEGIN '+variant,flush=True);started=time.monotonic()
        result['model_forward_calls']+=1
        result['language_scope_active']=True
        try:token,logits,kv=model.prefill(hidden)
        finally:result['language_scope_active']=False
        elapsed=time.monotonic()-started
        policy.capture('after-'+variant+'-prefill',True);policy.stop_sampling()
        after=copy.deepcopy(runtime.evidence());row=delta(before,after)
        check_call_contract(row,expected['logical_expected_macros'])
        transaction_delta=result['transactions'][start_count:]
        if len(transaction_delta)!=row['host_calls'] or len([t for t in transaction_delta if t['method']=='head-original-execute'])<8 or len(families)!=154 or model.grouped_attention_calls-gqa!=36 or len(kv.keys)!=36 or len(kv.values)!=36 or not policy.safe():raise ValueError('Incomplete language/physical/family/KV lifecycle')
        sample=dict(variant=variant,input=tensor(hidden),visual=tensor(visual),token=int(token),logits=tensor(logits),
            keys=[tensor(v) for v in kv.keys],values=[tensor(v) for v in kv.values],families=list(families),
            grouped_attention_calls=model.grouped_attention_calls-gqa,counts=row,physical_observed=len(transaction_delta),
            final_snapshot=base.transaction_snapshot(runtime.kernel,runtime.dma),sampled_memory=dict(result['sampled_memory']),
            elapsed_s_diagnostic_not_performance=elapsed)
        for field in ('keys','values'):
            if any({k:x[k] for k in ('shape','dtype','bytes')}!={k:y[k] for k in ('shape','dtype','bytes')} for x,y in zip(sample[field],expected[field])):raise ValueError('Full159 KV geometry differs')
        decision=constrained_knife_decision(logits);sample['decision']=decision;decisions.append(decision)
        result['logit_files'].append(save_array(output/(variant+'_logits.npy'),logits))
        result['samples'].append(sample)
        saved=provider.sources['language']['samples'][i]
        exact_integrated={key:sample[key]==saved[key] for key in ('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')}
        result.setdefault('integrated_exact_comparisons',[]).append(exact_integrated)
        if not all(exact_integrated.values()):raise ValueError('Full integrated language differs from saved M428 reference')
        result['original_exact_comparison']=dict(exact_integrated,decision=decision==saved['decision'])
        if not all(result['original_exact_comparison'].values()):raise ValueError('Accepted M437-policy decision differs')
        result['original_reference_pass']=True
        result['candidate_finite_complete']=True
        result['saved_reference_variant']='late13_23_candidate'
        print('M441V_PREFILL_COMPLETE '+variant+' '+decision['verdict'],flush=True)
        del hidden,logits,kv,after,before,transaction_delta,sample,row
        families.clear()
    checked,identities=load_features(json.loads((here/'PLAN.json').read_bytes()))
    del checked
    if identities!=result['saved_feature_identities']:raise ValueError('Saved features changed during language test')
    result['saved_features_unchanged_after']=True
    result['numerical_pass']=True;result['decision_consistency_pass']=True
    result['semantic_accuracy_proven']=False;result['expanded_24_layers']=False
