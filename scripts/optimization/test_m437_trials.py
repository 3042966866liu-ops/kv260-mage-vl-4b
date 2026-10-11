"""Actual frozen stream/trials orchestration over explicitly fake model/DMA."""
import ast,copy,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace,ModuleType
import numpy as np
import m437_trials as trials
from m428_saved_features import tensor

def component(root):
    here=Path(__file__).parent
    fixture=json.loads((here/'NUMERIC_FIXTURE.json').read_bytes())
    counts=fixture['counts'];env=json.loads((here/'ENVIRONMENT_FIXTURE.json').read_bytes())['environment']
    env={k:v for k,v in env.items() if k not in ('thermal_zones','cooling_devices','temperature_source','temperature_ABI_source','temperature_channel_mapping_proven')}
    env.update(missing=[],temperature_measurement_enabled=False)
    cache=dict(cache_entries=26,cache_bytes=66699264,cache_misses=26,cache_within_budget=True)
    snap=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error='')
    result=dict(model_forward_calls=0,vision_forward_calls=0,blocked_inference_attempts=[],released_buffers=[],sampled_memory={},transactions=[],visual_transactions=[])
    sums={k:0 for k in ('logical_calls','host_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','stage_bytes','logical_expected_macros','expected_macros')};attempts=[]
    def evidence():return dict(build_id='0x4D333537',scale_attempts=copy.deepcopy(attempts),**sums)
    runtime=SimpleNamespace(evidence=evidence,allocate=lambda:None,lm_head=lambda x:np.zeros(151936,np.float32),kernel=None,dma=None,_m368_closed=False)
    hidden=np.zeros((159,2560),np.float32);visual=np.zeros((98,2560),np.float32)
    keys=[np.zeros((159,8,128),np.float32) for _ in range(36)];kv=SimpleNamespace(keys=keys,values=keys)
    language=SimpleNamespace(grouped_attention_calls=0)
    decision=dict(token_id=15,text='0',verdict='ABSENT',knife_score=.4,score_kind='fake-unscored-component')
    def prefill(x):
        from m432_trials import COUNTERS
        for k,v in COUNTERS.items():sums[v]+=counts[k]
        attempts.extend(copy.deepcopy(counts['scale_attempts']));language.grouped_attention_calls+=36
        index=result['fake_variant_index']
        result['transactions']=copy.deepcopy(fixture['transactions'][index*781:(index+1)*781])
        return 15,runtime.lm_head(x),kv
    language.prefill=prefill
    class Vision:
        def __call__(self,*args):result['vision_forward_calls']+=1;return visual
        def decoder_evidence(self):return copy.deepcopy(cache)
    vision=Vision()
    value=dict(pixel_values=np.zeros(1,np.float32),image_grid_thw=np.zeros(1,np.float32),patch_positions=np.zeros(1,np.float32))
    refs=[dict(input=tensor(hidden),visual=tensor(visual),token=15,logits=tensor(np.zeros(151936,np.float32)),keys=[tensor(x) for x in keys],values=[tensor(x) for x in keys],counts=copy.deepcopy(counts),decision=decision) for _ in range(2)]
    provider=SimpleNamespace(current_owner=None,frames=np.zeros((4,448,448,3),np.uint8),sources=dict(visual=dict(preprocessed={k:tensor(v) for k,v in value.items()}),language=dict(samples=refs,transactions=fixture['transactions'])),original_vision_call=None)
    class Provider:
        def __getattr__(self,k):return getattr(provider,k)
        def __setattr__(self,k,v):setattr(provider,k,v)
        def __call__(self,index,*args,**kw):
            result['fake_variant_index']=index
            cache.update(cache_entries=25 if index else 26,cache_bytes=62177280 if index else 66699264)
            if index:
                result['visual_transactions']=[dict(completed=True,completed_snapshot=snap) for _ in range(286)]
                result['visual_staging']=[dict(layer=i,part=p,bytes=2228224) for i in range(13,24) for p in ('fc1','fc2')]
                result['visual_static_cache_invalidated']=True
            return provider.original_vision_call(vision,*args,**kw)
    provider_proxy=Provider()
    video=ModuleType('m276_video_runtime');video.np=np;video.time=__import__('time')
    video.M276_KNIFE_PROMPT='[TELLME_KNIFE_BINARY_V3] Knife visible? Reply exactly 1 for yes or 0 for no:'
    ids=json.loads((here/'VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']
    video.tokenize=lambda *unused:ids;video.preprocess=lambda *unused:value;video.latest_input_embeddings=lambda *unused:hidden
    video.constrained_knife_decision=lambda *unused:decision
    video._server=SimpleNamespace(BUILD_ID='0x4D333537',KERNEL='fake',expected_physical_calls=lambda *unused:778)
    source=root/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'
    cls=next(x for x in ast.parse(source.read_text()).body if isinstance(x,ast.ClassDef) and x.name=='M276ShortPromptBinaryRuntime')
    fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='stream')
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),video.__dict__)
    import threading
    engine=SimpleNamespace(config={'tokenizer':'fake'},board=runtime,vision=vision,language=language,tokenizer=object(),_inference_lock=threading.Lock(),load=lambda:None)
    engine.stream=lambda request:video.stream(engine,request)
    policy=SimpleNamespace(safe=lambda:True,capture=lambda *unused:{},begin_sampling=lambda:None)
    policy.stop_sampling=lambda:result.update(sampled_memory=dict(observer_stopped=True,stop_reason=None))
    base=SimpleNamespace(transaction_snapshot=lambda *unused:snap)
    old=sys.modules.get('m276_video_runtime');sys.modules['m276_video_runtime']=video
    restorations=[]
    def patch(obj,name,replacement):restorations.append((obj,name,getattr(obj,name)));setattr(obj,name,replacement)
    original_env,original_io=trials.read_environment,trials.io_snapshot
    trials.read_environment=lambda:copy.deepcopy(env)
    fake_io_count=[0]
    def fake_io():
        fake_io_count[0]+=1
        return {'read_bytes':fake_io_count[0]*(777<<20)}
    trials.io_snapshot=fake_io
    try:
        trials.run(engine,runtime,policy,base,here,here,result,patch,[],provider_proxy)
        assert result['all12_requests_completed'] and result['model_forward_calls']==result['vision_forward_calls']==12
        assert result['completed_language_physical']==9372 and result['completed_visual_physical']==1716
        assert all(s['io_delta']['read_bytes']>1048576 for s in result['samples'])
        assert result['preconditioning_completed']
        assert len(result['warmup_samples'])==4 and len(result['formal_samples'])==8 and not result['transactions']
        assert all(all(s['exact_saved_reference'].values()) for s in result['samples'])
        try:runtime.allocate()
        except RuntimeError:pass
        else:raise AssertionError('Extra DMA not sealed')
        result['blocked_inference_attempts'].clear()
        result['synthetic_component_only']=True
        (here/'TRIALS_FIXTURE_RESULT.json').write_bytes(json.dumps(result,separators=(',',':')).encode())
    finally:
        for obj,name,original in reversed(restorations):setattr(obj,name,original)
        trials.read_environment,trials.io_snapshot=original_env,original_io
        if old is None:sys.modules.pop('m276_video_runtime',None)
        else:sys.modules['m276_video_runtime']=old
    return dict(original_stream_AST_executed=True,actual_trials_12_sequence=True,endpoint_hashes_after_timer=True,counts_and_observer_reset=True,extra_DMA_rejected=True,all_model_DMA_IO_and_environment_explicitly_fake=True)
