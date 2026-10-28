"""Fixed current22/128 request: two warmups then hot ABBA, zero Decode."""
import gc,json,time
import numpy as np
from M455_128_native_pair523365 import NativePair,save,sha
from M455_request_guard52354 import physical_bound
from weight_prefetch import WeightPrefetch
from gate_up_profiler import ParserAB


def system():
    from pathlib import Path
    return {n:Path(n).read_text()[:14000] for n in ('/proc/self/io','/proc/self/status','/proc/meminfo')}


def counters(r):
    keys=('stage_ms','stage_bytes','host_calls','logical_calls','scale_retry_count',
          'pipeline_retry_launches','fused_nonfinite_detections','pack_prefetch_compute_ms','pack_prefetch_wait_ms')
    return dict(scalar={k:getattr(r,k) for k in keys},phase_ms=dict(r.phase_ms),phase_calls=dict(r.phase_calls))


def identity128(hidden,logits,cache):
    import hashlib
    assert hidden.shape==(128,2560) and hidden.dtype==np.float32 and logits.shape==(151936,) and logits.dtype==np.float32
    assert np.isfinite(hidden).all() and np.isfinite(logits).all() and len(cache.keys)==len(cache.values)==36
    raw=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    v=dict(input_embeddings=raw(hidden),first_logits=raw(logits),token_id=int(logits.argmax()),keys=[],values=[])
    for group,name in ((cache.keys,'keys'),(cache.values,'values')):
        for a in group:
            assert a.shape==(128,8,128) and a.dtype==np.float32 and np.isfinite(a).all()
            v[name].append(raw(a))
    return v


