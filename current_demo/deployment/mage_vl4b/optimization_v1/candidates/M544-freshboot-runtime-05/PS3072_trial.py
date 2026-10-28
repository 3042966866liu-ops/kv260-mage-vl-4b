"""Bounded warmed native current22 A vs onlyV12 PL B; same parser and prefetch."""
import gc,json,time
import numpy as np
from M455_128_native_pair523365 import NativePair
from M455_stage_benchmark523383 import Full22StageProfile128,counters,system,identity128,save,sha
from M455_request_guard52354 import physical_bound
from gate_up_profiler import ParserAB
from weight_prefetch import WeightPrefetch
from PS_crop_native import PSCropSelector


class PS3072Trial(Full22StageProfile128):
    __init__=NativePair.__init__
    def _run(self):
        ab=self.plan['parser_ab'];schedule=self.plan['PS3072_ttft']['schedule']
        assert schedule==[['WARMUP_A1','A'],['WARMUP_B1','B'],['HOT_A1','A'],['HOT_B1','B'],
            ['HOT_B2','B'],['HOT_A2','A']]
        assert self.plan['max_input_tokens']==128 and self.plan['new_full_model_forwards_budget']==6
        self.configure()
        import torch
        self.PS_selector=PSCropSelector(torch,self.engine.vision,self.component,idle=self.idle)
        self.parser_profiler=ParserAB(self.runtime,ab['original_parse_sha256'],ab['original_resolve_sha256']);self.parser_profiler.install()
        windows=json.loads((self.component/'STAGE_WINDOWS.json').read_bytes())['windows']
        self.weight_profiler=WeightPrefetch(self.factory['base'],self.runtime,windows,self.plan['weight_copy_source_sha256'])
        expected=json.loads((self.component/'EXPECTED128.json').read_bytes());samples=[];B_identity=None
        self.result.update(complete_request_forward_budget=0,first_token_forward_budget=6,total_prefill_budget=6,
            actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,sample_summaries=samples,
            parser_AB_order='one_warmup_each_then_ABBA',gateup_C_both_arms=True,weight_prefetch_both_arms=True,
            PS3072_only_B=True,PS_crop_layers=[2,3,6],PS_width=3072,language_and_head_unchanged=True,production_promoted=False)
        for label,arm in schedule:
            self.session.select(True);self.PS_selector.choose(arm);self.PS_selector.begin_request();gc.collect()
            budget=physical_bound(128,1,visual=False)+7*(286)
            self.guard.begin(label,budget);self.session.checkpoint()
            before=counters(self.runtime);system_before=system()
            n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
            entry=dict(label=label,variant=arm,entered=True,returned=False);self.result.setdefault('complete_request_entries',[]).append(entry)
            self.result['model_forwards']=len(self.result['complete_request_entries']);self.parser_profiler.begin('B')
            print('PS3072_TTFT_BEGIN '+label,flush=True)
            began=time.perf_counter_ns();hidden,inputs=self.prepare();prepared=time.perf_counter_ns()
            self.session.checkpoint();prefill_started=time.perf_counter_ns();self.weight_profiler.begin('B')
            token,logits,cache=self.engine.language.prefill(hidden);first=time.perf_counter_ns()
            weight=self.weight_profiler.end();parse=self.parser_profiler.end();PS=self.PS_selector.end_request();entry['returned']=True
            self.session.checkpoint();self.guard.end();after=counters(self.runtime);system_after=system()
            numerical=identity128(hidden,logits,cache)
            assert int(token)==numerical['token_id']==expected['token_id']==2753
            if arm=='A':assert numerical==expected,'Reference current22 complete identity differs'
            elif B_identity is None:B_identity=numerical.copy()
            else:assert numerical==B_identity,'Candidate full input/logits/all72KV repeat identity differs'
            native=self.result['transactions'][n:];visual=self.result['visual_transactions'][v:];strict=self.result.get('strict_visual_completion_observations',[])
            logical=286
            assert native and logical<=len(visual)<=7*logical and len(strict)==len(visual) and all(s['strict_completed'] for s in strict)
            assert {r['layer'] for r in visual}==set(range(13,24))
            assert parse['successful'] and parse['calls']>0
            record=dict(label=label,variant=arm,warmup=label.startswith('WARMUP'),first_token_wall_s=(first-began)/1e9,
                prepare_s=(prepared-began)/1e9,prefill_s=(first-prefill_started)/1e9,
                prefill_checkpoint_s=(prefill_started-prepared)/1e9,actual_input_tokens=128,T32_blocks=4,decode_calls=0,PS_component=PS,
                native_counters_before=before,native_counters_after=after,system_before=system_before,system_after=system_after,
                language_head_physical_calls=len(native),visual_physical_calls=len(visual),logical_visual_batches=logical,
                parse_summary={k:v for k,v in parse.items() if k not in ('rows','waits')},
                asynchronous_pack_parse_phase_sums_not_additive=True)
            folder=self.out/label;folder.mkdir()
            for name,value in [('INPUT.json',inputs),('SAMPLE.json',record),('NUMERICAL_IDENTITY.json',numerical),
                ('PARSER_PROFILE.json',parse),('WEIGHT_STAGE_PROFILE.json',weight),
                ('PHYSICAL_TRANSACTIONS.json',dict(instrumented=native,manual_visual=visual)),('STRICT_VISUAL_COMPLETION.json',dict(observations=strict))]:save(folder/name,value)
            summary={k:record[k] for k in ('label','variant','warmup','first_token_wall_s','prepare_s','prefill_s','parse_summary')}
            summary.update(sample_sha256=sha(folder/'SAMPLE.json'),language_head_physical_calls=len(native),visual_physical_calls=len(visual),weight_profile=weight['summary'])
            samples.append(summary);save(self.out/('SAVED_'+label+'.json'),summary)
            print('PS3072_TTFT_SAVED '+label+' '+str(record['first_token_wall_s']),flush=True)
            cache.keys.clear();cache.values.clear();del hidden,logits,cache,native,visual,strict,numerical;gc.collect()
            self.result['transactions']=[];self.result['visual_transactions']=[];self.result['strict_visual_completion_observations']=[]
        hot=samples[2:];a=[s['first_token_wall_s'] for s in hot if s['variant']=='A'];b=[s['first_token_wall_s'] for s in hot if s['variant']=='B']
        assert len(a)==len(b)==2
        blocks=[]
        for block in (hot,):
            aa=[s['first_token_wall_s'] for s in block if s['variant']=='A'];bb=[s['first_token_wall_s'] for s in block if s['variant']=='B']
            saving=sum(aa)/2-sum(bb)/2;noise=max(max(aa)-min(aa),max(bb)-min(bb))
            blocks.append(dict(order=''.join(s['variant'] for s in block),A_s=aa,B_s=bb,saved_s=saving,within_variant_range_s=noise,
                positive_and_exceeds_range=saving>0 and saving>noise))
        am,bm=sum(a)/2,sum(b)/2;gain=1-bm/am
        self.result.update(total_prefills_returned=6,first_token_samples_returned=6,
            PS3072_TTFT_result=dict(hot_A_s=a,hot_B_s=b,A_mean_s=am,B_mean_s=bm,saved_s=am-bm,gain_fraction=gain,blocks=blocks,
                observed_net_gain_pass=am>bm and all(x['positive_and_exceeds_range'] for x in blocks),
                gain_at_least_5percent=gain>=.05,small_sample_observation=True,extra_sampling_allowed=False),
            strict_TTFT_limit_s=92.0,strict_TTFT_pass=all(s['first_token_wall_s']<92 for s in samples),
            performance_pass=False,target30_observed=all(s['first_token_wall_s']<30 for s in hot),
            production_promoted=False,heldout_quality_proven=False,semantic_quality_pass=None)

    def close(self):
        selector=getattr(self,'PS_selector',None)
        if selector is not None and not selector.closed:selector.close()
        return super().close()
