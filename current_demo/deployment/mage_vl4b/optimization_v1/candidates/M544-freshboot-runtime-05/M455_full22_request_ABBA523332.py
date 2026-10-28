"""Two natural complete fixed V2 requests then ABBA4 first-token comparisons, no new math."""
import gc,hashlib,time
from pathlib import Path
import numpy as np
from M455_full22_native_pair523330 import NativePair,save,sha
from M455_request_guard52354 import physical_bound

def raw_sha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

def identity(hidden,logits,keys,values):
 assert hidden.shape==(160,2560) and hidden.dtype==np.float32 and np.isfinite(hidden).all()
 assert logits.shape==(151936,) and logits.dtype==np.float32 and np.isfinite(logits).all()
 assert len(keys)==len(values)==36
 v=dict(input_embeddings=raw_sha(hidden),first_logits=raw_sha(logits),token_id=int(logits.argmax()),keys=[],values=[])
 for group,name in ((keys,'keys'),(values,'values')):
  for a in group:
   assert a.shape==(160,8,128) and a.dtype==np.float32 and np.isfinite(a).all();v[name].append(raw_sha(a))
 return v

class Full22RequestABBA(NativePair):
 def save_observations(self,label,first_native,first_visual):
  native=self.result['transactions'][first_native:];visual=self.result['visual_transactions'][first_visual:]
  strict=self.result.get('strict_visual_completion_observations',[])
  assert native and len(visual)>=286 and len(strict)==len(visual) and all(r['strict_completed'] for r in strict)
  folder=self.out/label;folder.mkdir(exist_ok=True)
  save(folder/'PHYSICAL_TRANSACTIONS.json',dict(instrumented=native,manual_visual=visual))
  save(folder/'STRICT_VISUAL_COMPLETION.json',dict(observations=strict))
  result=dict(language_head_physical_calls=len(native),visual_physical_calls=len(visual),
   physical_sha256=sha(folder/'PHYSICAL_TRANSACTIONS.json'),strict_sha256=sha(folder/'STRICT_VISUAL_COMPLETION.json'))
  self.result['transactions']=[];self.result['visual_transactions']=[];self.result['strict_visual_completion_observations']=[]
  return result
 def _run(self):
  self.configure();expected={};natural=[];samples=[]
  self.result.update(complete_request_forward_budget=2,first_token_forward_budget=4,total_prefill_budget=6,
   first_token_measured_order=['A1','B1','B2','A2'],sample_summaries=samples,complete_requests=natural,
   input_scope='historical_seen_M455_four_frame_bringup_fixture_not_heldout_or_6cal_quality',
   independent_heldout_quality_proven=False)
  for label,active in [('warm_A',False),('warm_B',True)]:
   self.idle();gc.collect();print('M523_FULL22_NATURAL_BEGIN '+label,flush=True)
   n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
   self.result['models']=1;self.result.setdefault('complete_request_entries',[]).append(dict(label=label,entered=True,returned=False))
   self.result['model_forwards']=len(self.result['complete_request_entries'])
   record,tensors,inputs=self.session.run(label=label,active=active,language=self.engine.language,prepare=self.prepare,
    tokenizer=self.engine.tokenizer,prompt_tokens=160,mode='free')
   self.result['complete_request_entries'][-1]['returned']=True
   arm='candidate' if active else 'original'
   expected[arm]=identity(tensors['input_embeddings'],tensors['logits'][0],tensors['prefill_keys'],tensors['prefill_values'])
   summary=self.persist_tensors(label,record,tensors,inputs)
   summary.update(self.save_observations(label,n,v));summary.update(arm=arm,first_token_s=record['timing']['first_token_s'])
   save(self.out/label/'PREFILL_IDENTITY.json',expected[arm]);natural.append(summary)
   save(self.out/('SAVED_'+label+'.json'),summary)
   print('M523_FULL22_NATURAL_SAVED '+label+' '+str(record['timing']['first_token_s']),flush=True)
   if record['stop_reason']!='EOS':raise RuntimeError('Natural fixed request hit original cap; no performance-stage advance')
   del tensors,record,inputs;gc.collect()
  save(self.out/'OWN_NEW_PREFILL_IDENTITIES.json',expected)
  for label,active in [('A1',False),('B1',True),('B2',True),('A2',False)]:
   arm='candidate' if active else 'original';self.session.select(active);gc.collect()
   n=len(self.result.get('transactions',[]));v=len(self.result.get('visual_transactions',[]))
   self.guard.begin(label,physical_bound(160,1,visual=True));self.session.checkpoint()
   self.result.setdefault('complete_request_entries',[]).append(dict(label=label,entered=True,returned=False))
   self.result['model_forwards']=len(self.result['complete_request_entries'])
   print('M523_FULL22_TTFT_BEGIN '+label,flush=True)
   began=time.perf_counter_ns();hidden,inputs=self.prepare();prepared=time.perf_counter_ns()
   self.session.checkpoint();prefill_started=time.perf_counter_ns()
   token,logits,cache=self.engine.language.prefill(hidden);first=time.perf_counter_ns()
   self.result['complete_request_entries'][-1]['returned']=True
   observed=identity(hidden,logits,cache.keys,cache.values)
   assert int(token)==observed['token_id'] and observed==expected[arm],'ABBA own-arm warm prefill identity differs'
   self.session.checkpoint();self.guard.end()
   folder=self.out/label;folder.mkdir()
   record=dict(label=label,arm=arm,first_token_wall_s=(first-began)/1e9,prepare_s=(prepared-began)/1e9,
    prefill_s=(first-prefill_started)/1e9,prefill_checkpoint_s=(prefill_started-prepared)/1e9,
    input_tokens=160,input_T32_blocks=5,decode_calls=0,token_id=int(token),numerical_identity=observed,
    own_new_warm_prefill_identity_equal=True,export_and_hash_outside_timer=True,model_load_excluded=True,
    original_PS_schedule_unchanged=True)
   save(folder/'INPUT.json',inputs);save(folder/'SAMPLE.json',record)
   with (folder/'first_logits.npy').open('xb') as f:np.save(f,logits,allow_pickle=False)
   summary=dict(label=label,arm=arm,first_token_wall_s=record['first_token_wall_s'],prepare_s=record['prepare_s'],
    prefill_s=record['prefill_s'],token_id=int(token),sample_sha256=sha(folder/'SAMPLE.json'),
    first_logits_sha256=sha(folder/'first_logits.npy'),own_new_warm_prefill_identity_equal=True)
   summary.update(self.save_observations(label,n,v));samples.append(summary);save(self.out/('SAVED_'+label+'.json'),summary)
   print('M523_FULL22_TTFT_SAVED '+label+' '+str(record['first_token_wall_s']),flush=True)
   cache.keys.clear();cache.values.clear();assert not cache.keys and not cache.values
   del hidden,logits,cache,observed,record,inputs;gc.collect()
  a=[r['first_token_wall_s'] for r in samples if r['arm']=='original'];b=[r['first_token_wall_s'] for r in samples if r['arm']=='candidate']
  assert len(a)==len(b)==2
  self.result.update(complete_requests_returned=2,measured_ABBA_returned=4,total_prefills_returned=6,
   TTFT_original_mean_s=sum(a)/2,TTFT_candidate_mean_s=sum(b)/2,TTFT_speedup_fraction=1-sum(b)/sum(a),
   strict_TTFT_limit_s=92.0,strict_TTFT_pass=all(t<92.0 for t in b),performance_pass=all(t<92.0 for t in b),
   semantic_quality_pass=None,production_promoted=False,heldout_quality_proven=False,
   complete_fixed_input_hardware_functional=True,pruned_language_layers=19,pruned_visual_layers=3,
   scope='Current22 fixed seen V2 input: two natural answers and four own-prefill-identical ABBA first tokens; not heldout quality')
