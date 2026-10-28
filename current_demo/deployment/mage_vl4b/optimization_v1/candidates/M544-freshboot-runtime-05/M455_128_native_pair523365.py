"""Native four-request entry using the real returned engine and seven owners.

Called only after the enclosing native runner verifies the sealed package and
the actual V14 layer result. Arrays are saved after each original timed loop.
"""
import gc,hashlib,importlib.util,json,os,time
from pathlib import Path
import numpy as np
from M455_request_guard52354 import RequestTransactionGuard,BorrowedPolicyBridge,workers
from M455_same_owner_canary52301 import run_same_owner_canary
from M455_dense_only_view52301 import DenseOnlyView
from M455_twentytwo_language_binding523288 import TwentytwoLanguageBinding
from M455_twentytwo_visual_scope523290 import TwentytwoVisualProvider
from M455_four_block_request523366 import RequestPreparation,same_prefix_KL
from M455_full22_paired_request523331 import PairedRequestSession
from M455_strict_visual_wait52326 import StrictVisualBase

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();part=path.with_suffix(path.suffix+'.partial')
    with part.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    assert not path.exists();os.rename(part,path)

class NativePair:
    def __init__(self,*,component,here,engine,runtime,factory,ledger,state,clocks,result,out,snapshot,safe,wait_observed):
        self.component,self.here,self.engine,self.runtime=component,here,engine,runtime
        self.factory,self.ledger,self.state,self.clocks,self.result,self.out=factory,ledger,state,clocks,result,out
        self.snapshot,self.outer_safe,self.wait_observed=snapshot,safe,wait_observed
        self.guard=self.binding=self.visual=self.original=None;self.closed=False
        self.plan=read(component/'REQUEST_PLAN.json')
        assert {r['layer'] for r in self.plan['language']}=={1,2,4,12,14,15,16,20,21,22,23,24,26,27,28,29,31,32,34}
        assert set(self.plan['visual'])=={'14','15','21'}
        assert self.plan['generation_cap']==32 and self.plan['input_source']=='historical_seen_M455_four_frame_fixture'
        assert self.plan['new_full_model_forwards_budget']==6
        if not 98<len(self.plan['token_ids'])<=160 or self.plan['token_ids'].count(151655)!=98:raise ValueError('Frozen five-block M455 input required')
        if sha(component/'TASK_CONTRACT.json')!=self.plan['task_contract_sha256']:raise ValueError('Actual five-block task contract SHA differs')
        task=read(component/'TASK_CONTRACT.json')
        if task['token_ids']!=self.plan['token_ids'] or task['generation_cap_tokens']!=32:raise ValueError('Common input or original generation cap differs')
    def check_resources(self):
        from m455_board_clocks03 import validate_operating
        self.ledger.verify_full(self.runtime);validate_operating(self.clocks.snapshot())
        if self.state.unsafe() or self.ledger.allocating_unknown:raise RuntimeError('Actual request owner unknown')
        if any(h.state!='owned' for h in self.ledger.hooks):raise RuntimeError('Seven original live release hooks required')
    def idle(self):
        if workers() or not self.outer_safe() or self.guard is not None and not self.guard.safe():raise RuntimeError('Native request DMA/workers unresolved')
        self.check_resources()
    def configure(self):
        runtime=self.runtime;factory=self.factory;base=factory['base'];component=self.component;plan=self.plan
        self.idle();chains=list(runtime.language_contract.chains)+list(runtime.head_contract.chains)
        self.guard=RequestTransactionGuard(chains,self.snapshot,self.check_resources,self.result,self.state)
        from completion_boundary import install
        install(self.guard,self.result)
        canary=read(component/'CANARY_PLAN.json')
        packet=(component/canary['packet']).read_bytes();golden=(component/canary['golden']).read_bytes()
        weights=[(component/n).read_bytes() for n in canary['weights']]
        identities=dict(packet=hashlib.sha256(packet).hexdigest(),golden=hashlib.sha256(golden).hexdigest(),weights=[hashlib.sha256(w).hexdigest() for w in weights])
        init=run_same_owner_canary(runtime=runtime,guard=self.guard,ledger=self.ledger,base=base,packet=packet,golden=golden,weights=weights,
            config=int(canary['config'],0),identities=identities,check_resources=self.check_resources,wait_observed=self.wait_observed,result=self.result)
        raw=bytes(memoryview(runtime.output_buffer)[:len(golden)]);assert raw==golden
        with (self.out/'same_owner_canary_fullwire.bin').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        save(self.out/'same_owner_canary.json',init)
        self.result['instrumented_original_methods']=[self.guard.bind(runtime,n) for n in ('_launch_prepacked','_launch_once','_execute')]
        specs={}
        for row in plan['language']:
            layouts=[]
            for entry in row['layouts']:
                directory=component/entry['path'];layouts.append(base.verify_layout(directory,entry['manifest_sha256'],entry['modules']))
            bias=np.frombuffer((component/row['bias']).read_bytes(),np.float32).copy()
            specs[row['layer']]=(row['cases'],layouts,bias)
        self.binding=TwentytwoLanguageBinding(runtime,self.engine.language,specs,safe=self.guard.safe,ledger=self.ledger,base=base)
        view=DenseOnlyView(factory,runtime,self.ledger,self.idle)
        assets=Path(plan['assets_root']);asset_plan=read(assets/'PLAN.json')
        from m432_request_visual import verify_sources
        from m455_original94_timed_visual01 import TimedVisualProvider
        sources=verify_sources(asset_plan)
        policy=BorrowedPolicyBridge(self.guard,self.ledger,runtime,self.check_resources)
        from m455_completion_observer import wait_observed as original_visual_observer
        visual_base=StrictVisualBase(base,original_visual_observer,self.result)
        self.original=TimedVisualProvider(self.engine,runtime,policy,visual_base,assets,self.result,sources,enabled=True,abi=view)
        self.original.original_vision_call=self.engine.vision.__class__.__call__
        crops={int(i):dict(chains=c['chains'],windows=c['windows'],kept_ids=np.asarray(c['kept_ids'],np.int64),
            r1=np.frombuffer(Path(c['bias']).read_bytes(),np.float32).copy()) for i,c in plan['visual'].items()}
        self.visual=TwentytwoVisualProvider(self.original,crops=crops,cropped_root=Path(plan['crop_root']),idle=self.idle)
        spec=importlib.util.spec_from_file_location('_m455_original_generation52324',component/'generation01.py')
        generation=importlib.util.module_from_spec(spec);spec.loader.exec_module(generation)
        import m273_latest_multiscale_contract as m273,m276_video_runtime as m276
        self.prepare=RequestPreparation(self.engine,self.original.frames,self.visual,m273.preprocess,m276.latest_input_embeddings,plan['token_ids'])
        self.session=PairedRequestSession(runtime,self.binding,self.visual,self.guard,generation.generate,self.idle,view.require_current)
        self.result.update(initialization_manual_physical_calls=1,complete_request_forward_budget=5,request_model_loading_included=False,
            request_timing_contains_guard_observers=True,independent_heldout_quality_proven=False,all_11_visual_PL_layers=True)
    def persist_tensors(self,label,record,tensors,input_record):
        directory=self.out/label;directory.mkdir();rows=[]
        def array(name,value):
            a=np.asarray(value)
            if a.dtype!=np.float32 or not np.isfinite(a).all():raise RuntimeError('Nonfinite or wrong complete native output: '+name)
            path=directory/(name+'.npy')
            with path.open('xb') as f:np.save(f,a,allow_pickle=False);f.flush();os.fsync(f.fileno())
            rows.append(dict(path=path.name,bytes=path.stat().st_size,sha256=sha(path),shape=list(a.shape),dtype=str(a.dtype)))
        array('input_embeddings',tensors['input_embeddings']);array('logits',tensors['logits'])
        for prefix in ('prefill_keys','prefill_values','final_keys','final_values'):
            assert len(tensors[prefix])==36
            for i,a in enumerate(tensors[prefix]):array(prefix+'_'+str(i).zfill(2),a)
        save(directory/'INPUT.json',input_record);save(directory/'REQUEST.json',record)
        save(directory/'ARRAY_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),all72_KV_initial_and_final_saved=True))
        return dict(label=label,request_sha256=sha(directory/'REQUEST.json'),array_manifest_sha256=sha(directory/'ARRAY_MANIFEST.json'),
            text=record['text'],token_ids=record['token_ids'],stop_reason=record['stop_reason'],timing=record['timing'])
    def run(self):
        try:return self._run()
        except OSError:
            self.state.latched=True
            raise
    def close(self):
        if self.closed:return
        self.idle()
        if self.original is not None:
            if self.original.current_owner is not None or self.original.current_scope is not None:raise RuntimeError('Borrowed visual owner/scope retained')
        if self.guard is not None and self.guard.request is not None:raise RuntimeError('Request boundary not returned')
        if self.binding is not None:self.binding.close()
        if self.guard is not None:self.guard.restore_methods()
        self.closed=True
