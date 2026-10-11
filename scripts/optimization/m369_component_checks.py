"""Actual frozen stream control with explicit fake model/MMIO/memory only."""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
from types import SimpleNamespace as N
import numpy as np
import m351_workflow as w


def checks():
    old=w.BASE/'candidates/M368-staged-video-03'
    sys.path.insert(0,str(old))
    import m369_trials as trials
    import m369_light_policy as light
    from m368_video_contract import tensor
    expected=json.loads((old/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    actual=w.ROOT/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/m276_video_runtime.py'
    tree=ast.parse(actual.read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M276ShortPromptBinaryRuntime')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='stream')
    code=compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)],type_ignores=[])),str(actual),'exec')
    original={name:getattr(trials,name) for name in ('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor')}
    saved={name:sys.modules.get(name) for name in ('m276_video_runtime','m366_head_observer')}
    reports=[]
    try:
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'fixtures').mkdir()
            frames=np.zeros((4,448,448,3),np.uint8)
            frame_files={}
            for i,a in enumerate(frames):
                name=f'{i}.npy';np.save(root/'fixtures'/name,a)
                frame_files[name]=hashlib.sha256((root/'fixtures'/name).read_bytes()).hexdigest()
            trials.FRAMES=frame_files;trials.STACK_SHA=hashlib.sha256(frames.tobytes()).hexdigest();trials.ADDON=root
            hidden=np.zeros((159,1),np.float32);visual=np.zeros((98,1),np.float32)
            logits=np.zeros((151936,),np.float32)
            kv=N(keys=[np.zeros((1,1),np.float32) for _ in range(36)],values=[np.zeros((1,1),np.float32) for _ in range(36)])
            prep=dict(pixel_values=np.zeros((2,1),np.float32),image_grid_thw=np.ones((2,3),np.int64),patch_positions=np.zeros((2,1),np.int64))
            ref=copy.deepcopy(expected)
            ref.update(input=tensor(hidden),logits=tensor(logits),keys=[tensor(a) for a in kv.keys],values=[tensor(a) for a in kv.values])
            (root/'VIDEO_EXPECTED.json').write_text(json.dumps(dict(baseline=ref)),encoding='utf-8')
            (root/'VISUAL_EXPECTED.json').write_text(json.dumps(dict(visual_features=tensor(visual),preprocessed={k:tensor(v) for k,v in sorted(prep.items())})),encoding='utf-8')
            decoder=dict(cache_entries=26,cache_bytes=66699264,cache_misses=26,cache_within_budget=True)
            board_rows=[dict(index=i,bytes=b) for i,b in enumerate([6963200]*4+[389152,2621440,2621440])]
            result={};requests=[];closed=[];flag={'timed':False};failure={'kind':None}
            snapshot=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=4098,s2mm_dmasr=4098,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
            class Board:
                def __init__(self,build):self.build=build;self.kernel=object();self.dma=object();self.head_contract=N(chains=[]);self._execute=lambda:None;self._m368_closed=False;self.done=False
                def evidence(self):
                    row=copy.deepcopy(ref if flag['timed'] or requests else ref)
                    if not self.done:row.update(logical_calls=0,logical_expected_macros=0)
                    row.update(build_id=f'0x{self.build:08X}',scale_retry_count=ref['retry_count'],pipeline_retry_launches=ref['retry_launches'],fused_nonfinite_detections=ref['nonfinite_detections'])
                    return row
                def lm_head(self):return logits
                def _launch_once(self,*a):pass
                def _launch_prepacked(self,*a):pass
                def close(self):
                    assert not policy.active
                    self._m368_closed=True;result['released_buffers']=list(reversed(board_rows));closed.append(self.build)
            class Policy:
                def __init__(self,build):self.build=build;self.result=result;self.active=False;self.baseline_rss=0
                def snapshot(self):return {'process_bytes':{'VmRSS':100}}
                def capture(self,*a):return self.snapshot()
                def begin_sampling(self):pass
                def stop_sampling(self):result['sampled_memory']={'observer_stopped':True,'stop_reason':None}
                def wrap_launch(self,fn,name):return fn
                def safe(self):return not self.active
            class Vision:
                def __call__(self,*a):return visual
                def decoder_evidence(self):return dict(decoder)
            class Language:
                grouped_attention_calls=0
                def prefill(self,x):
                    flag['timed']=True;requests.append(self.runtime.build)
                    if failure['kind']=='active':policy.active=True;raise TimeoutError('explicit fake active DMA')
                    self.grouped_attention_calls+=36
                    result['transactions']=[{'method':'head-original-execute' if i>=773 else '_launch_once'} for i in range(781)]
                    self.runtime.lm_head();snapshot['ap_return']=self.runtime.build;self.runtime.done=True
                    return 15,logits,kv
            video=types.ModuleType('m276_video_runtime');video.M276_KNIFE_PROMPT='fake prompt';video.preprocess=lambda *a:prep
            server=N(BUILD_ID='0x4D395832',KERNEL=ref['semantic']['proof']['kernel'],expected_physical_calls=lambda *a:778)
            scope=dict(time=importlib.import_module('time'),np=np,preprocess=lambda *a:video.preprocess(*a),tokenize=lambda *a:list(range(159)),M276_KNIFE_PROMPT='fake prompt',latest_input_embeddings=lambda *a:hidden,constrained_knife_decision=lambda a:dict(text='0',token_id=15,verdict='ABSENT',knife_score=ref['semantic']['token']['knife_score'],score_kind=ref['semantic']['observation']['score_kind']),_server=server)
            exec(code,scope)
            class Engine:
                def load(self):pass
                config={'tokenizer':None};tokenizer=object();_inference_lock=threading.Lock();vision=Vision();language=Language()
                def stream(self,request):
                    flag['timed']=False
                    try:yield from scope['stream'](self,request)
                    finally:flag['timed']=False
            engine=Engine()
            sys.modules['m276_video_runtime']=video
            head=types.ModuleType('m366_head_observer');head.bind=lambda fn,*a:(fn,{'removed_observation_calls_ast_equals_original':True,'original_module':'m230_prefill_runtime','original_function':'M230PrefillRuntime._execute'});sys.modules['m366_head_observer']=head
            trials.minimal=lambda *a:dict(full_output_exact=True,output_bytes=4096)
            trials.io_snapshot=lambda:{'read_bytes':0}
            def checked_tensor(a):
                assert not flag['timed'],'HASH INSIDE ORIGINAL REQUEST TIMER'
                return tensor(a)
            trials.tensor=checked_tensor
            patches=[]
            def patch(obj,name,value):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,value)
            def new(variant,index):
                nonlocal policy
                if index:assert engine.board._m368_closed
                build=0x4d395832 if variant=='A' else 0x4d333537
                server.BUILD_ID=f'0x{build:08X}';board=Board(build);policy=Policy(build)
                result.update(allocated_buffers=copy.deepcopy(board_rows),released_buffers=[],transactions=[])
                return board,policy
            base=N(transaction_snapshot=lambda *a:dict(snapshot))
            for kind in (None,'active','visual'):
                requests.clear();closed.clear();result.clear();failure['kind']=kind
                if kind=='visual':visual[0,0]=1
                board,policy=new('A',0);engine.board=board;engine.language.runtime=board;engine.language.grouped_attention_calls=0
                try:
                    trials.run_trials(engine,board,policy,base,root,root,result,new,patch)
                    assert kind is None and len(result['samples'])==8 and len(closed)==8
                    assert [s['variant'] for s in result['samples']]==list('ABBABAAB')
                    assert result['fpga_transactions_total']==6256
                    reports+=['actual frozen stream balanced8 exact post-timer arrays','seven reverse releases per trial and safe switch','original timers positive and head subset','778logical781physical8head each trial']
                except TimeoutError:
                    assert kind=='active' and policy.active and not closed and len(requests)==1
                    reports+=['active fake DMA failure retains runtime and stops sequence']
                except RuntimeError:
                    assert kind=='visual' and not requests and not closed
                    reports+=['bad warm visual rejected before request']
                finally:
                    for obj,name,value in reversed(patches):setattr(obj,name,value)
                    patches.clear();visual[0,0]=0
            # Sparse policy still invokes original full admission and checks counters.
            mem=dict(process_bytes=dict(VmRSS=100,VmHWM=100),system_bytes=dict(CmaFree=1,MemAvailable=3<<30))
            counts={'area:alloc_pages_success':8,'area:alloc_pages_fail':0}
            p=light.StagePolicy({},lambda:None,None,snapshot=lambda:mem,counters=lambda:counts.copy())
            p.seal([N(nbytes=n) for n in [6963200]*4+[389152,2621440,2621440]],0x4d395832)
            before=len(p.result['stage_memory']);p.capture('before-physical-launch:fake',True)
            assert len(p.result['stage_memory'])==before
            counts['area:alloc_pages_success']+=1
            try:p.capture('before-physical-launch:fake',True);raise AssertionError('Counter change accepted')
            except RuntimeError:pass
            reports+=['sparse physical observation keeps counter stop without large log']
    finally:
        for name,value in original.items():setattr(trials,name,value)
        for name,value in saved.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value
        sys.path.remove(str(old))
    return reports


if __name__=='__main__':print(json.dumps(dict(status='PASS_OFFLINE_LIGHT_TIMING_CONTROL',checks=checks(),fake_model_MMIO_memory=True,hardware_proof=False)))
