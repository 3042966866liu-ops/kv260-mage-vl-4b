"""Fixed4 demo answer validation, then same128 hot ABBA TTFT, zero Decode."""
import gc,hashlib,json,os,time
from pathlib import Path
import numpy as np
from M455_128_native_pair523365 import NativePair
from M455_stage_benchmark523383 import Full22StageProfile128,counters,system,save,sha
from M455_request_guard52354 import physical_bound
from language_parser_profiler import ParserAB
from weight_prefetch import WeightPrefetch
from PS_crop_native import PSCropSelector
from visual_cache_profiler import CacheAB
from board_helpers import NoVisualProfiler as VisionProfiler, core, proof
from v4_recovery_native import V4Recovery
from board_subset import LanguageSubset,VisionSubset,StageSubset,verify_PS_counts
from board_visual_subset import SubsetVisualProvider

def classify(text):return {'yes':'Yes','true':'Yes','no':'No','false':'No'}.get(text.strip().casefold().rstrip('.,!?;:'),'Invalid')
def identity(hidden,logits,cache,retained):
    assert hidden.shape==(128,2560) and hidden.dtype==np.float32 and logits.shape==(151936,) and logits.dtype==np.float32
    assert np.isfinite(hidden).all() and np.isfinite(logits).all() and len(cache.keys)==len(cache.values)==len(retained)
    digest=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    result=dict(input_embeddings=digest(hidden),first_logits=digest(logits),token_id=int(logits.argmax()),retained_original_language=list(retained),keys=[],values=[])
    for arrays,name in ((cache.keys,'keys'),(cache.values,'values')):
        for x in arrays:
            assert x.shape==(128,8,128) and x.dtype==np.float32 and np.isfinite(x).all();result[name].append(digest(x))
    return result

class DemoPreparation:
    def __init__(self,engine,provider,frames,preprocess,embeddings,ids,request):
        self.engine,self.provider,self.frames,self.preprocess,self.embeddings,self.ids,self.request=engine,provider,frames,preprocess,embeddings,list(ids),request
    def __call__(self):
        from M455_four_block_request523366 import render
        ids=[int(v) for v in self.engine.tokenizer.encode(render(),add_special_tokens=False).ids]
        if ids!=self.ids or len(ids)!=128 or ids.count(151655)!=98:raise RuntimeError('Exact fixed128/98-slot question required')
        a=self.preprocess(np.ascontiguousarray(self.frames[None]))
        if a['pixel_values'].shape!=(392,768) or int(a['merged_visual_tokens'])!=98 or int(a['view_count'])!=2:raise RuntimeError('Original latest-frame/two-view geometry required')
        visual=self.provider(a['pixel_values'],a['image_grid_thw'],a['patch_positions'])
        hidden=self.embeddings(self.engine.language,ids,visual)
        if hidden.shape!=(128,2560) or hidden.dtype!=np.float32 or not np.isfinite(hidden).all():raise RuntimeError('Complete original embedding boundary required')
        return hidden,dict(request_id=self.request['id'],source_video=self.request['video'],video_sha256=self.request['video_sha256'],timestamp_ms=self.request['timestamp_ms'],frame_raw_sha256=hashlib.sha256(self.frames.tobytes()).hexdigest(),question='Is a knife visible in these views',actual_input_tokens=128,T32_blocks=4,visual_slots=98,views=2,latest_frame_only=True,video_file_decode_included=False,preprocess_visual_embedding_included=True)