class Full22StageProfile128(NativePair):
    def close(self):
        w=getattr(self,'weight_profiler',None)
        if w is not None and w.active:w.abort()
        self.idle()
        p=getattr(self,'parser_profiler',None)
        if p is not None:
            if p.active:self.result['parser_failure_profile']=p.end()
            p.restore()
        p=getattr(self,'weight_profiler',None)
        if p is not None:
            p.active=False;p.restore()
        return super().close()

    def _run(self):
        ab=self.plan['parser_ab']
        schedule=[('WARMUP_A1', 'A'), ('WARMUP_A2', 'A'), ('HOT_A1', 'A'), ('HOT_B1', 'B'), ('HOT_B2', 'B'), ('HOT_A2', 'A')]
        assert ab['schedule']==[[label,arm] for label,arm in schedule]
        assert self.plan['max_input_tokens']==128 and self.plan['new_full_model_forwards_budget']==6
        self.configure()
        self.parser_profiler=ParserAB(self.runtime,ab['original_parse_sha256'],ab['original_resolve_sha256'])
        self.parser_profiler.install()
        windows=json.loads((self.component/'STAGE_WINDOWS.json').read_bytes())['windows']
        self.weight_profiler=WeightPrefetch(self.factory['base'],self.runtime,windows,self.plan['weight_copy_source_sha256'])
        expected=json.loads((self.component/'EXPECTED128.json').read_bytes());samples=[]
        self.result.update(complete_request_forward_budget=0,first_token_forward_budget=6,total_prefill_budget=6,
            actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,sample_summaries=samples,
            parser_AB_order='two_warmups_A_then_ABBA',parser_AB_only_language_family=True, gateup_C_both_arms=True, weight_prefetch_only_B=True, both_arms_RAM=True,
            LM_head_visual_weights_and_DMA_completion_unchanged=True,production_promoted=False)
        for label,arm in schedule:
            self.session.select(True);gc.collect()
            self.guard.begin(label,physical_bound(128,1,visual=True));self.session.checkpoint()
            before=counters(self.runtime);system_before=system()
            n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
            entry=dict(label=label,variant=arm,entered=True,returned=False)
            self.result.setdefault('complete_request_entries',[]).append(entry)
            self.result['model_forwards']=len(self.result['complete_request_entries'])
            self.parser_profiler.begin('B')
            print('WEIGHT_PREFETCH_BEGIN '+label,flush=True)
            began=time.perf_counter_ns();hidden,inputs=self.prepare();prepared=time.perf_counter_ns()
            self.session.checkpoint();prefill_started=time.perf_counter_ns();self.weight_profiler.begin(arm)
            token,logits,cache=self.engine.language.prefill(hidden);first=time.perf_counter_ns()
            weight=self.weight_profiler.end();parse=self.parser_profiler.end();entry['returned']=True
            self.session.checkpoint();self.guard.end();after=counters(self.runtime);system_after=system()
            numerical=identity128(hidden,logits,cache)
            assert int(token)==numerical['token_id'] and numerical==expected,'Complete input/logits/all72 KV identity differs'
            native=self.result['transactions'][n:];visual=self.result['visual_transactions'][v:]
            strict=self.result.get('strict_visual_completion_observations',[])
            assert native and len(visual)>=286 and len(strict)==len(visual) and all(x['strict_completed'] for x in strict)
            assert parse['successful'] and parse['calls']>0
            record=dict(label=label,variant=arm,warmup=label.startswith('WARMUP'),
                first_token_wall_s=(first-began)/1e9,prepare_s=(prepared-began)/1e9,
                prefill_s=(first-prefill_started)/1e9,prefill_checkpoint_s=(prefill_started-prepared)/1e9,
                actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,token_id=int(token),
                numerical_identity=numerical,full_identity_equal_to_EXPECTED128=True,
                counters_before=before,counters_after=after,system_before=system_before,system_after=system_after,
                parse_summary={k:v for k,v in parse.items() if k not in ('rows','waits')},
                asynchronous_pack_parse_phase_sums_not_additive=True)
            folder=self.out/label;folder.mkdir()
            save(folder/'INPUT.json',inputs);save(folder/'SAMPLE.json',record)
            save(folder/'NUMERICAL_IDENTITY.json',numerical);save(folder/'PARSER_PROFILE.json',parse)
            save(folder/'WEIGHT_STAGE_PROFILE.json',weight)
            save(folder/'PHYSICAL_TRANSACTIONS.json',dict(instrumented=native,manual_visual=visual))
            save(folder/'STRICT_VISUAL_COMPLETION.json',dict(observations=strict))
            summary={k:record[k] for k in ('label','variant','warmup','first_token_wall_s','prepare_s','prefill_s','parse_summary')}
            summary.update(sample_sha256=sha(folder/'SAMPLE.json'),language_head_physical_calls=len(native),
                visual_physical_calls=len(visual),weight_profile=weight['summary'])
            samples.append(summary);save(self.out/('SAVED_'+label+'.json'),summary)
            print('WEIGHT_PREFETCH_SAVED '+label+' '+str(record['first_token_wall_s']),flush=True)
            cache.keys.clear();cache.values.clear();del hidden,logits,cache,native,visual,strict,numerical;gc.collect()
            self.result['transactions']=[];self.result['visual_transactions']=[];self.result['strict_visual_completion_observations']=[]
        hot=samples[2:];a=[s['first_token_wall_s'] for s in hot if s['variant']=='A'];b=[s['first_token_wall_s'] for s in hot if s['variant']=='B']
        am,bm=sum(a)/len(a),sum(b)/len(b);gain=1-bm/am;noise=max(max(a)-min(a),max(b)-min(b))
        self.result.update(total_prefills_returned=6,first_token_samples_returned=6,
            weight_prefetch_AB_result=dict(hot_A_s=a,hot_B_s=b,A_mean_s=am,B_mean_s=bm,saved_s=am-bm,
                gain_fraction=gain,within_variant_range_s=noise,minimum_gain_fraction=.05,
                observed_gain_pass=gain>=.05 and am-bm>noise,small_sample_observation=True),
            strict_TTFT_limit_s=92.0,strict_TTFT_pass=all(s['first_token_wall_s']<92 for s in samples),
            performance_pass=False,target30_observed=all(s['first_token_wall_s']<30 for s in hot),
            production_promoted=False,heldout_quality_proven=False,semantic_quality_pass=None)
