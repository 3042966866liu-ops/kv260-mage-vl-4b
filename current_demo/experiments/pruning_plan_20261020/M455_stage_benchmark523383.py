"""Two current22 actual128/4T32 first tokens; no Decode or extra per-call profiling."""
import gc,hashlib,time,json,os
from pathlib import Path
import numpy as np
from M455_128_native_pair523365 import NativePair,save,sha
from M455_request_guard52354 import physical_bound
from M455_full22_request_ABBA523332 import identity
from M455_weight_stage_profile523381 import WeightStageProfile

def system():
 r={}
 for name in ('/proc/self/io','/proc/self/status','/proc/meminfo','/proc/pressure/io'):
  try:r[name]=Path(name).read_text()[:14000]
  except OSError:r[name]=None
 return r

def counters(runtime):
 keys=('stage_ms','stage_bytes','host_calls','logical_calls','scale_retry_count','pipeline_retry_launches','fused_nonfinite_detections','pack_prefetch_compute_ms','pack_prefetch_wait_ms')
 return dict(scalar={k:getattr(runtime,k) for k in keys},phase_ms=dict(runtime.phase_ms),phase_calls=dict(runtime.phase_calls))

def identity128(hidden,logits,cache):
 assert hidden.shape==(128,2560) and hidden.dtype==np.float32 and logits.shape==(151936,) and logits.dtype==np.float32
 assert np.isfinite(hidden).all() and np.isfinite(logits).all() and len(cache.keys)==len(cache.values)==36
 raw=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
 v=dict(input_embeddings=raw(hidden),first_logits=raw(logits),token_id=int(logits.argmax()),keys=[],values=[])
 for group,name in ((cache.keys,'keys'),(cache.values,'values')):
  for a in group:
   assert a.shape==(128,8,128) and a.dtype==np.float32 and np.isfinite(a).all();v[name].append(raw(a))
 return v

class Full22StageProfile128(NativePair):
 def save_arrays(self,folder,hidden,logits,cache):
  expected=json.loads((self.component/'EXPECTED128.json').read_bytes())
  assert identity128(hidden,logits,cache)==expected,'Current128 differs from all148 previously audited full arrays'
  save(folder/'NUMERICAL_IDENTITY.json',expected)
 def close(self):
  self.idle()
  if getattr(self,'weight_profiler',None) is not None:
   self.weight_profiler.active=False;self.weight_profiler.restore()
  return super().close()
 def _run(self):
  assert self.plan['max_input_tokens']==128 and self.plan['new_full_model_forwards_budget']==2
  self.configure();expected=None;samples=[]
  self.weight_profiler=WeightStageProfile(self.plan['weight_copy_source_sha256']);self.weight_profiler.install(self.factory['base'])
  self.result.update(complete_request_forward_budget=0,first_token_forward_budget=2,total_prefill_budget=2,
   actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,natural_complete_requests_returned=0,sample_summaries=samples,
   shortened_user_requested_task_not_pure_identical_prompt_length_ablation=True,extra_per_transaction_profiler=False,weight_window_read_copy_sync_profiler=True)
  for label in ('B128_1','B128_2'):
   self.session.select(True);gc.collect();self.guard.begin(label,physical_bound(128,1,visual=True));self.session.checkpoint()
   system_before=system();c_before=counters(self.runtime)
   n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
   self.result.setdefault('complete_request_entries',[]).append(dict(label=label,entered=True,returned=False))
   self.result['model_forwards']=len(self.result['complete_request_entries']);print('M523_128_TTFT_BEGIN '+label,flush=True)
   began=time.perf_counter_ns();hidden,inputs=self.prepare();prepared=time.perf_counter_ns()
   self.session.checkpoint();prefill_started=time.perf_counter_ns()
   self.weight_profiler.begin()
   token,logits,cache=self.engine.language.prefill(hidden);first=time.perf_counter_ns()
   weight_profile=self.weight_profiler.end()
   self.result['complete_request_entries'][-1]['returned']=True
   # Finish actual guarded request before post-timer numerical/export checks.
   self.session.checkpoint();self.guard.end();c_after=counters(self.runtime);system_after=system()
   observed=identity128(hidden,logits,cache);assert int(token)==observed['token_id']
   if expected is None:expected=observed
   else:assert observed==expected,'Repeated current22 128-token prefill numerical identity changed'
   native=self.result['transactions'][n:];visual=self.result['visual_transactions'][v:]
   strict=self.result.get('strict_visual_completion_observations',[])
   assert native and len(visual)>=286 and len(strict)==len(visual) and all(x['strict_completed'] for x in strict)
   record=dict(label=label,arm='current22',actual_input_tokens=128,input_T32_blocks=4,decode_calls=0,
    first_token_wall_s=(first-began)/1e9,prepare_s=(prepared-began)/1e9,prefill_s=(first-prefill_started)/1e9,
    prefill_checkpoint_s=(prefill_started-prepared)/1e9,token_id=int(token),numerical_identity=observed,
    same_128_prefill_identity=True,counters_before=c_before,counters_after=c_after,system_before=system_before,system_after=system_after,
    original_runtime_phase_timers_only=False,extra_per_transaction_profiler=False,weight_window_read_copy_sync_profiler=True,
    asynchronous_pack_parse_phase_sums_not_additive=True,load_decode_hash_export_excluded=True)
   folder=self.out/label;folder.mkdir();save(folder/'INPUT.json',inputs);save(folder/'SAMPLE.json',record)
   self.save_arrays(folder,hidden,logits,cache)
   save(folder/'WEIGHT_STAGE_PROFILE.json',weight_profile)
   save(folder/'PHYSICAL_TRANSACTIONS.json',dict(instrumented=native,manual_visual=visual))
   save(folder/'STRICT_VISUAL_COMPLETION.json',dict(observations=strict))
   summary={k:record[k] for k in ('label','first_token_wall_s','prepare_s','prefill_s','token_id','same_128_prefill_identity')}
   summary.update(sample_sha256=sha(folder/'SAMPLE.json'),language_head_physical_calls=len(native),visual_physical_calls=len(visual))
   summary.update(weight_profile=weight_profile['summary'],profile_sha256=sha(folder/'WEIGHT_STAGE_PROFILE.json'))
   samples.append(summary);save(self.out/('SAVED_'+label+'.json'),summary)
   print('M523_128_TTFT_SAVED '+label+' '+str(record['first_token_wall_s']),flush=True)
   cache.keys.clear();cache.values.clear();del hidden,logits,cache,native,visual,strict,observed;gc.collect()
   self.result['transactions']=[];self.result['visual_transactions']=[];self.result['strict_visual_completion_observations']=[]
  t=[x['first_token_wall_s'] for x in samples]
  self.result.update(total_prefills_returned=2,first_token_samples_returned=2,TTFT_current22_128_mean_s=sum(t)/2,
   strict_TTFT_limit_s=92.0,strict_TTFT_pass=all(x<92 for x in t),performance_pass=all(x<92 for x in t),
   production_promoted=False,heldout_quality_proven=False,semantic_quality_pass=None,
   scope='User requested current22 actual128-token four-T32 first-token measurement, two samples, no Decode')