class FixedDemoTrial(Full22StageProfile128):
    __init__=NativePair.__init__
    def _run(self):
        own=Path(__file__).resolve().parent;plan=json.loads((own/'DEMO_BOARD_PLAN.json').read_bytes())
        budget=plan['new_full_forwards_budget'];assert budget==13 and len(plan['demo_requests'])==1
        from live_protocol import Channel
        session=os.environ['CAMPUS_SESSION_ID'];channel=Channel(sha(own/'PACKAGE_MANIFEST.json'),session);self.live_channel=channel
        retained_v=plan['retained_vision'];retained_l=plan['retained_language']
        self.configure();import torch
        from learned_head import LearnedHead
        assert sha(own/'HEAD_MANIFEST.json')==plan['learned_head_manifest_sha256']
        self.learned_head=LearnedHead(own,json.loads((own/'HEAD_MANIFEST.json').read_bytes()));self.learned_head.install(self.runtime)
        self.PS_selector=PSCropSelector(torch,self.engine.vision,self.component,idle=self.idle);self.PS_selector.choose('B');self.cache_profiler=CacheAB(self.PS_selector)
        self.language_subset=LanguageSubset(self.engine.language,retained_l,self.idle,plan['M241_prefill_source_sha256'])
        self.vision_subset=VisionSubset(torch,self.engine.vision,retained_v,self.idle)
        self.v4_recovery=V4Recovery(torch,core(self.vision_subset.original[4]).mlp,own,self.idle)
        self.vision_profiler=VisionProfiler(torch,self.vision_subset.original,retained_v,vision_model=self.engine.vision.vision)
        self.subset_provider=SubsetVisualProvider(self.visual,retained_v,self.idle)
        ab=self.plan['parser_ab'];self.parser_profiler=ParserAB(self.runtime,ab['original_parse_sha256'],ab['original_resolve_sha256']);self.parser_profiler.install()
        windows=json.loads((self.component/'STAGE_WINDOWS.json').read_bytes())['windows']
        self.weight_profiler=WeightPrefetch(self.factory['base'],self.runtime,windows,self.plan['weight_copy_source_sha256'])
        self.stage_subset=StageSubset(self.runtime,self.weight_profiler,windows,retained_l,self.idle)
        import m273_latest_multiscale_contract as m273,m276_video_runtime as m276
        frames={}
        for r in plan['demo_requests']:
            file=own/r['frame_path'];assert sha(file)==r['frame_sha256'];a=np.load(file,allow_pickle=False)
            assert a.shape==(448,448,3) and a.dtype==np.uint8;frames[r['id']]=a
        requests=plan['demo_requests'];by_id={r['id']:r for r in requests}
        def schedule():
            yield 'VALID_WARMUP','B',requests[0],None
            for label,arm,request,job,frame in channel.jobs():
                frames[request['id']]=frame
                yield label,arm,request,job
        expected={};samples=[];saved_logits_bytes=0
        self.result.update(model_forwards=0,first_token_forward_budget=budget,total_prefill_budget=budget,actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,application_output='Actual unforced model first-token Yes/No/True/False => binary display; no forced answer; not naturalEOS evidence',demo_requests=requests,sample_summaries=samples,research_speed_only=False,learned_head_FP32_full_vocab=True,head_extra_MACs_included_in_TTFT=1235968,retained_vision=retained_v,retained_language=retained_l)
        for label,arm,request,ui_job in schedule():
            candidate=True;self.v4_recovery.select(arm=='B');self.session.select(True);self.language_subset.select(candidate);self.vision_subset.select(candidate)
            stages=self.stage_subset.select(candidate)
            # The original runtime contract is immutable; narrow only guard capabilities.
            chains=[]
            for c in self.session.original_language:
                if candidate and c['layer'] not in retained_l:continue
                key=(c['layer'],c['family']);chains.append(self.binding.entries[key][0] if key in self.binding.entries else c)
            self.guard.set_chains(chains+list(self.session.original_head))
            provider=self.subset_provider if candidate else self.visual
            self.prepare=DemoPreparation(self.engine,provider,frames[request['id']],m273.preprocess,m276.latest_input_embeddings,self.plan['token_ids'],request)
            self.cache_profiler.begin('B');self.PS_selector.begin_request();gc.collect();pl=sorted(set(retained_v)&set(range(13,24))) if candidate else list(range(13,24))
            self.guard.begin(label,physical_bound(128,1,visual=False)+7*26*len(pl));self.session.checkpoint()
            before=counters(self.runtime);system_before=system();
            mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','SwapTotal:'))}
            assert mem['MemAvailable']>=256<<20 and mem['SwapTotal']==0, 'Ordinary memory margin/swap contract failed'
            n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
            entry=dict(label=label,variant=arm,request_id=request['id'],entered=True,returned=False);self.result.setdefault('complete_request_entries',[]).append(entry);self.result['model_forwards']=len(self.result['complete_request_entries'])
            self.vision_profiler.begin(capture=label=='VALID_B_'+requests[0]['id']);self.parser_profiler.begin('B');print('FIXED_DEMO_TTFT_BEGIN '+label,flush=True)
            started=time.perf_counter_ns();hidden,input_record=self.prepare();prepared=time.perf_counter_ns();vision_profile=self.vision_profiler.end();self.session.checkpoint()
            prefill_started=time.perf_counter_ns();self.weight_profiler.begin('B');token,logits,cache=self.engine.language.prefill(hidden);first=time.perf_counter_ns()
            weight=self.weight_profiler.end();parse=self.parser_profiler.end();cache_profile=self.cache_profiler.end();entry['returned']=True
            ps=verify_PS_counts(self.PS_selector,retained_v if candidate else list(range(24)));vision=self.vision_subset.verify_request()
            self.session.checkpoint();self.guard.end();numerical=identity(hidden,logits,cache,retained_l if candidate else list(range(36)))
            if arm=='A':assert numerical==plan['parent_full_numerical_identity'][request['id']], 'Original4096 control identity differs from saved baseline'
            assert int(token)==numerical['token_id'];raw=self.engine.tokenizer.decode([int(token)],skip_special_tokens=True);answer=classify(raw);truth_correct=(answer==request['expected_decision']) if ui_job is None else None;correct=(truth_correct is True) if ui_job is None else answer in ('Yes','No')
            logits_proof=proof(logits)
            assert logits_proof['actual_full_vocab_argmax']==int(token)
            key=(arm,request['id'])
            if ui_job is None:expected[key]=numerical
            else:assert input_record['frame_raw_sha256']==request['pixel_sha256'], 'Actual received RGB input differs'
            native=self.result['transactions'][n:];visual_rows=self.result['visual_transactions'][v:];strict=self.result.get('strict_visual_completion_observations',[])
            assert native and {r['layer'] for r in visual_rows}==set(pl)
            assert 26*len(pl)<=len(visual_rows)<=7*26*len(pl) and len(strict)==len(visual_rows) and all(r['strict_completed'] for r in strict)
            actual_language={r['layer'] for r in native if r['family']!='lm_head'}
            assert actual_language==set(retained_l if candidate else range(36)) and parse['successful']
            folder=self.out/label;folder.mkdir()
            # All151936 logits are evaluated/hash-checked online against the exact saved parent; no duplicate NPY.
            record=dict(label=label,variant=arm,request_id=request['id'],validation=label.startswith('VALID_'),first_token_wall_s=(first-started)/1e9,prepare_s=(prepared-started)/1e9,prefill_s=(first-prefill_started)/1e9,prefill_checkpoint_s=(prefill_started-prepared)/1e9,actual_input_tokens=128,T32_blocks=4,decode_calls=0,token_id=int(token),raw_first_token=raw,display_decision=answer,expected_decision=request['expected_decision'],answer_correct=truth_correct,answer_valid=correct,natural_EOS_claimed=False,application_stop_after_decision=True,language_head_physical_calls=len(native),visual_physical_calls=len(visual_rows),logical_visual_batches=26*len(pl),retained_language=list(retained_l) if candidate else list(range(36)),retained_vision=list(retained_v) if candidate else list(range(24)),stage_schedule=stages,PS_component=ps,visual_cache_profile=cache_profile,vision_layer_profile=vision_profile,full_logits_saved=False,full_logits_evaluated_and_parent_SHA_checked=(arm=='A'),vision_bypass=vision,parse_summary={k:z for k,z in parse.items() if k not in ('rows','waits')},counters_before=before,counters_after=counters(self.runtime),system_before=system_before,system_after=system(),phase_sums_overlap_not_additive=True,learned_head_calls=self.learned_head.calls,learned_head_cumulative_s=self.learned_head.elapsed_s)
            trace_bytes=json.dumps(dict(instrumented=native,manual_visual=visual_rows,strict=strict),sort_keys=True,separators=(',',':')).encode()
            physical_proof=dict(language_head_calls=len(native),visual_calls=len(visual_rows),all_visual_strict=all(r['strict_completed'] for r in strict),full_trace_sha256=hashlib.sha256(trace_bytes).hexdigest())
            for name,data in [('SAMPLE.json',record),('INPUT.json',input_record),('NUMERICAL_IDENTITY.json',numerical),('FULL_LOGITS_PROOF.json',logits_proof),('PHYSICAL_COMPLETION_PROOF.json',physical_proof),('SCHEDULING_SUMMARY.json',dict(weight=weight['summary'],prefetch=weight['prefetch'],parser=record['parse_summary']))]:save(folder/name,data)
            summary={k:record[k] for k in ('label','variant','request_id','validation','first_token_wall_s','prepare_s','prefill_s','raw_first_token','display_decision','answer_correct','language_head_physical_calls','visual_physical_calls')};summary.update(visual_cache_profile=cache_profile,sample_sha256=sha(folder/'SAMPLE.json'),full_logits_FP32_sha256=numerical['first_logits'],vision_layer_profile=vision_profile);samples.append(summary);save(self.out/('SAVED_'+label+'.json'),summary)
            print('FIXED_DEMO_TTFT_SAVED',label,record['first_token_wall_s'],raw,correct,flush=True)
            if ui_job is not None:
                ui_proof=dict(status='COMPLETE_M544_LIVE_REQUEST_ORIGINAL_OWNERS_STILL_LIVE',primary_rc=0,session=session,ui_job_id=ui_job['id'],case_id=request['id'],frame_sha256=request['frame_sha256'],pixel_sha256=request['pixel_sha256'],package_manifest_sha256=sha(own/'PACKAGE_MANIFEST.json'),base_model_manifest_sha256=plan['base_model_manifest_sha256'],actual_full_vocab=151936,argmax_verified=True,physical_calls=len(native),visual_physical_calls=len(visual_rows),decision=answer,raw_token=raw,TTFT_s=record['first_token_wall_s'],prepare_s=record['prepare_s'],prefill_s=record['prefill_s'],full_logits_sha256=numerical['first_logits'],logits_sha256=numerical['first_logits'],source_sample_sha256=sha(folder/'SAMPLE.json'),completed_request=True,owner_released=False,stable_restored=False,truth_label_not_used_for_live_decision=True)
                save(folder/'UI_RESULT.json',ui_proof);channel.packet('RESULT',ui_proof)
                frames.pop(request['id'],None)

            cache.keys.clear();cache.values.clear();del hidden,logits,cache,native,visual_rows,strict,numerical;gc.collect()
            self.result['transactions']=[];self.result['visual_transactions']=[];self.result['strict_visual_completion_observations']=[]
            assert correct, 'Trained fixed-window answer incorrect: no later hot requests'
            if ui_job is None:
                channel.fixed_gate_proof=dict(status='PASS_M544_CURRENT_BOOT_FIXED_WARMUP_BEFORE_WEB',primary_rc=0,boot_id=plan['expected_boot'],session=session,package_manifest_sha256=sha(own/'PACKAGE_MANIFEST.json'),completed_request=True,decision=answer,expected_decision=request['expected_decision'],answer_correct=truth_correct,frame_sha256=request['frame_sha256'],actual_full_vocab=151936,argmax_verified=True,logits_sha256=summary['full_logits_FP32_sha256'],source_sample_sha256=summary['sample_sha256'],physical_calls=record['language_head_physical_calls'],visual_physical_calls=record['visual_physical_calls'],input_tokens=128,T32_blocks=4,decode_calls=0,owners_still_live=True)
        assert 1<=len(samples)<=budget and self.learned_head.calls==len(samples)
        self.idle()
        self.result.update(total_prefills_returned=len(samples),first_token_samples_returned=len(samples),warmup_correct=samples[0]['answer_correct'] is True,live_jobs_returned=len(samples)-1,learned_head_calls=self.learned_head.calls,learned_head_total_s=self.learned_head.elapsed_s,production_promoted=False,heldout_quality_proven=False,session=session)

    def close(self):
        w=getattr(self,'weight_profiler',None)
        if w is not None and w.active:w.abort()
        self.idle()
        v4=getattr(self,'v4_recovery',None)
        if v4 is not None:v4.close()
        profiler=getattr(self,'vision_profiler',None)
        if profiler is not None:profiler.close(idle=self.idle)
        h=getattr(self,'learned_head',None)
        if h is not None:h.close()
        for name in ('language_subset','vision_subset'):
            x=getattr(self,name,None)
            if x is not None and not x.closed:x.close()
        selector=getattr(self,'PS_selector',None)
        if selector is not None and not selector.closed:selector.close()
        return super().close()
