"""Bounded native KV260 prefill/decode loop. No hardware construction at import.

Input preparation includes original preprocessing/vision/embedding when called
by the full request provider. Fixed work feeds frozen ORIGINAL tokens; free
work feeds actual argmax tokens. No constrained binary-logit substitution.
"""
import time
import numpy as np

EOS=151645
CAP=32
VOCAB=151936

def validate_cache(cache, length):
    if len(cache.keys)!=36 or len(cache.values)!=36:
        raise RuntimeError('All 72 KV tensors required')
    for key,value in zip(cache.keys,cache.values):
        if key.dtype!=np.float32 or value.dtype!=np.float32 or key.shape!=(length,8,128) or value.shape!=(length,8,128):
            raise RuntimeError('Native KV geometry, position or dtype differs')

def generate(language,prepare,tokenizer,*,mode,teacher_tokens=None,checkpoint=lambda:None,clock=time.perf_counter):
    if mode not in ('fixed','free'):raise ValueError('Frozen fixed/free mode required')
    if mode=='fixed':
        if not isinstance(teacher_tokens,list) or not 1<=len(teacher_tokens)<=CAP or any(type(i)is not int or not 0<=i<VOCAB for i in teacher_tokens):
            raise ValueError('Frozen original teacher token IDs required')
        if EOS in teacher_tokens[:-1]:raise ValueError('Original prefix cannot feed beyond EOS')
    elif teacher_tokens is not None:raise ValueError('Free mode must use actual generated prefix')
    checkpoint();began=clock();hidden,input_record=prepare();prepared=clock()
    x=np.asarray(hidden)
    if x.dtype!=np.float32 or x.ndim!=2 or x.shape[1]!=2560 or not 1<=len(x)<=992 or not np.isfinite(x).all():
        raise ValueError('Finite native prompt with room for 31 decode steps required')
    count=len(teacher_tokens) if mode=='fixed' else CAP
    checkpoint();t=clock();token,logits,cache=language.prefill(x);first=clock()
    validate_cache(cache,len(x))
    first_keys=tuple(cache.keys);first_values=tuple(cache.values)
    # Preserve arrays, not 32 full cache copies. No SHA/files inside timed loop.
    prefill_s=first-t;steps=[];outputs=[];emitted=[];argmax=[];fed=[]
    for index in range(count):
        if index:
            checkpoint();previous=emitted[-1];fed.append(previous);t=clock()
            token,logits=language.decode(previous,cache);ended=clock()
            validate_cache(cache,len(x)+index)
            step_s=ended-t
        else:step_s=prefill_s
        z=np.asarray(logits)
        if z.shape!=(VOCAB,) or z.dtype!=np.float32 or not np.isfinite(z).all() or int(z.argmax())!=int(token):
            raise RuntimeError('Complete native logits/actual argmax required')
        outputs.append(z);argmax.append(int(token))
        actual=int(teacher_tokens[index]) if mode=='fixed' else int(token)
        emitted.append(actual);steps.append(step_s)
        if mode=='free' and actual==EOS:break
    text=tokenizer.decode(emitted,skip_special_tokens=True)
    stopped=clock()
    validate_cache(cache,len(x)+len(emitted)-1)
    record=dict(mode=mode,token_ids=emitted,token_count=len(emitted),argmax_token_ids=argmax,
        tokens_fed_after_prompt=fed,text=text,prompt_tokens=len(x),
        stop_reason=('fixed_original_prefix_complete' if mode=='fixed' else ('EOS' if emitted[-1]==EOS else 'token_cap')),
        ended_with_eos=emitted[-1]==EOS,reached_cap=mode=='free' and emitted[-1]!=EOS,
        decode_calls=len(emitted)-1,cache_initial_length=0,cache_final_length=len(x)+len(emitted)-1,
        timing=dict(total_s=stopped-began,prepare_s=prepared-began,prefill_s=prefill_s,
            first_token_s=first-began,decode_step_s=steps[1:],decode_sum_s=sum(steps[1:]),
            decode_mean_s=sum(steps[1:])/len(steps[1:]) if len(steps)>1 else None,
            tokenizer_and_loop_included=True,model_loading_included=False,
            full_hashes_and_file_export_included=False,steps_are_nested_not_additive_to_total=True))
    tensors=dict(input_embeddings=x,logits=np.stack(outputs),prefill_keys=first_keys,prefill_values=first_values,
        final_keys=tuple(cache.keys),final_values=tuple(cache.values))
    # Native model stores KV only in its returned request object. Clear the
    # container after retaining the arrays for post-timer complete verification.
    cache.keys.clear();cache.values.clear()
    if cache.keys or cache.values:raise RuntimeError('Request KV container not empty')
    record['cache_cleared_length']=0
    return record,tensors,input_record
